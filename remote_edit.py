import sublime, sublime_plugin, os, subprocess

# Variables that can be used in the host and pathname
TEMPLATE_ARGS = {
	"SUNetID": "cfigg"
}
# Default options as placeholder when choosing a hostname and path
DEFAULT_HOST = "{SUNetID}@cardinal.stanford.edu"
DEFAULT_PATH = "~/"

tries = 3

# Remote Download command to fetch a file and open it in a new tab
class RemoteDownloadCommand(sublime_plugin.TextCommand):
	# host: host name to download from
	# path: path to file within host to download
	# defaultHost: the value to show as the placeholder when choosing a host
	# defaultPath: the value to show as the placeholder when choosing a path
	def run(self, edit, host=None, path=None, defaultHost=DEFAULT_HOST, defaultPath=DEFAULT_PATH):
		window = self.view.window()

		# If no host or path was passed in, show a prompt for the user to choose
		if host is None or path is None:
			def on_done_host(host):
				def on_done_path(path):
					# Once the user has chosen a host and path, re-run the command with the new values
					window.active_view().run_command("remote_download", {"host": host, "path": path})

				window.show_input_panel(
				"Enter a file path to download:",
				defaultPath.format(**TEMPLATE_ARGS),
				on_done=on_done_path,
				on_change=None,
				on_cancel=None)

			window.show_input_panel(
				"Enter a host name to download from:",
				defaultHost.format(**TEMPLATE_ARGS),
				on_done=on_done_host,
				on_change=None,
				on_cancel=None)
			return

		host = host.format(**TEMPLATE_ARGS)
		path = path.format(**TEMPLATE_ARGS)

		# Will store the downloaded file as bytes
		file = None
		# Try to download file `tries' times before giving up
		for i in range(tries):
			# If scp returns a non-0 code, an error is raised and caught
			try:
				# -B ensures scp will fail if a password is asked for
				file = subprocess.check_output(["scp", "-B", "{}:{}".format(host, path), "/dev/stdout"])
				break
			except subprocess.CalledProcessError as err:
				if err.returncode == 0:
					raise(err)
		else:
			# The file couldn't be downloaded and an error message is shown to the user
			sublime.error_message("The file at {}:{} couldn't be downloaded.".format(host, path))
			return
		
		# A temporary file is made on disk to store the downloaded file
		filename = RemoteDownloadCommand.makeTmpFile(path, file)

		# Open a new tab for the file (or open a pre-existing one)
		view = window.open_file(filename)

		# openFile is run once the view is done loading
		def openFile():
			if view.is_loading():
				# If it's not done loading, try again in 200 ms
				sublime.set_timeout_async(openFile, 200)
			else:
				# Set up settings for the file for easier uploading later
				view.settings().set("remote_edit_tmp_file", filename)
				view.settings().set("remote_edit_origin", "{}:{}".format(host, path))
				view.settings().set("remote_edit_is_remote", True)
				view.set_status("remote_edit_status", "Uplaoding to {}:{}".format(host, path))
		sublime.set_timeout_async(openFile, 0)

	# makeTmpFile makes a file in /tmp to store downloaded files
	# path: the path the file was downloaded from (used in naming the temporary file)
	# write: whether to write to the new file or just make it
	@staticmethod
	def makeTmpFile(path, file, write=True):
		# The directory to store temporary files in
		dirname = "/tmp/sublimeremoteedit"

		# Make the directory if it doesn't exist yet
		try:
			os.mkdir(dirname)
		except FileExistsError:
			pass

		# A sub-directory is made inside that is named from the hash of the path's directory name
		# Using a hash ensures files from the same path are stored in the same directory on disk
		# Using a hash also ensures the directory is always a valid name (since the path being hashed will probably contains character like "/")
		dirname += "/{}".format(hash(os.path.dirname(path)))
		try:
			os.mkdir(dirname)
		except FileExistsError:
			pass

		# The original file name is used so the user sees it correctly in the tab name
		filename = "{}/{}".format(dirname, os.path.basename(path))

		# Write to the new file if `write' is True
		if write:
			diskFile = open(filename, "wb+" if type(file) is bytes else "w+")
			diskFile.write(file)
			diskFile.close()
		else:
			diskFile = open(filename, "a")
			diskFile.close()

		# Return the path to the temporary file
		return filename

# Remote Upload command to upload a file to a remote location
class RemoteUploadCommand(sublime_plugin.TextCommand):
	# src: the combination of host:path to upload the file to
	# write: whether the on-disk file has to be written to before uploading
	#	If the user saves the file manually, there's no need to re-write to the file before uploading
	def run(self, edit, src=None, write=True, defaultHost=DEFAULT_HOST, defaultPath=DEFAULT_PATH):
		window = self.view.window()
		view = self.view
		settings = view.settings()

		# If no src was passed, try to get it from the file's settings or prompt the user if that fails
		if src is None:
			src = settings.get("remote_edit_origin")
			if src is None:
				# Prompt the user for a host and path name to upload to
				def on_done_host(host):
					def on_done_path(path):
						# Re-run the command with the new values
						view.run_command("remote_upload", {"src": "{}:{}".format(host, path)})

					window.show_input_panel(
					"Enter a path to upload file to:",
					defaultPath.format(**TEMPLATE_ARGS),
					on_done=on_done_path,
					on_change=None,
					on_cancel=None)

				window.show_input_panel(
					"Enter a host name to upload to:",
					defaultHost.format(**TEMPLATE_ARGS),
					on_done=on_done_host,
					on_change=None,
					on_cancel=None)
				return

		src = src.format(**TEMPLATE_ARGS)

		# Update the file's settings to be able to upload without having to re-choose in the future
		settings.set("remote_edit_origin", src)
		settings.set("remote_edit_is_remote", True)
		view.set_status("remote_edit_status", "Uploading to {}".format(src))

		# Get the location of the on-disk copy of the file
		diskLoc = view.file_name() or settings.get("remote_edit_tmp_file")

		# If it couldn't be found, make a new temporary file to store it
		if diskLoc is None:
			write = True
			diskLoc = RemoteDownloadCommand.makeTmpFile(src.split(":")[1], view.substr(sublime.Region(0, view.size())), write=False)
			settings.set("remote_edit_tmp_file", diskLoc)

		# Shows "Uploading..." in the status bar to show the user stuff is happening
		window.status_message("Uploading...")

		# doUpload is done asynchronously to prevent freezing
		def doUpload():
			# If `write' is True, write to the temporary file before saving (may not be necessary if the user saved manually)
			if write:
				diskFile = open(diskLoc, "w+")
				diskFile.write(view.substr(sublime.Region(0, view.size())))
				diskFile.close()

			# Try `tries' number of times to upload
			for i in range(tries):
				try:
					subprocess.check_output(["scp", "-B", diskLoc, src])
					window.status_message("Uploaded successfully")
					break
				except subprocess.CalledProcessError as err:
					if err.returncode == 0:
						raise(err)
			else:
				# Show an error if the upload failed
				sublime.error_message("The file at {}:{} couldn't be uploaded.".format(src, path))

		sublime.set_timeout_async(doUpload, 0)

# Controls auto-uploading on save and cleaning up temporary files
class KeepRemoteFileUpdated(sublime_plugin.ViewEventListener):
	# Only run auto-uploading and cleaning for files that are associated with a remote location
	@classmethod
	def is_applicable(cls, settings):
		return bool(settings.get("remote_edit_is_remote", False))

	def on_activated_async(self):
		origin = self.view.settings().get("remote_edit_origin", False)
		if origin:
			self.view.set_status("remote_edit_status", "Uplaoding to {}".format(origin))
		else:
			self.view.set_status("remote_edit_status", "")
	# After saving, upload the file
	def on_post_save_async(self):
		if self.view.settings().get("remote_edit_origin", False):
			self.view.run_command("remote_upload", {"write": False})

	# After closing the file tab, delete the temporary file
	# NOTE: Since the temporary file is cleaned up immediately, re-opening the tab will not work
	# (The settings to upload the file aren't saved and restored either anyway, so even if it wasn't deleted, it wouldn't be able to be uploaded)
	# The file can still be redownloaded and opened again as normal though
	def on_pre_close(self):
		diskLoc = self.view.settings().get("remote_edit_tmp_file", False)
		if diskLoc:
			os.remove(diskLoc)
			# Also try removing its directory if there are no more files in it
			try:
				os.rmdir(os.path.dirname(diskLoc))
			except OSError:
				pass

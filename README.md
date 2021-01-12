# Remote-Edit
Sublime Text 3 plugin to edit remote files on a server as a local file. (Mac OS X)

Instead of using `ssh` and then editing a file in the terminal using `emacs` or some other terminal-based text editor, this plugin will download the file from the server and open it in Sublime Text to make editing easier and faster. Saving the file in ST will automatically upload the file back to the server to save to the original file.

This plugin was helpful for me in classes that required me to submit/edit/run files on Stanford's myth machines as in CS 107.

### Usage
Use the "Remote Edit: Download File" and "Remote Edit: Upload File" commands to open a remote file and save to a remote location respectively.

After opening a remote file, saving it through ST will automatically upload the file so you don't have to "Remote Edit: Upload File" each time.

Remote files will show "`Uploading to [host]:[path]`" in the status bar at the bottom to show where they are being saved to.

### Setup
Stanford's `ssh` requires you to enter your password every time you want to access anything over `ssh`, which can be annoying when all you want to do is edit a single file. To make it easier, set up a Kerberos ticket so you don't have to enter your password every time ([here's a helpful (but slightly outdated) outdated guide to setting that up](https://reberhardt.com/blog/2016/10/09/tips-for-working-with-stanfords-myth-machines.html))

After doing that, drop `remote_edit.py` and `remote_edit.sublime-commands` in your user packages folder (probably at `~/Library/Application Support/Sublime Text 3/Packages/User`) and restart ST to see the commands in the command palette.

Lastly, to make sure it actually logs into **your** account, you should change the `"SUNetID"` template argument (line 4 of `remote_edit.py`) to your own SUNetID (or add to it or remove it or whatever you want to do).

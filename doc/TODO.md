# TODO

A list of stuff & things todo (not in any particular order):

#### Short term goals

* Finish the port of FastConfigure to use virtual shares.
* Drop the bundle Configparser module (upstream as all the patches).
* Convert libsexy spellcheck stuff to pygtkspell.
* Upload old sourceforge releases to github & refresh the update check code.
* GNU/Linux: Switch to using XDG_* directories.
* Apply downstream patches (debian, fedora & ubuntu).
* Convert all the libglade files to GTKBuilder.
* Our sounds are dropped by downstream packagers for being non-free: investigate.
* Convert old (unmaintained) python-GeoIP code to an up to date version.
* Drop the embeded Web browser: does work anymore, outdated and security nightmare.
* **DONE**: Refresh setuptools installer/builder (Done on the GNU/Lonux side).
* **DONE**: Drop in-house mp3 metadata parsing: replaced by mutagen.
* **DONE**: Drop the old trayicon module: use the GTK included one.
* **DONE**: Drop psyco (code speed up for Windows): unmaintained and not usefull anymore.
* **DONE**: Drop py2exe code: pyinstaller will be used for Windows.
* **DONE**: Rewrite UPnP handling to avoid nasty bugs.
* **DONE**: Rewrite locales/translation code to better handle Windows.

#### Long term goals

* **IN PROGRESS**: Update the wiki.
* Update the Nicotine Guide.
* Reach out for tranlation help.
* Switch to Python 3.X.
* Switch to GTK3.
* Switch to Gstreamer 1.X (require GTK3).
* Switch from python-notify to an up to date alternative.
* Use pip and venv for build/tests purposes.
* Make as much as possible optionnal dependencies work on Windows.
* Build the OSX version (I've no Mac).

#### Windows specific stuff

PyInstaller:
* **IN PROGRESS**: Document how to build a frozen app.
* **IN PROGRESS**: Write a spec file including:
    * The Nicotine Guide.
    * Translations files.
    * MiniUPnPc binary for upnp support.
    * Glade and gtkbuilder files.

* Refresh setuptools installer/builder.

NSIS installer:
* Test & refresh Quinox stuff.
* Check for VS2010 runtime availability.

UPnP:
* **IN PROGRESS**: Test using the precompiled binary from upstream.

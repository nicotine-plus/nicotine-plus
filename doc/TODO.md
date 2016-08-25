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
* Drop the embeded Web browser: doesn't work anymore, outdated and security nightmare.
* **DONE**: Refresh setuptools installer.
* **DONE**: Drop in-house mp3 metadata parsing: replaced by mutagen.
* **DONE**: Drop the old trayicon module: use the GTK included one.
* **DONE**: Drop psyco (code speed up for Windows): unmaintained and not useful anymore.
* **DONE**: Drop py2exe code: PyInstaller will be used for Windows.
* **DONE**: Rewrite UPnP handling to avoid nasty bugs.
* **DONE**: Rewrite locales/translation code to better handle Windows.

#### Long term goals

* **IN PROGRESS**: Update the wiki.
* Update the Nicotine Guide.
* Reach out for translation help.
* Switch to Python 3.X.
* Switch to GTK3.
* Switch to Gstreamer 1.X (require GTK3).
* Switch from python-notify to an up to date alternative.
* **IN PROGRESS**: Use pip and venv for build/tests purposes.
* **IN PROGRESS**: Make as much as possible optional dependencies work on Windows.
* **STALLED**: Build the OSX version: I've no Mac.

#### Windows specific goals

* Theming

    * Find a GTK2 theme to apply to the frozen app so it doesn't look bad.
    * Same goes for fonts.


* NSIS installer:

    * Test & refresh Quinox stuff.


* **DONE**: PyInstaller:

    * Document how to build a frozen app.
    * Write a spec file including:
        * The Nicotine Guide.
        * Translations files.
        * MiniUPnPc binary for UPnP support.
        * Glade and gtkbuilder files.


* **DONE**: UPnP:

    * Use the precompiled binary from the MiniUPnP Project.

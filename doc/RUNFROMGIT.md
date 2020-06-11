# Run Nicotine+ from git

## GNU/Linux

* Install all the [required dependencies](README.md#required):

    * On Redhat/Fedora based distributions:

    `sudo dnf install gobject-introspection gtk3 python3-dbus python3-gobject python3-mutagen`

    * On Debian/Ubuntu based distributions:

    `sudo apt install gobject-introspection gir1.2-gtk-3.0 python3-dbus python3-gi python3-mutagen`

* Install [optional dependencies](README.md#optional), if desired:

    * On Redhat/Fedora based distributions:

    `sudo dnf install gsound gspell libappindicator-gtk3 libnotify python3-miniupnpc`

    * On Debian/Ubuntu based distributions:

    `sudo apt install gir1.2-appindicator3-0.1 gir1.2-gsound-1.0 gir1.2-gspell-1 gir1.2-notify-0.7 python3-miniupnpc `

* Check that the Python version you are using is 3.5 or newer via `python -V`.

* In the git root folder, run `python nicotine`.

## Windows

See [PACKAGING.md](doc/PACKAGING.md#windows)

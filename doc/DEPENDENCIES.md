# Dependencies

## Required

* [python3](https://www.python.org/) >= 3.5 for interpreter;
* [python3-gi](https://pygobject.readthedocs.io/en/latest/getting_started.html) for using GObject introspection with Python 3;
* [gobject-introspection](https://gi.readthedocs.io/en/latest/) for GObject introspection;
* [gir1.2-gtk-3.0](https://www.gtk.org/) for GObject introspection bindings for GTK;
* [python3-mutagen](https://mutagen.readthedocs.io/en/latest/) >= 1.36.2 for metadata parsing;
* [python3-miniupnpc](https://miniupnp.tuxfamily.org/) >= 1.9 for opening ports on your router or `upnpc(1)` if not available;
* [robotframework](https://robotframework.org/) for CI testing.

## Optional

* [gir1.2-appindicator3-0.1](https://lazka.github.io/pgi-docs/AppIndicator3-0.1/index.html) for tray icon;
* [gir1.2-gsound-1.0](https://lazka.github.io/pgi-docs/GSound-1.0/index.html) for sound effects;
* [gir1.2-gspell-1](https://lazka.github.io/pgi-docs/Gspell-1/index.html) for spell checking in chat;
* [gir1.2-notify-0.7](https://lazka.github.io/pgi-docs/Notify-0.7/index.html) for desktop notifications;

## Installing dependencies
### GNU/Linux

#### Installing the required dependencies
* On Redhat/Fedora based distributions:
```
sudo dnf install gobject-introspection gtk3 python3-dbus python3-gobject python3-mutagen
```
* On Debian/Ubuntu based distributions:
```
sudo apt install gobject-introspection gir1.2-gtk-3.0 python3-dbus python3-gi python3-mutagen
```

#### Installing the optional dependencies
* On Redhat/Fedora based distributions:
```
sudo dnf install gsound gspell libappindicator-gtk3 libnotify python3-miniupnpc
```
* On Debian/Ubuntu based distributions:
```
sudo apt install gir1.2-appindicator3-0.1 gir1.2-gsound-1.0 gir1.2-gspell-1 gir1.2-notify-0.7 python3-miniupnpc
```

#### Check the Python version.
To check that the Python version you are using is 3.5 or newer use `python -V`. On lots of systems this will return something like this:
```
% python -V
Python 2.7.16
```
Not to worry, python version 3 is often installed alongside and can be used like  this:
```
% python3 -V
Python 3.7.3
```

## Windows
See [PACKAGING.md](PACKAGING.md#windows)

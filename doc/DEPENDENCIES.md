# Dependencies

## Required

* [python3](https://www.python.org/) >= 3.5 for interpreter;
* [python3-gi](https://pygobject.readthedocs.io/en/latest/getting_started.html) for using GObject introspection with Python 3;
* [gobject-introspection](https://gi.readthedocs.io/en/latest/) for GObject introspection;
* [gir1.2-gtk-3.0](https://www.gtk.org/) for GObject introspection bindings for GTK;
* [robotframework](https://robotframework.org/) for CI testing.

## Optional

* [gir1.2-appindicator3-0.1](https://lazka.github.io/pgi-docs/AppIndicator3-0.1/index.html) or [gir1.2-ayatanaappindicator3-0.1](https://lazka.github.io/pgi-docs/AyatanaAppIndicator3-0.1/index.html) for tray icon;
* [gir1.2-gspell-1](https://lazka.github.io/pgi-docs/Gspell-1/index.html) for spell checking in chat;

## Installing dependencies
### GNU/Linux

#### Installing the required dependencies
* On Redhat/Fedora based distributions:
```
sudo dnf install gobject-introspection gtk3 python3-dbus python3-gobject
```
* On Debian/Ubuntu based distributions:
```
sudo apt install gobject-introspection gir1.2-gtk-3.0 python3-dbus python3-gi
```

#### Installing the optional dependencies
* On Redhat/Fedora based distributions:
```
sudo dnf install gspell libappindicator-gtk3
```
* On Debian/Ubuntu based distributions:
```
sudo apt install gir1.2-appindicator3-0.1 gir1.2-gspell-1
```

#### Check the Python version.
To check that the Python version you are using is 3.5 or newer, use `python -V`. On a lot of older systems, the response will look something like this:  
```
% python -V
Python 2.7.16
```

Not to worry, Python 3 is often installed alongside and can be used like this:  
```
% python3 -V
Python 3.7.3
```

## Windows
See [PACKAGING.md](PACKAGING.md#windows)

# Dependencies

## Runtime

### Required

* [python](https://www.python.org/) >= 3.6 for interpreter;
* [pygobject](https://pygobject.readthedocs.io/en/latest/getting_started.html) for using GObject introspection with Python 3;
* [gir1.2-gtk-3.0](https://www.gtk.org/) for GObject introspection bindings for GTK;
* [gdbm](https://www.gnu.org.ua/software/gdbm/) or [semidbm](https://semidbm.readthedocs.io/en/latest/) for scanning shared files.

### Recommended

* [gir1.2-appindicator3-0.1](https://lazka.github.io/pgi-docs/AppIndicator3-0.1/index.html) or [gir1.2-ayatanaappindicator3-0.1](https://lazka.github.io/pgi-docs/AyatanaAppIndicator3-0.1/index.html) for tray icon;
* [gir1.2-gspell-1](https://lazka.github.io/pgi-docs/Gspell-1/index.html) for spell checking in chat.

## Building

* [gettext](https://www.gnu.org/software/gettext/) for generating translations.

## Testing

* [flake8](https://flake8.pycqa.org/en/latest/) for lint checks;
* [pylint](https://www.pylint.org/) for lint checks;
* [pygobject](https://pygobject.readthedocs.io/en/latest/getting_started.html) for integration tests;
* [gir1.2-gtk-3.0](https://www.gtk.org/) for integration tests.

## Installing dependencies

### GNU/Linux

#### Installing the required runtime dependencies
* On Debian/Ubuntu based distributions:

```sh
sudo apt install gir1.2-gtk-3.0 python3-gi python3-gdbm
```

* On Redhat/Fedora based distributions:

```sh
sudo dnf install gtk3 python3-gobject gdbm
```

#### Installing the recommended runtime dependencies
* On Debian/Ubuntu based distributions:

```sh
sudo apt install gir1.2-appindicator3-0.1 gir1.2-gspell-1
```

* On Redhat/Fedora based distributions:

```sh
sudo dnf install gspell libappindicator-gtk3
```

#### Installing the test dependencies
* On Debian/Ubuntu based distributions:

```sh
sudo apt install gir1.2-gtk-3.0 pylint3 python3-flake8 python3-gi
```

* On Redhat/Fedora based distributions:

```sh
sudo dnf install gtk3 pylint python3-flake8 python3-gobject
```

#### Check the Python version.
To check that the Python version you are using is recent enough, use `python -V`. On a lot of older systems, the response will look something like this:

```console
% python -V
Python 2.7.16
```

Not to worry, Python 3 is often installed alongside and can be used like this:

```console
% python3 -V
Python 3.7.3
```

### Windows
See [PACKAGING.md](PACKAGING.md#windows)

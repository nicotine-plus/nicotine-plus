# Dependencies

## Runtime

### Required

- [python3](https://www.python.org/) >= 3.5;
- [gtk3](https://gtk.org/) >= 3.18 for graphical interface;
- [pygobject](https://pygobject.readthedocs.io/) for Python bindings for GTK;
- [gdbm](https://www.gnu.org/software/gdbm/) for scanning shared files.

### Recommended

- [ayatanaappindicator](https://lazka.github.io/pgi-docs/AyatanaAppIndicator3-0.1/) / appindicator for tray icon;
- [gspell](https://lazka.github.io/pgi-docs/Gspell-1/) for spell checking in chat.

## Building

- [appstream](https://freedesktop.org/wiki/Distributions/AppStream/) for generating translations;
- [gettext](https://www.gnu.org/software/gettext/) for generating translations;
- [setuptools](https://setuptools.pypa.io/) for packaging.

## Testing

- [flake8](https://flake8.pycqa.org/) for lint checks;
- [pylint](https://pylint.org/) for lint checks;
- [pygobject](https://pygobject.readthedocs.io/) for integration tests;
- [gtk3](https://gtk.org/) for integration tests.


## Installing Dependencies

### GNU/Linux

#### Installing Required Runtime Dependencies

- On Debian/Ubuntu based distributions:

```sh
sudo apt install gir1.2-gtk-3.0 python3-gi python3-gdbm
```

- On Redhat/Fedora based distributions:

```sh
sudo dnf install gtk3 python3-gobject gdbm
```

#### Installing Recommended Runtime Dependencies

- On Debian/Ubuntu based distributions:

```sh
sudo apt install gir1.2-ayatanaappindicator3-0.1 gir1.2-gspell-1
```

- On Redhat/Fedora based distributions:

```sh
sudo dnf install gspell libappindicator-gtk3
```

#### Installing Build Dependencies

- On Debian/Ubuntu based distributions:

```sh
sudo apt install appstream gettext python3-setuptools
```

- On Redhat/Fedora based distributions:

```sh
sudo dnf install appstream gettext python3-setuptools
```

#### Installing Test Dependencies

- On Debian/Ubuntu based distributions:

```sh
sudo apt install gir1.2-gtk-3.0 pylint3 python3-flake8 python3-gi
```

- On Redhat/Fedora based distributions:

```sh
sudo dnf install gtk3 pylint python3-flake8 python3-gobject
```

### Windows

See [PACKAGING.md](PACKAGING.md#windows)

### macOS

See [PACKAGING.md](PACKAGING.md#macos)

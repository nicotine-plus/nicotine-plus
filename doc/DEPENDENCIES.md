# Dependencies

## Runtime

### Required

- [python3](https://www.python.org/) >= 3.6;
- [gtk3](https://gtk.org/) >= 3.22.30 for graphical interface;
- [pygobject](https://pygobject.readthedocs.io/) >= 3.22 for Python bindings for GTK.

### Recommended

- [ayatanaappindicator / appindicator](https://ayatanaindicators.github.io/) for tray icon;
- [gspell](https://gitlab.gnome.org/GNOME/gspell) for spell checking in chat.

## Building

- [gettext](https://www.gnu.org/software/gettext/) for generating translations;
- [setuptools](https://setuptools.pypa.io/) for packaging.

## Testing

- [flake8](https://flake8.pycqa.org/) for lint checks;
- [pylint](https://pylint.pycqa.org/) for lint checks;
- [pygobject](https://pygobject.readthedocs.io/) for integration tests;
- [gtk3](https://gtk.org/) for integration tests.


## Installing Dependencies

### GNU/Linux

#### Installing Required Runtime Dependencies

- On Debian/Ubuntu based distributions:

```sh
sudo apt install gir1.2-gtk-3.0 python3-gi
```

- On Redhat/Fedora based distributions:

```sh
sudo dnf install gtk3 python3-gobject
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
sudo apt install gettext python3-setuptools
```

- On Redhat/Fedora based distributions:

```sh
sudo dnf install gettext python3-setuptools
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

### Windows and macOS

All required dependencies are included in the [Nicotine+ Windows Installer](DOWNLOADS.md#windows) and [Nicotine+ macOS Installer](DOWNLOADS.md#macos) official release packages, no additional steps are required by a regular user in order to install stable versions of Nicotine+.

For developers who need to build packages with dependencies in a development environment, see [PACKAGING.md](PACKAGING.md).

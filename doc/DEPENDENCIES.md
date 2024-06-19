# Dependencies

## Runtime

### Required

- [python3](https://www.python.org/) >= 3.6;
- [gtk4](https://gtk.org/) >= 4.6.9 or [gtk3](https://gtk.org/) >= 3.22.30 for graphical interface;
- [pygobject](https://pygobject.readthedocs.io/) for Python bindings for GTK;

### Recommended

- [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita) for Adwaita theme on GNOME (GTK 4).
- [gspell](https://gitlab.gnome.org/GNOME/gspell) for spell checking in chat (GTK 3).

## Building

- [build](https://build.pypa.io/) for building;
- [gettext](https://www.gnu.org/software/gettext/) for generating translations;
- [setuptools](https://setuptools.pypa.io/) for packaging.

## Testing

- [pycodestyle](https://pycodestyle.pycqa.org/) for code style checks;
- [pylint](https://pylint.readthedocs.io/) for linting.


## Installing Dependencies

### GNU/Linux

#### Installing Runtime Dependencies

- On Debian/Ubuntu-based distributions:

```sh
sudo apt install gir1.2-gspell-1 gir1.2-gtk-4.0 gir1.2-adw-1 python3-gi
```

- On Redhat/Fedora-based distributions:

```sh
sudo dnf install gspell gtk4 libadwaita python3-gobject
```

- On SUSE-based distributions:

```sh
sudo zypper install typelib-1_0-Gspell-1 typelib-1_0-Gtk-4_0 typelib-1_0-Adw-1 python3-gobject
```

#### Installing Build Dependencies

- On Debian/Ubuntu-based distributions:

```sh
sudo apt install gettext python3-build python3-setuptools
```

- On Redhat/Fedora-based distributions:

```sh
sudo dnf install gettext python3-build python3-setuptools
```

- On SUSE-based distributions:

```sh
sudo zypper install gettext-runtime python3-build python3-setuptools
```

#### Installing Test Dependencies

- On Debian/Ubuntu-based distributions:

```sh
sudo apt install pylint3 python3-pycodestyle
```

- On Redhat/Fedora-based distributions:

```sh
sudo dnf install pylint python3-pycodestyle
```

- On SUSE-based distributions:

```sh
sudo zypper install python3-pylint python3-pycodestyle
```

### Windows and macOS

All required dependencies are included in the [Nicotine+ Windows Installer](DOWNLOADS.md#windows) and [Nicotine+ macOS Installer](DOWNLOADS.md#macos) official release packages, no additional steps are required by a regular user in order to install stable versions of Nicotine+.

For developers who need to build packages with dependencies in a development environment, see [PACKAGING.md](PACKAGING.md).

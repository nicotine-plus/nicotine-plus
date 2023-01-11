# Dependencies

## Runtime

### Required

- [python3](https://www.python.org/) >= 3.6;
- [python3-gdbm](https://docs.python.org/3/library/dbm.html#module-dbm.gnu) for scanning shared files.
- [gtk3](https://gtk.org/) >= 3.22.30 or [gtk4](https://gtk.org/) >= 4.6.6 for graphical interface;
- [pygobject](https://pygobject.readthedocs.io/) for Python bindings for GTK;

### Recommended

- [gspell](https://gitlab.gnome.org/GNOME/gspell) for spell checking in chat.

## Building

- [gettext](https://www.gnu.org/software/gettext/) for generating translations;
- [setuptools](https://setuptools.pypa.io/) for packaging.

## Testing

- [flake8](https://flake8.pycqa.org/) for lint checks;
- [pylint](https://pylint.pycqa.org/) for lint checks.


## Installing Dependencies

### GNU/Linux

#### Installing Runtime Dependencies

- On Debian/Ubuntu-based distributions:

```sh
sudo apt install gir1.2-gspell-1 gir1.2-gtk-3.0 python3-gi python3-gdbm
```

- On Redhat/Fedora-based distributions:

```sh
sudo dnf install gspell gtk3 python3-gobject
```

- On SUSE-based distributions:

```sh
sudo zypper install typelib-1_0-Gspell-1 typelib-1_0-Gtk-3_0 python3-gobject python3-dbm
```

#### Installing Build Dependencies

- On Debian/Ubuntu-based distributions:

```sh
sudo apt install gettext python3-setuptools
```

- On Redhat/Fedora-based distributions:

```sh
sudo dnf install gettext python3-setuptools
```

- On SUSE-based distributions:

```sh
sudo zypper install gettext-runtime python3-setuptools
```

#### Installing Test Dependencies

- On Debian/Ubuntu-based distributions:

```sh
sudo apt install pylint3 python3-flake8
```

- On Redhat/Fedora-based distributions:

```sh
sudo dnf install pylint python3-flake8
```

- On SUSE-based distributions:

```sh
sudo zypper install python3-pylint python3-flake8
```

### Windows and macOS

All required dependencies are included in the [Nicotine+ Windows Installer](DOWNLOADS.md#windows) and [Nicotine+ macOS Installer](DOWNLOADS.md#macos) official release packages, no additional steps are required by a regular user in order to install stable versions of Nicotine+.

For developers who need to build packages with dependencies in a development environment, see [PACKAGING.md](PACKAGING.md).

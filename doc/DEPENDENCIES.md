# Dependencies

## Runtime

### Required

 - [python3](https://www.python.org/) >= 3.6
      for runtime language;
 - [gtk4](https://gtk.org/) >= 4.6.9 or [gtk3](https://gtk.org/) >= 3.22.30
      for graphical interface;
 - [pygobject](https://pygobject.gnome.org/)
      for Python bindings for GTK.

### Recommended

 - [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita)
      for Adwaita theme on GNOME (GTK 4);
 - [gspell](https://gitlab.gnome.org/GNOME/gspell)
      for spell checking in chat (GTK 3).

## Building

 - [python3-setuptools](https://setuptools.pypa.io/)
      for build backend;
 - [python3-build](https://build.pypa.io/)
      for building;
 - [python3-wheel](https://wheel.readthedocs.io/)
      for packaging;
 - [gettext](https://www.gnu.org/software/gettext/)
      for generating translations.

## Testing

 - [pycodestyle](https://pycodestyle.pycqa.org/)
      for code style checks;
 - [pylint](https://pylint.readthedocs.io/)
      for linting.


## Installing Dependencies

### GNU/Linux

#### Installing Runtime Dependencies

 - On Debian/Ubuntu-based distributions:

   ```sh
   sudo apt install gir1.2-gspell-1 gir1.2-gtk-4.0 gir1.2-adw-1 python3-gi python3-gi-cairo
   ```

 - On Redhat/Fedora-based distributions:

   ```sh
   sudo dnf install gspell gtk4 libadwaita python3-gobject
   ```

 - On SUSE-based distributions:

   ```sh
   sudo zypper install typelib-1_0-Gspell-1 typelib-1_0-Gtk-4_0 typelib-1_0-Adw-1 python312-gobject python312-gobject-cairo python312-gobject-Gdk
   ```

 - On Alpine-based distributions:

   ```sh
   sudo apk add gspell gtk4.0 libadwaita py3-gobject3
   ```

#### Installing Build Dependencies

 - On Debian/Ubuntu-based distributions:

   ```sh
   sudo apt install gettext python3-build python3-setuptools python3-wheel
   ```

 - On Redhat/Fedora-based distributions:

   ```sh
   sudo dnf install gettext python3-build python3-setuptools python3-wheel
   ```

 - On SUSE-based distributions:

   ```sh
   sudo zypper install gettext-tools python312-build python312-setuptools python312-wheel
   ```

 - On Alpine-based distributions:

   ```sh
   sudo apk add gettext py3-build py3-setuptools py3-wheel
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
   sudo zypper install python312-pylint python312-pycodestyle
   ```

 - On Alpine-based distributions:

   ```sh
   sudo apk add py3-pylint py3-pycodestyle
   ```

### Windows and macOS

All required dependencies are included in the [Nicotine+ Windows Installer](DOWNLOADS.md#windows)
and [Nicotine+ macOS Installer](DOWNLOADS.md#macos) official release packages,
no additional steps are required by a regular user in order to install stable
versions of Nicotine+.

For developers who need to build packages with dependencies in a development
environment, see [PACKAGING.md](PACKAGING.md).

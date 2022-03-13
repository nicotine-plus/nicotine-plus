# Testing Nicotine+

For those who like living on the bleeding edge, you can run the latest unstable build of Nicotine+ to test recent changes and bug fixes.

If you want to download the current stable version of Nicotine+, see [DOWNLOADS.md](DOWNLOADS.md).

## GNU/Linux, *BSD, Solaris

### Ubuntu/Debian

[Download a .deb package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/debian-package.zip) for Debian-based systems.

You need to download and install Nicotine+ from the link above every time you want to update to the latest unstable build.

### Flatpak

Unstable [Flatpak](https://www.flatpak.org/setup/) packages are built after every commit to the master branch.

- [Download Unstable Flatpak Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/flatpak-package.zip)

### pip

To install the latest unstable build of Nicotine+ using [pip](https://pip.pypa.io/), ensure the [runtime dependencies](DEPENDENCIES.md) are installed, and run the following:

```sh
pip install git+https://github.com/nicotine-plus/nicotine-plus.git@3.2.x
```

Nicotine+ will now be available in your list of programs.

To update to the latest unstable build of Nicotine+, run the following:

```sh
pip install --upgrade git+https://github.com/nicotine-plus/nicotine-plus.git@3.2.x
```

To uninstall Nicotine+, run:

```sh
pip uninstall nicotine-plus
```

### Git

To run Nicotine+ directly from a local [Git](https://git-scm.com/) folder, ensure the [runtime dependencies](DEPENDENCIES.md) are installed, and run the following:

```sh
git clone -b 3.2.x https://github.com/nicotine-plus/nicotine-plus.git
cd nicotine-plus
./nicotine
```

To update to the latest unstable build of Nicotine+, run the following:

```sh
cd nicotine-plus
git pull
```

## Windows

Unstable Windows packages are built after every commit to the master branch.

- [Download Unstable 64-bit Windows Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/windows-x86_64-installer.zip)
- [Download Unstable 32-bit Windows Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/windows-i686-installer.zip)

Portable packages are also available. They can be run from your home directory, and do not require installation or administrator privileges.

- [Download Unstable 64-bit Windows Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/windows-x86_64-package.zip)
- [Download Unstable 32-bit Windows Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/windows-i686-package.zip)

## macOS (Catalina/10.15 and newer)

Unstable macOS installers are built after every commit to the master branch.

- [Download Unstable macOS Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/macos-installer.zip)

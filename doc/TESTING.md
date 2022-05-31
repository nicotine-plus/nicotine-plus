# Testing

For those who like living on the bleeding edge, you can run the latest unstable build of Nicotine+ to test recent changes and bug fixes.

If you want to download the current stable version of Nicotine+, see [DOWNLOADS.md](DOWNLOADS.md).

## GNU/Linux, *BSD, Solaris

### Ubuntu/Debian

[Download a .deb package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/debian-package.zip) for Debian-based systems.

You need to download and install Nicotine+ from the link above every time you want to update to the latest unstable build.

### Other Distributions

#### Flatpak

Unstable [Flatpak](https://www.flatpak.org/setup/) packages are built after every commit to the 3.2.x branch.

- [Download Unstable Flatpak Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/flatpak-package.zip)

If Nicotine+ is not packaged for your system, the latest unstable build can be [installed using pip (see below)](#pip).

## Windows

Unstable Windows packages are built after every commit to the 3.2.x branch.

- [Download Unstable 64-bit Windows Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/windows-x86_64-installer.zip)
- [Download Unstable 32-bit Windows Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/windows-i686-installer.zip)

Portable packages are also available. They can be run from any folder and do not require installation or administrator privileges.

- [Download Unstable 64-bit Windows Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/windows-x86_64-package.zip)
- [Download Unstable 32-bit Windows Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/windows-i686-package.zip)

## macOS

Unstable installers for macOS Catalina 10.15 and newer are built after every commit to the 3.2.x branch.

- [Download Unstable macOS Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/macos-installer.zip)

## Cross-Platform

### pip

If Nicotine+ is not packaged for your system, the latest unstable build can be installed using [pip](https://pip.pypa.io/).

Installing Nicotine+ using pip on Windows requires a [MinGW environment](https://www.mingw-w64.org/). On macOS, this requires [Homebrew](https://brew.sh/). In other words, a Python installation from Python's website will not work for these platforms, therefore, it is recommended to use a supported Nicotine+ installer for [Windows](#windows) or [macOS](#macos) instead.

Ensure the [runtime dependencies](DEPENDENCIES.md) are installed, and run the following:

```sh
pip3 install git+https://github.com/nicotine-plus/nicotine-plus.git@3.2.x
```

Nicotine+ will now be available in your list of programs.

To update to the latest unstable build of Nicotine+, run the following:

```sh
pip3 install --upgrade git+https://github.com/nicotine-plus/nicotine-plus.git@3.2.x
```

To uninstall Nicotine+, run:

```sh
pip3 uninstall nicotine-plus
```

## Source

### Git

Running Nicotine+ using Git on Windows requires a [MinGW environment](https://www.mingw-w64.org/). On macOS, this requires [Homebrew](https://brew.sh/). It is recommended to use a supported Nicotine+ installer for [Windows](#windows) or [macOS](#macos) instead of building from source.

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

For information about Nicotine+ development procedures for maintainers, developers and code contributors, see [DEVELOPING.md](DEVELOPING.md).

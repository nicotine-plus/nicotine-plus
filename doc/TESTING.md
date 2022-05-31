# Testing

For those who like living on the bleeding edge, you can run the latest unstable build of Nicotine+ to test recent changes and bug fixes.

For information about Nicotine+ development procedures for maintainers, developers and code contributors, see [DEVELOPING.md](DEVELOPING.md).

If you want to download the current stable version of Nicotine+, see [DOWNLOADS.md](DOWNLOADS.md).


## GNU/Linux

### Ubuntu/Debian

[Download a .deb package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/debian-package.zip) for Debian-based systems.

You need to download and install Nicotine+ from the link above every time you want to update to the latest unstable build.

### Flatpak

Unstable [Flatpak](https://www.flatpak.org/setup/) packages are built after every commit to the 3.2.x branch.

- [Download Unstable Flatpak Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.2.x/flatpak-package.zip)

### Other

See [All Platforms](#all-platforms) for installing the unstable version of Nicotine+ on other distributions.


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


## All Platforms

The following installation methods work out of the box on GNU/Linux, *BSD and Solaris. On Windows, a [MinGW development environment](PACKAGING.md#windows) is required. On macOS, [Homebrew](PACKAGING.md#macos) is required. Consider using the Windows and macOS packages above if you do not need to modify the source code.

### pip

The latest unstable build of Nicotine+ can be installed using [pip](https://pip.pypa.io/). Ensure the [runtime dependencies](DEPENDENCIES.md) are installed, and run the following:

```sh
pip3 install git+https://github.com/nicotine-plus/nicotine-plus.git@3.2.x
```

To start Nicotine+:

```sh
nicotine
```

To update to the latest unstable build of Nicotine+, run the following:

```sh
pip3 install --upgrade git+https://github.com/nicotine-plus/nicotine-plus.git@3.2.x
```

To uninstall Nicotine+, run:

```sh
pip3 uninstall nicotine-plus
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

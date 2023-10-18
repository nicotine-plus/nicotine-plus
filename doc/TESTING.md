# Testing

For those who like living on the bleeding edge, you can run the latest unstable build of Nicotine+ to test recent changes and bug fixes.

For information about Nicotine+ development procedures for maintainers, developers and code contributors, see [DEVELOPING.md](DEVELOPING.md).

If you want to download the current stable version of Nicotine+, see [DOWNLOADS.md](DOWNLOADS.md).


## GNU/Linux

### Ubuntu/Debian

To use [unstable packages](https://launchpad.net/~nicotine-team/+archive/ubuntu/unstable) on Ubuntu and Debian, add the *nicotine-team/unstable* PPA repository.

On Ubuntu and distributions based on it (e.g. Linux Mint, elementary OS, Pop!_OS, various Ubuntu flavors), run the following:

```sh
sudo add-apt-repository ppa:nicotine-team/unstable
sudo apt update; sudo apt install nicotine
```

On Debian and distributions based on it (e.g. Devuan, Peppermint OS), run the following:

```sh
sudo apt update; sudo apt install python3-launchpadlib software-properties-common
sudo add-apt-repository 'deb https://ppa.launchpadcontent.net/nicotine-team/unstable/ubuntu jammy main'
sudo apt update; sudo apt install nicotine
```

If you prefer to install a .deb package directly, you can [download one here](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/debian-package.zip). Unlike the repository installation method, you need to download and install Nicotine+ from the link above every time you want to update to the latest unstable build.

### Flatpak

Unstable [Flatpak](https://www.flatpak.org/setup/) packages are built after every commit to the master branch.

- [Download Unstable Flatpak Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/flatpak-package-x86_64.zip)

### Other

See [All Platforms](#all-platforms) for installing the unstable version of Nicotine+ on other distributions.


## Windows

Unstable Windows packages are built after every commit to the master branch.

- [Download Unstable 64-bit Windows Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-installer.zip) [[Info](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-installer)]
- [Download Unstable 32-bit Windows Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-installer.zip) [[Info](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-installer)]

Standalone executables are also available. They can be run from any folder and do not require installation or administrator privileges. Configuration files are stored in `C:\Users\USERNAME\AppData\Roaming\nicotine`.

- [Download Unstable 64-bit Windows Standalone Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-package.zip) [[Info](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-package)]
- [Download Unstable 32-bit Windows Standalone Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-package.zip) [[Info](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-package)]

## macOS

Unstable installers for macOS Big Sur 11 and newer are built after every commit to the master branch.

- [Download Unstable macOS Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/macos-installer.zip) [[Info](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/macos-installer)]


## All Platforms

The following installation methods work out of the box on GNU/Linux, *BSD and Solaris. On Windows, a [MinGW development environment](PACKAGING.md#windows) is required. On macOS, [Homebrew](PACKAGING.md#macos) is required. Consider using the Windows and macOS packages above if you do not need to modify the source code.

### pip

The latest unstable build of Nicotine+ can be installed using [pip](https://pip.pypa.io/). Ensure the [runtime dependencies](DEPENDENCIES.md) are installed, and run the following:

```sh
pip3 install git+https://github.com/nicotine-plus/nicotine-plus.git
```

To start Nicotine+:

```sh
nicotine
```

To update to the latest unstable build of Nicotine+, run the following:

```sh
pip3 install --upgrade git+https://github.com/nicotine-plus/nicotine-plus.git
```

To uninstall Nicotine+, run:

```sh
pip3 uninstall nicotine-plus
```

### Git

To run Nicotine+ directly from a local [Git](https://git-scm.com/) folder, ensure the [runtime dependencies](DEPENDENCIES.md) are installed, and run the following:

```sh
git clone https://github.com/nicotine-plus/nicotine-plus.git
cd nicotine-plus
./nicotine
```

To update to the latest unstable build of Nicotine+, run the following:

```sh
cd nicotine-plus
git pull
```

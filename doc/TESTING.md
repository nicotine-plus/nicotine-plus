# Testing Nicotine+

For those who like living on the bleeding edge, you can run the latest unstable build of Nicotine+ to test recent changes and bug fixes.

If you want to download the current stable version of Nicotine+, see [DOWNLOADS.md](DOWNLOADS.md).

## GNU/Linux, *BSD, Solaris

### Flatpak

Unstable [Flatpak](https://www.flatpak.org/setup/) packages are built after every commit to the master branch.

- [Download Unstable Flatpak Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/flatpak-package.zip)

### Ubuntu/Debian

[Daily unstable snapshots](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-daily) are built in a separate [unstable PPA repository](https://code.launchpad.net/~nicotine-team/+archive/ubuntu/unstable). To install the latest unstable build of Nicotine+, run the following:

```sh
sudo apt install software-properties-common
sudo add-apt-repository ppa:nicotine-team/unstable
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6CEB6050A30E5769
sudo apt update
sudo apt install nicotine
```

If you prefer to install a .deb package directly, you can [download one here](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/debian-package.zip).

Unlike the repository installation method, you need to download and install Nicotine+ from the link above every time you want to update to the latest unstable build.

## Windows

Unstable Windows packages are built after every commit to the master branch.

- [Download Unstable 64-bit Windows Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-installer.zip) [[Info](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-installer)]
- [Download Unstable 32-bit Windows Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-installer.zip) [[Info](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-installer)]

Portable packages are also available. They can be run from your home directory, and do not require installation or administrator privileges.

- [Download Unstable 64-bit Windows Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-package.zip) [[Info](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-package)]
- [Download Unstable 32-bit Windows Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-package.zip) [[Info](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-package)]

## macOS (Catalina/10.15 and newer)

Unstable macOS installers are built after every commit to the master branch.

- [Download Unstable macOS Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/macos-installer.zip) [[Info](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/macos-installer)]

## Cross-Platform

### pip

Running Nicotine+ using pip requires a [MinGW environment](https://en.wikipedia.org/wiki/MinGW) on Windows and [Homebrew](https://brew.sh/) on macOS. Note that problems encountered using this installation method on OSes other than GNU/Linux variants are unlikely to receive support.

To install the latest unstable build of Nicotine+ using [pip](https://pip.pypa.io/), ensure the [runtime dependencies](DEPENDENCIES.md) are installed, and run the following:

```sh
pip install git+https://github.com/nicotine-plus/nicotine-plus.git
```

Nicotine+ will now be available in your list of programs.

To update to the latest unstable build of Nicotine+, run the following:

```sh
pip install --upgrade git+https://github.com/nicotine-plus/nicotine-plus.git
```

To uninstall Nicotine+, run:

```sh
pip uninstall nicotine-plus
```

## Source

### Git

Running Nicotine+ using Git requires a [MinGW environment](https://en.wikipedia.org/wiki/MinGW) on Windows and [Homebrew](https://brew.sh/) on macOS. Note that problems encountered using this installation method on OSes other than GNU/Linux variants are unlikely to receive support.

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

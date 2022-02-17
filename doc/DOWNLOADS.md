# Download Nicotine+

Download the current stable version of Nicotine+ for your operating system. For the release notes, see [NEWS.md](/NEWS.md).

If you want to download the latest unstable build and help test Nicotine+, see [TESTING.md](TESTING.md).

## GNU/Linux, *BSD, Solaris

### Ubuntu/Debian

To use [stable packages](https://launchpad.net/~nicotine-team/+archive/ubuntu/stable) on Ubuntu and Debian, add the *nicotine-team/stable* PPA repository by running the following:

```sh
sudo apt install software-properties-common
sudo add-apt-repository ppa:nicotine-team/stable
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6CEB6050A30E5769
sudo apt update
sudo apt install nicotine
```

If you prefer to install a .deb package directly, you can [download one here](http://ppa.launchpad.net/nicotine-team/stable/ubuntu/pool/main/n/nicotine/).

Unlike the repository installation method, you need to download and install Nicotine+ from the link above every time you want to update to the latest version.

### Fedora

To install Nicotine+ on Fedora, run the following:

```sh
sudo dnf install nicotine+
```

### Flatpak

If your Linux distribution supports [Flatpak](https://www.flatpak.org/setup/), you can install the current stable version of Nicotine+ from Flathub.

- [Download Nicotine+ from Flathub](https://flathub.org/apps/details/org.nicotine_plus.Nicotine)

### Arch Linux/Manjaro/Parabola

Nicotine+ is available in the community repository of Arch Linux, Manjaro and Parabola. To install, run the following:

```sh
sudo pacman -S nicotine+
```

### Void Linux

To install Nicotine+ on Void Linux, run the following:

```sh
sudo xbps-install -S nicotine+
```

### FreeBSD

To install Nicotine+ on FreeBSD, run the following:

```sh
pkg install py-nicotine-plus
```

### pip

If Nicotine+ is not packaged for your system, the current stable version can be installed using [pip](https://pip.pypa.io/). Ensure the [runtime dependencies](DEPENDENCIES.md) are installed, and run the following:

```sh
pip3 install nicotine-plus
```

Keep in mind that Nicotine+ will not update automatically. When a new release is available, run the following:

```sh
pip3 install --upgrade nicotine-plus
```

## Windows

### Official Release

Stable Windows installers for Nicotine+ are available for download. Installing Nicotine+ requires administrator privileges.

*NOTE: The installer format has changed since Nicotine+ 3.2.0. If you are upgrading from Nicotine+ 3.1.1 or earlier, please uninstall Nicotine+ first (this will not remove your existing settings).*

- [Download Nicotine+ 64-bit Windows Installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-installer.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-installer.zip.sha256)]
- [Download Nicotine+ 32-bit Windows Installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-installer.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-installer.zip.sha256)]

Portable packages are also available. They can be run from your home directory, and do not require installation or administrator privileges.

- [Download Nicotine+ 64-bit Windows Portable Package](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-package.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-package.zip.sha256)]
- [Download Nicotine+ 32-bit Windows Portable Package](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-package.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-package.zip.sha256)]

### Scoop

Nicotine+ can be installed using [Scoop](https://scoop.sh/). Run the following:

```sh
scoop bucket add extras
scoop install nicotine-plus
```

In order to upgrade Nicotine+ to a newer release, run the following:

```sh
scoop update nicotine-plus
```

### Chocolatey

Nicotine+ can be installed using [Chocolatey](https://community.chocolatey.org/packages/nicotine-plus). Run the following:

```sh
choco install nicotine-plus
```

## macOS

### Official Release (Catalina/10.15 and newer)

A stable macOS installer for Nicotine+ is available on macOS version 10.15 (Catalina) and newer.

- [Download Nicotine+ macOS Installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/macos-installer.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/macos-installer.zip.sha256)]

### Homebrew (Mojave/10.14 and newer)

*NOTE: If your Mac has an Apple M1 chip, please use the [official macOS installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/macos-installer.zip) instead. Installing Nicotine+ from Homebrew will currently not work on Apple M1 devices due to issues in upstream dependencies.*

On macOS version 10.14 (Mojave), the recommended approach is to install Nicotine+ using [Homebrew](https://brew.sh). Run the following:

```sh
brew install nicotine-plus
```

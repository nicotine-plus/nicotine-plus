# Downloads

Download the current stable version of Nicotine+ for your operating system.
For the release notes, see [NEWS.md](../NEWS.md).

If you want to download the latest unstable build and help test Nicotine+,
see [TESTING.md](TESTING.md).


## GNU/Linux, *BSD, Solaris

### Operating System Packages

If you are using any of the operating systems listed, you can install Nicotine+
using the package manager.

| Operating System                                                                         | Package Name               |
|------------------------------------------------------------------------------------------|----------------------------|
| [Alpine Linux Edge](https://pkgs.alpinelinux.org/packages?name=nicotine-plus)            | `nicotine-plus`            |
| [Arch Linux](https://archlinux.org/packages/extra/any/nicotine+/)                        | `nicotine+`                |
| [Chimera Linux](https://pkgs.chimera-linux.org/packages?name=nicotine-plus)              | `nicotine-plus`            |
| [Debian Unstable/Testing](https://tracker.debian.org/pkg/nicotine)                       | `nicotine`                 |
| [Fedora](https://packages.fedoraproject.org/pkgs/nicotine+/nicotine+/)                   | `nicotine+`                |
| [FreeBSD Ports](https://www.freshports.org/net-p2p/py-nicotine-plus)                     | `net-p2p/py-nicotine-plus` |
| [Gentoo](https://packages.gentoo.org/packages/net-p2p/nicotine+)                         | `net-p2p/nicotine+`        |
| [Mageia](https://madb.mageialinux-online.org/show?distribution=cauldron&rpm=nicotine%2B) | `nicotine+`                |
| [Manjaro](https://manjaristas.org/branch_compare?q=nicotine%2B)                          | `nicotine+`                |
| [NixOS](https://search.nixos.org/packages?show=nicotine-plus)                            | `nicotine-plus`            |
| [OpenBSD Ports](https://openports.pl/path/net/nicotine-plus)                             | `net/nicotine-plus`        |
| [OpenMandriva](https://github.com/OpenMandrivaAssociation/nicotineplus)                  | `nicotine+`                |
| [Parabola](https://www.parabola.nu/packages/extra/x86_64/nicotine+/)                     | `nicotine+`                |
| [PLD Linux](https://git.pld-linux.org/?p=packages/nicotine.git;a=tree)                   | `nicotine`                 |
| [Solus](https://github.com/getsolus/packages/tree/main/packages/n/nicotine-plus)         | `nicotine-plus`            |
| [T2 SDE](https://t2sde.org/packages/nicotine-plus)                                       | `nicotine-plus`            |
| [Void Linux](https://github.com/void-linux/void-packages/tree/master/srcpkgs/nicotine+)  | `nicotine+`                |

### Universal Packages (GNU/Linux)

Packages listed below can be installed on different GNU/Linux distributions.

| Format                                                                           | Package Name                 |
|----------------------------------------------------------------------------------|------------------------------|
| [Flatpak](https://flathub.org/apps/details/org.nicotine_plus.Nicotine)           | `org.nicotine_plus.Nicotine` |
| [Snap](https://snapcraft.io/nicotine-plus)                                       | `nicotine-plus`              |

### PPA (Ubuntu/Debian)

To use [stable packages](https://launchpad.net/~nicotine-team/+archive/ubuntu/stable)
on Ubuntu and Debian, add the *nicotine-team/stable* PPA repository.

On Ubuntu and distributions based on it (e.g. Linux Mint, elementary OS,
Pop!_OS, various Ubuntu flavors), run the following:

```sh
sudo add-apt-repository ppa:nicotine-team/stable
sudo apt update; sudo apt install nicotine
```

On Debian and distributions based on it (e.g. Devuan, Peppermint OS), run the
following:

```sh
sudo apt update; sudo apt install python3-launchpadlib software-properties-common
sudo add-apt-repository 'deb https://ppa.launchpadcontent.net/nicotine-team/stable/ubuntu jammy main'
sudo apt update; sudo apt install nicotine
```

If you prefer to install a .deb package manually, you can
[download one here](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/debian-package.zip).

> **NOTE**: When installing the .deb package manually, Nicotine+ will not
> update automatically. You need to download and install the latest version
> from the link above after every update.

### PyPi (GNU/Linux, *BSD, Solaris)

If no package is available for your operating system, you can install Nicotine+
from [PyPi](https://pypi.org/project/nicotine-plus/).

Ensure the [runtime dependencies](DEPENDENCIES.md) are installed, and run the
following:

```sh
pip3 install nicotine-plus
```

Keep in mind that Nicotine+ will not update automatically. When a new release
is available, run the following:

```sh
pip3 install --upgrade nicotine-plus
```


## Windows

### Official Release

Stable installers are available for download.

 - [Download Windows Installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-installer.zip)
    — [`SHA256`](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-installer.zip.sha256)  
   for Windows 10 or later

Standalone executables are also available. They can be run from any folder and
do not require installation.

 - [Download Windows Standalone Package](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-package.zip)
    — [`SHA256`](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-package.zip.sha256)  
   for Windows 10 or later

> **IMPORTANT**: The installer format has changed since Nicotine+ 3.2.0. If you
> are upgrading from Nicotine+ 3.1.1 or earlier, please uninstall Nicotine+
> first (this will not remove your existing settings).

> **NOTE**: Configuration files are always stored in  
> *C:\Users\\<USERNAME\>\AppData\Roaming\nicotine*

### Package Managers

If you are using any of the package managers listed, you can install Nicotine+
using them.

| Package Manager                                                                                    | Package Name           |
|----------------------------------------------------------------------------------------------------|------------------------|
| [Chocolatey](https://community.chocolatey.org/packages/nicotine-plus)                              | `nicotine-plus`        |
| [Scoop](https://github.com/ScoopInstaller/Extras/blob/master/bucket/nicotine-plus.json)            | `extras/nicotine-plus` |
| [Winget](https://github.com/microsoft/winget-pkgs/tree/master/manifests/n/Nicotine%2B/Nicotine%2B) | `nicotine+.nicotine+`  |


## macOS

### Official Release

> **IMPORTANT**: You must follow [these instructions](https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unidentified-developer-mh40616/mac)
> the first time you start Nicotine+.

 - [Download macOS Intel Installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/macos-x86_64-installer.zip)
    — [`SHA256`](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/macos-x86_64-installer.zip.sha256)  
   for macOS 13 Ventura or later

 - [Download macOS Apple Silicon Installer](https://github.com/nicotine-plus/nicotine-plus/releases/download/3.3.6/macos-arm64-installer.zip)
    — [`SHA256`](https://github.com/nicotine-plus/nicotine-plus/releases/download/3.3.6/macos-arm64-installer.zip.sha256)  
   for macOS 14 Sonoma or later

### Package Managers

If you are using any of the package managers listed, you can install Nicotine+
using them.

| Package Manager                                                     | Package Name    |
|---------------------------------------------------------------------|-----------------|
| [Homebrew Formulae](https://formulae.brew.sh/formula/nicotine-plus) | `nicotine-plus` |
| [MacPorts](https://ports.macports.org/port/nicotine-plus/)          | `nicotine-plus` |

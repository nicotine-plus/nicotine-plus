<!--
  SPDX-FileCopyrightText: 2016-2026 Nicotine+ Contributors
  SPDX-License-Identifier: GPL-3.0-or-later
-->

# Testing

For those who like living on the bleeding edge, you can run the latest test
build of Nicotine+ to test recent changes and bug fixes.

For information about Nicotine+ development procedures for maintainers,
developers and code contributors, see [DEVELOPING.md](DEVELOPING.md).

If you want to download the current stable version of Nicotine+, see
[DOWNLOADS.md](DOWNLOADS.md).


## GNU/Linux

### PPA (Ubuntu/Debian)

To use [the latest 3.4.0.dev1 packages](https://launchpad.net/~nicotine-team/+archive/ubuntu/unstable)
on Ubuntu and Debian, add the *nicotine-team/unstable* PPA repository.

On Ubuntu and distributions based on it (e.g. Linux Mint, elementary OS,
Pop!_OS, various Ubuntu flavors), run the following:

```sh
sudo add-apt-repository ppa:nicotine-team/unstable
sudo apt update; sudo apt install nicotine
```

On Debian and distributions based on it (e.g. Devuan, Peppermint OS), run the
following:

```sh
sudo apt update; sudo apt install python3-launchpadlib software-properties-common
sudo add-apt-repository 'deb https://ppa.launchpadcontent.net/nicotine-team/unstable/ubuntu jammy main'
sudo apt update; sudo apt install nicotine
```

If you prefer to install a .deb package directly, you can [download one here (for 3.3.11rc1)](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/debian-package.zip)
or [here (for 3.4.0.dev1)](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/debian-package.zip).
Unlike the repository installation method, you need to download and install
Nicotine+ from the link above every time you want to update to the latest build.

### Flatpak

The latest [Flatpak](https://www.flatpak.org/setup/) packages are built after
every commit.

 - [Download 3.3.11rc1 Flatpak x64 Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/flatpak-x86_64-package.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/flatpak-x86_64-package)  

 - [Download 3.3.11rc1 Flatpak ARM64 Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/flatpak-aarch64-package.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/flatpak-aarch64-package)  

 - [Download 3.4.0.dev1 Flatpak x64 Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/flatpak-x86_64-package.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/flatpak-x86_64-package)  

 - [Download 3.4.0.dev1 Flatpak ARM64 Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/flatpak-aarch64-package.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/flatpak-aarch64-package)  

### Snap

The latest [Snap](https://snapcraft.io/docs/installing-snapd) packages for
3.4.0.dev1 are published in the Snap Store, and can be installed by running
the following:

```sh
sudo snap install nicotine-plus --edge
```

### Other

See [All Platforms](#all-platforms) for installing the test build of Nicotine+
on other distributions.


## Windows

The latest installers are built after every commit.

 - [Download 3.3.11rc1 Windows x64 Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/windows-x86_64-installer.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/windows-x86_64-installer)  
   for Windows 10 or later

 - [Download 3.3.11rc1 Windows ARM64 Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/windows-arm64-installer.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/windows-arm64-installer)  
   for Windows 11 or later

 - [Download 3.4.0.dev1 Windows x64 Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-installer.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-installer)  
   for Windows 10 or later

 - [Download 3.4.0.dev1 Windows ARM64 Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-arm64-installer.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-arm64-installer)  
   for Windows 11 or later

Portable packages for 3.4.0.dev1 are also available. They can be run from any
folder and do not require installation. User data files are stored in a
`portable\data` folder next to the executable.

> **IMPORTANT**: If you are upgrading from the standalone package, and wish to
> use your previous data files, you can rename the
> `C:\Users\<USERNAME>\AppData\Roaming\nicotine` folder to `data`, and place it
> inside the `portable` folder next to the executable. Alternatively, remove
> the `portable` folder to continue using the old AppData path.

 - [Download 3.4.0.dev1 Windows x64 Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-portable.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-portable)  
   for Windows 10 or later

 - [Download 3.4.0.dev1 Windows ARM64 Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-arm64-portable.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-arm64-portable)  
   for Windows 11 or later

Standalone packages are available for 3.3.11rc1. They always store user data
files in `C:\Users\<USERNAME>\AppData\Roaming\nicotine`.

 - [Download 3.3.11rc1 Windows x64 Standalone Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/windows-x86_64-package.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/windows-x86_64-package)  
   for Windows 10 or later

 - [Download 3.3.11rc1 Windows ARM64 Standalone Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/windows-arm64-package.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/windows-arm64-package)  
   for Windows 11 or later


## macOS

The latest installers are built after every commit.

> **IMPORTANT**: You must follow [these instructions](https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unidentified-developer-mh40616/mac)
> the first time you start Nicotine+.

 - [Download 3.3.11rc1 macOS Intel Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/macos-x86_64-installer.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/macos-x86_64-installer)  
   for macOS 11 Big Sur or later

 - [Download 3.3.11rc1 macOS Apple Silicon Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/macos-arm64-installer.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/3.3.x/macos-arm64-installer)  
   for macOS 11 Big Sur or later

 - [Download 3.4.0.dev1 macOS Intel Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/macos-x86_64-installer.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/macos-x86_64-installer)  
   for macOS 11 Big Sur or later

 - [Download 3.4.0.dev1 macOS Apple Silicon Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/macos-arm64-installer.zip)
    — [`INFO`](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/macos-arm64-installer)  
   for macOS 11 Big Sur or later


## All Platforms

The following installation methods work out of the box on GNU/Linux, *BSD and
illumos. On Windows, a [MinGW development environment](PACKAGING.md#windows) is
required. On macOS, [Homebrew](PACKAGING.md#macos) is required. Consider using
the Windows and macOS packages above if you do not need to modify the source
code.

### pip

The latest test build of Nicotine+ can be installed using
[pip](https://pip.pypa.io/). Ensure the [runtime dependencies](DEPENDENCIES.md)
are installed, and run the following:

For testing 3.3.11rc1:

```sh
pip3 install git+https://github.com/nicotine-plus/nicotine-plus.git@3.3.x
```

For testing 3.4.0.dev1:

```sh
pip3 install git+https://github.com/nicotine-plus/nicotine-plus.git
```

To start Nicotine+:

```sh
nicotine
```

To update to the latest test build of Nicotine+, run the following:

For 3.3.11rc1:

```sh
pip3 install --upgrade git+https://github.com/nicotine-plus/nicotine-plus.git@3.3.x
```

For 3.4.0.dev1:

```sh
pip3 install --upgrade git+https://github.com/nicotine-plus/nicotine-plus.git
```

To uninstall Nicotine+, run:

```sh
pip3 uninstall nicotine-plus
```

### Git

To run Nicotine+ directly from a local [Git](https://git-scm.com/) folder,
ensure the [runtime dependencies](DEPENDENCIES.md) are installed, and run the
following:

For testing 3.3.11rc1:

```sh
git clone https://github.com/nicotine-plus/nicotine-plus.git -b 3.3.x
cd nicotine-plus
./nicotine
```

For testing 3.4.0.dev1:

```sh
git clone https://github.com/nicotine-plus/nicotine-plus.git
cd nicotine-plus
./nicotine
```

To update to the latest test build of Nicotine+, run the following:

```sh
cd nicotine-plus
git pull
```

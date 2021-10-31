# Download Nicotine+

Download stable builds of Nicotine+ for your operating system.

## GNU/Linux, *BSD, Solaris

If you have no need to modify the Nicotine+ source, you are strongly recommended to use packages for your distribution/operating system. This will save you time.

### Ubuntu/Debian

To use [stable packages](https://launchpad.net/~nicotine-team/+archive/ubuntu/stable) on Ubuntu and Debian, add the stable Nicotine+ apt repository (PPA) by running the following:

```sh
sudo apt install software-properties-common
sudo add-apt-repository ppa:nicotine-team/stable
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6CEB6050A30E5769
sudo apt update
sudo apt install nicotine
```

If you prefer to install a .deb package directly, you can download one [here](http://ppa.launchpad.net/nicotine-team/stable/ubuntu/pool/main/n/nicotine/). Unlike the repository installation method, Nicotine+ will not update automatically; you need to download a .deb package each time a new release is available.

### Fedora

To install Nicotine+ on Fedora, run the following:

```sh
sudo dnf install nicotine+
```

### Flatpak

If your distribution supports Flatpak, you can install Nicotine+ from Flathub.

- [Download Nicotine+ on Flathub](https://flathub.org/apps/details/org.nicotine_plus.Nicotine)

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

### pip

Nicotine+ can be installed using [pip](https://pip.pypa.io/en/stable/). Ensure the [runtime dependencies](doc/DEPENDENCIES.md) are installed, and run the following:

```sh
pip3 install nicotine-plus
```

Keep in mind that Nicotine+ will not auto-update. When a new release is available, run the following:

```sh
pip3 install --upgrade nicotine-plus
```

## Windows

### Official Builds

Stable Windows installers for Nicotine+ are available for download. Installing Nicotine+ requires administrator privileges.

- [64-bit Installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-installer.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-installer.zip.sha256)]
- [32-bit Installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-installer.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-installer.zip.sha256)]

Portable packages are also available. They can be run from your home directory, and do not require installation or administrator privileges.

- [64-bit Portable Package](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-package.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-package.zip.sha256)]
- [32-bit Portable Package](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-package.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-package.zip.sha256)]

### Chocolatey

Nicotine+ can be installed using [Chocolatey](https://community.chocolatey.org/packages/nicotine-plus). Run the following:

```sh
choco install nicotine-plus
```

## macOS

### Official Builds (Catalina/10.15 and newer)

A stable macOS installer for Nicotine+ is available on macOS version 10.15 (Catalina) and newer.

- [Download Installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/macos-installer.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/macos-installer.zip.sha256)]

### Homebrew (Mojave/10.14 and newer)

On macOS version 10.14 (Mojave), the recommended approach is to install Nicotine+ using [Homebrew](https://brew.sh).

Once Homebrew is set up, run the following:

```sh
brew install nicotine-plus
```

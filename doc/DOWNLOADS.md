# Download Nicotine+

## GNU/Linux, *BSD, Solaris

If you have no need to modify the Nicotine+ source, you are strongly recommended to use packages for your distribution/operating system. This will save you time.

### Ubuntu/Debian (Stable)

To use [stable packages](https://launchpad.net/~nicotine-team/+archive/ubuntu/stable) on Ubuntu and Debian, add the stable Nicotine+ apt repository (PPA) by running the following:

```sh
sudo apt install software-properties-common
sudo add-apt-repository ppa:nicotine-team/stable
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6CEB6050A30E5769
sudo apt update
sudo apt install nicotine
```

If you prefer to install a .deb package directly, you can download one [here](http://ppa.launchpad.net/nicotine-team/stable/ubuntu/pool/main/n/nicotine/). Unlike the repository installation method, Nicotine+ will not update automatically; you need to download a .deb package each time a new release is available.

### Ubuntu/Debian (Unstable)

The project builds [daily unstable snapshots](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-daily) in a separate [unstable PPA](https://code.launchpad.net/~nicotine-team/+archive/ubuntu/unstable). To use it, run the following:

```sh
sudo apt install software-properties-common
sudo add-apt-repository ppa:nicotine-team/unstable
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6CEB6050A30E5769
sudo apt update
sudo apt install nicotine
```

If you prefer to install a .deb package directly, you can download one [here](http://ppa.launchpad.net/nicotine-team/unstable/ubuntu/pool/main/n/nicotine/). Unlike the repository installation method, Nicotine+ will not update automatically; you need to download a .deb package each time a new release is available.

### Arch Linux/Manjaro/Parabola (Stable)

Nicotine+ is available in the community repository of Arch Linux, Manjaro and Parabola. To install, run the following:

```sh
sudo pacman -S nicotine+
```

### Void Linux (Stable)

To install Nicotine+ on Void Linux, run the following:

```sh
sudo xbps-install -S nicotine+
```

### Fedora (Stable)

To install Nicotine+ on Fedora, run the following:

```sh
sudo dnf install nicotine+
```

### Other Distributions

If Nicotine+ has not been packaged for your distribution/operating system yet, there are other recommended ways of installing Nicotine+.

#### pip (Stable)

Nicotine+ can be installed using [pip](https://pip.pypa.io/en/stable/). Ensure the [runtime dependencies](doc/DEPENDENCIES.md) are installed, and run the following:

```sh
pip3 install nicotine-plus
```

Keep in mind that Nicotine+ will not update automatically. When a new release is available, run the following:

```sh
pip3 install nicotine-plus --upgrade
```

#### Flatpak (Stable)

If your distribution supports Flatpak, you can install Nicotine+ from Flathub.

- [Download Nicotine+ on Flathub](https://flathub.org/apps/details/org.nicotine_plus.Nicotine)

#### Flatpak (Unstable)

Unstable Flatpak packages are generated after every commit to the master branch, and should only be used for testing.

- [Download Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/flatpak-package.zip)

## Windows

### Stable

Stable Windows installers for Nicotine+ are available for download. Installing Nicotine+ requires administrator privileges.

- [64-bit Installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-installer.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-installer.zip.sha256)]
- [32-bit Installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-installer.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-installer.zip.sha256)]

Portable packages are also available. They can be run from your home directory, and do not require installation or administrator privileges.

- [64-bit Portable Package](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-package.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-x86_64-package.zip.sha256)]
- [32-bit Portable Package](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-package.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/windows-i686-package.zip.sha256)]

### Unstable

Unstable Windows packages are generated after every commit to the master branch, and should only be used for testing.

- [64-bit Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-installer.zip)
- [32-bit Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-installer.zip)

Portable packages are also available. They can be run from your home directory, and do not require installation or administrator privileges.

- [64-bit Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-package.zip)
- [32-bit Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-package.zip)

### Chocolatey (Stable)

Nicotine+ can be installed using [Chocolatey](https://community.chocolatey.org/packages/nicotine-plus). Run the following:

```sh
choco install nicotine-plus
```

## macOS

### Stable (Catalina/10.15 and newer)

A stable macOS installer for Nicotine+ is available on macOS version 10.15 (Catalina) and newer.

- [Download Installer](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/macos-installer.zip)  [[SHA256](https://github.com/nicotine-plus/nicotine-plus/releases/latest/download/macos-installer.zip.sha256)]

### Stable (Mojave/10.14)

On macOS version 10.14 (Mojave), the recommended approach is to install Nicotine+ using [Homebrew](https://brew.sh).

Once Homebrew is set up, run the following:

```sh
brew install nicotine-plus
```

### Unstable (Catalina/10.15 or newer)

Unstable macOS installers are generated after every commit to the master branch, and should only be used for testing.

- [Download Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/macos-installer.zip)

## Building from git (Unstable)

For more experienced users and developers who want to test the latest and greatest changes in Nicotine+, building from git is described in [RUNFROMGIT.md](doc/RUNFROMGIT.md). Also read the next section about getting involved.

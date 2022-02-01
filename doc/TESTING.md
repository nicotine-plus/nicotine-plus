# Testing Nicotine+

For those who like living on the bleeding edge, you can run the latest unstable build of Nicotine+ to test recent changes and bug fixes.

If you want to download the current stable version of Nicotine+, see [DOWNLOADS.md](DOWNLOADS.md).

## GNU/Linux, *BSD, Solaris

### Ubuntu/Debian

The project builds [daily unstable snapshots](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-daily) in a separate [unstable PPA repository](https://code.launchpad.net/~nicotine-team/+archive/ubuntu/unstable). To use it, run the following:

```sh
sudo apt install software-properties-common
sudo add-apt-repository ppa:nicotine-team/unstable
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6CEB6050A30E5769
sudo apt update
sudo apt install nicotine
```

If you prefer to install a .deb package directly, you can download one [here](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/debian-package.zip).

Unlike the repository installation method, Nicotine+ will not update automatically unless you download and install it again.

### Flatpak

Unstable [Flatpak](https://www.flatpak.org/setup/) packages are generated after every commit to the master branch, and should only be used for testing.

- [Download Nicotine+ Flatpak Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/flatpak-package.zip)

### pip

To install the latest unstable build of Nicotine+ locally (no root required) using [pip](https://pip.pypa.io/), run the following:

```console
pip install git+https://github.com/nicotine-plus/nicotine-plus.git
```

Nicotine+ will now be available in your list of programs.

To update to newer versions of Nicotine+, run the following command:

```console
pip install --upgrade git+https://github.com/nicotine-plus/nicotine-plus.git
```

To uninstall Nicotine+, run:
```console
pip uninstall nicotine-plus
```

### Git

This is not particularly difficult, but may require some [dependancies](DEPENDENCIES.md) to be installed manually.

To run Nicotine+ directly from a local [Git](https://git-scm.com/) folder, run the following:

```console
git clone https://github.com/nicotine-plus/nicotine-plus.git
cd nicotine-plus
./nicotine
```

To update to newer versions of Nicotine+, run the following:

```console
cd nicotine-plus
git pull
```

## Windows

Unstable Windows packages are generated after every commit to the master branch, and should only be used for testing.

- [Download Nicotine+ 64-bit Windows Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-installer.zip)
- [Download Nicotine+ 32-bit Windows Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-installer.zip)

Portable packages are also available. They can be run from your home directory, and do not require installation or administrator privileges.

- [Download Nicotine+ 64-bit Windows Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-package.zip)
- [Download Nicotine+ 32-bit Windows Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-package.zip)

## macOS (Catalina/10.15 and newer)

Unstable macOS installers are generated after every commit to the master branch, and should only be used for testing.

- [Download Nicotine+ macOS Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/macos-installer.zip)

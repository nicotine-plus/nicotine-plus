# Testing Nicotine+

For those who like living on the bleeding edge and want to help testing the latest changes and bug fixes, you can run unstable builds of Nicotine+.
This is not particularly difficult, but may come with some additional required skills, like managing changes in the database and the config files.

## GNU/Linux, *BSD, Solaris

If you have no need to modify the Nicotine+ source, you should use packages for your distribution/operating system.

### Ubuntu/Debian

The project builds [daily unstable snapshots](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-daily) in a separate [unstable PPA](https://code.launchpad.net/~nicotine-team/+archive/ubuntu/unstable). To use it, run the following:

```sh
sudo apt install software-properties-common
sudo add-apt-repository ppa:nicotine-team/unstable
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6CEB6050A30E5769
sudo apt update
sudo apt install nicotine
```

If you prefer to install a .deb package directly, you can download one [here](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/debian-package.zip). Unlike the repository installation method, Nicotine+ will not update automatically; you need to download a .deb package each time a new release is available.

### Flatpak

Unstable Flatpak packages are generated after every commit to the master branch, and should only be used for testing.

- [Download Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/flatpak-package.zip)

### pip

To install the latest unstable build of Nicotine+ locally (no root required), run the following:

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

To run Nicotine+ directly from a local Git folder, run the following:

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

- [64-bit Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-installer.zip)
- [32-bit Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-installer.zip)

Portable packages are also available. They can be run from your home directory, and do not require installation or administrator privileges.

- [64-bit Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-x86_64-package.zip)
- [32-bit Portable Package](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/windows-i686-package.zip)

## macOS (Catalina/10.15 and newer)

Unstable macOS installers are generated after every commit to the master branch, and should only be used for testing.

- [Download Installer](https://nightly.link/nicotine-plus/nicotine-plus/workflows/packaging/master/macos-installer.zip)

## Stable builds

If you want to download the current stable version of Nicotine+, see [DOWNLOADS.md](DOWNLOADS.md).

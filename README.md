# Nicotine+

Nicotine+ is a graphical client for the [Soulseek](https://www.slsknet.org/news/) peer-to-peer file sharing network.

Nicotine+ aims to be a pleasant, Free and Open Source (FOSS) alternative to the official Soulseek client, providing additional functionality while keeping current with the Soulseek protocol.

[Screenshots](files/screenshots/SCREENSHOTS.md)

# Download Nicotine+
The current stable version of Nicotine+ is 2.1.1, released on 26 September 2020. See the [changelog](NEWS.md).

## GNU/Linux
If you have no need to modify the Nicotine+ source, you are strongly recommended to use precompiled packages for your distribution. This will save you time.

### Ubuntu PPA (Stable)
This repository also should work on Debian or any of its derivatives, provided dependencies can be satisfied. As an example Debian Buster works fine.

To use [stable packages](https://launchpad.net/~nicotine-team/+archive/ubuntu/stable), run the following:

```console
$ sudo apt install software-properties-common
$ sudo add-apt-repository ppa:nicotine-team/stable
$ sudo apt update
$ sudo apt install nicotine
```

### Ubuntu PPA (Unstable)
The project builds [daily unstable snapshots](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-daily) in a separate [unstable PPA](https://code.launchpad.net/~nicotine-team/+archive/ubuntu/unstable). It currently contains bleeding edge packages for _Xenial_, _Bionic_, _Focal_, and _Groovy_. To use it, run the following:

```console
$ sudo apt install software-properties-common
$ sudo add-apt-repository ppa:nicotine-team/unstable
$ sudo apt update
$ sudo apt install nicotine
```

### Arch Linux/Manjaro/Parabola (Stable)
Nicotine+ is available in the community repository of Arch Linux, Manjaro and Parabola. To install, run the following:

```console
$ sudo pacman -S nicotine+
```

### Void Linux (Stable)
To install Nicotine+ on Void Linux, run the following:

```console
$ sudo xbps-install -S nicotine+
```

### Fedora (Stable)
To install Nicotine+ on Fedora, run the following:

```console
$ sudo dnf install nicotine+
```

### Guix (Stable)
To install Nicotine+ on Guix, run the following:

```console
$ guix install nicotine+
```

### Flathub (Stable)
[Download Nicotine+ on Flathub](https://flathub.org/apps/details/org.nicotine_plus.Nicotine)

### Other Distributions
Package maintainers, please insert instructions for users to install pre-compiled packages from your respective repositories here.

## Windows

### Stable

You can download stable Windows packages here:

- [64-bit Installer](https://github.com/Nicotine-Plus/nicotine-plus/releases/download/2.1.1/Nicotine+-2.1.1-x86_64.exe)
- [32-bit Installer](https://github.com/Nicotine-Plus/nicotine-plus/releases/download/2.1.1/Nicotine+-2.1.1-i686.exe)

### Unstable

Unstable Windows packages are generated after every commit to the master branch, and should only be used for testing. You need to be signed into a GitHub account to download the packages.

- [64/32-bit Installers / Packages](https://github.com/Nicotine-Plus/nicotine-plus/actions?query=branch%3Amaster+event%3Apush+is%3Asuccess+workflow%3A%22Packaging%22)

## macOS

### Unstable

Unstable MacOS packages are generated after every commit to the master branch, and should only be used for testing. You need to be signed into a GitHub account to download the packages.

Please note that we haven't been able to test these packages. Please let us know about any potential issues.

- [Download Installer / Package](https://github.com/Nicotine-Plus/nicotine-plus/actions?query=branch%3Amaster+event%3Apush+is%3Asuccess+workflow%3A%22Packaging%22)

## Building from git (Unstable)
For more experienced users and developers who want to test the latest and greatest changes in Nicotine+, building from git is described in [RUNFROMGIT.md](doc/RUNFROMGIT.md). Also read the next section about getting involved.

# Getting Involved
Please come and join us in the `#nicotine+` channel on Freenode!

If you'd like to contribute, you have a couple of options to get started:

* If you'd like to translate Nicotine+ into another language it has not been already, see [TRANSLATIONS.md](doc/TRANSLATIONS.md).
* If you find a problem or have a feature request you can
  * discuss your findings on the `#nicotine+` channel on the [freenode IRC-Network](https://webchat.freenode.net/)
  * [create a new issue](https://github.com/Nicotine-Plus/nicotine-plus/issues) on GitHub, 
  * or post to the project [mailing list](mailto:nicotine-team@lists.launchpad.net).
* Developers are also encouraged to join the [Launchpad Team](https://launchpad.net/~nicotine-team) or subscribe to the mailing list so that they are automatically notified of failed commits.
* For (unofficial) documentation of the Soulseek protocol, see [SLSKPROTOCOL.md](doc/SLSKPROTOCOL.md)
* For a current list of things to do, see the [issue tracker](https://github.com/Nicotine-Plus/nicotine-plus/issues).
* If you want to contact someone, see [MAINTAINERS.md](AUTHORS.md).

# Continuous Integration Testing

It is important that all patches pass unit testing. Unfortunately developers make all kinds of changes to their local development environment that can have unintended consequences. This means sometimes tests on the developer's computer pass when they should not, and other times failing when they should not have. 

To properly validate that things are working, continuous integration (CI) is required. This means compiling, performing local in-tree unit tests, installing through the system package manager, and finally testing the actually installed build artifacts to ensure they do what the user expects them to do.

The key thing to remember is that in order to do this properly, this all needs to be done within a realistic end user system that hasn't been unintentionally modified by a developer. This might mean a chroot container with the help of QEMU and KVM to verify that everything is working as expected. The hermetically sealed test environment validates that the developer's expected steps for, as an example in the case of a library, compilation, linking, unit testing, and post installation testing are actually replicable.

There are [different ways](https://wiki.debian.org/qa.debian.org#Other_distributions) of performing CI on different distros. The most common one is via the international [DEP-8](https://dep-team.pages.debian.net/deps/dep8/) standard as used by hundreds of different operating systems.

## Autopkgtest
On Debian based distributions, `autopkgtest` implements the DEP-8 standard. To create and use a build image environment for Ubuntu, follow these steps. First install the autopkgtest(1) tools:
```
$ sudo apt install autopkgtest
```

Next create the test image, substituting `focal` or `amd64` for other releases or architectures:
```
$ autopkgtest-buildvm-ubuntu-cloud -r focal -a amd64
```

Generate a Nicotine+ source package in the parent directory of `nicotine_source`:
```
$ cd nicotine_source
$ sudo apt build-dep nicotine
$ ./debian/rules get-orig-source
$ debuild -S -sa
```

Test the source package on the host architecture in QEMU with KVM support and 8GB of RAM and four CPUs:
```
$ autopkgtest --shell-fail --apt-upgrade ../nicotine_(...).dsc -- \
      qemu --ram-size=8192 --cpus=4 --show-boot path_to_build_image.img \
      --qemu-options='-enable-kvm'
```

# Legal and Privacy

- By using Nicotine+, you agree to abide by the Soulseek [rules](https://www.slsknet.org/news/node/681) and [terms of service](https://www.slsknet.org/news/node/682), as long as you are using the official Soulseek server.
- While Nicotine+ does not collect any user data, the official Soulseek server or a user-configured third-party server may potentially do so.

# License

Nicotine+ is released under the terms of the [GNU Public License v3](https://www.gnu.org/licenses/gpl-3.0-standalone.html) or later.

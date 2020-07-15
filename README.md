# Nicotine+

Nicotine+ is a graphical client for the [Soulseek](https://www.slsknet.org/news/) peer-to-peer file sharing network. It is an attempt to keep [Nicotine](https://web.archive.org/web/20150720173459/http://nicotine.thegraveyard.org/) working with the latest libraries, kill bugs, keep current with the Soulseek protocol, and add some new features that users want and/or need.

[Screenshots](files/screenshots/SCREENSHOTS.md)

# Download Nicotine+
The current stable version of Nicotine+ is 2.0.0, released on 14 July 2020. See the [changelog](NEWS).

## GNU/Linux
If you have no need to modify the Nicotine+ source, you are strongly recommended to use precompiled packages for your distribution. This will save you time.

### Ubuntu PPA (Stable)
To use [stable packages](https://launchpad.net/~nicotine-team/+archive/ubuntu/stable), run the following:

```console
$ sudo add-apt-repository ppa:nicotine-team/stable
$ sudo apt update
$ sudo apt install nicotine
```

### Ubuntu PPA (Unstable)
The project builds [daily unstable snapshots](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-daily) in a separate [unstable PPA](https://code.launchpad.net/~nicotine-team/+archive/ubuntu/unstable). It currently contains bleeding edge packages for _Xenial_, _Bionic_, _Eoan_, _Focal_, and _Groovy_. To use it, run the following:

```console
$ sudo add-apt-repository ppa:nicotine-team/unstable
$ sudo apt update
$ sudo apt install nicotine
```

### Arch Linux/Parabola (Stable)
Nicotine+ is available in the community repository of Arch Linux and Parabola. To install, run the following:

```console
$ pacman -S nicotine+
```

### Other Distributions
Package maintainers, please insert instructions for users to install pre-compiled packages from your respective repositories here.

## Windows
- [Nicotine+ Installer](https://github.com/Nicotine-Plus/nicotine-plus/releases/download/2.0.0/Nicotine+-2.0.0.exe)  

# License

Nicotine+ is released under the terms of the [GNU Public License v3](https://www.gnu.org/licenses/gpl-3.0-standalone.html) or later.

# Getting Involved
Please come and join us in the `#nicotine+` channel on Freenode!

If you'd like to contribute, you have a couple of options to get started. You can [open an issue ticket](https://github.com/Nicotine-Plus/nicotine-plus/issues) on GitHub, discuss in `#nicotine+`, or post to the project [mailing list](mailto:nicotine-team@lists.launchpad.net). Developers are also encouraged to join the [Launchpad Team](https://launchpad.net/~nicotine-team) or subscribe to the mailing list so that they are automatically notified of failed commits.

For (unofficial) documentation of the Soulseek protocol, see [SLSKPROTOCOL.md](doc/SLSKPROTOCOL.md)

There is a current list of things [TODO.md](doc/TODO.md).

If you'd like to translate Nicotine+ into another language it has not been already, see [TRANSLATIONS.md](doc/TRANSLATIONS.md).

If you want to contact someone, see [MAINTAINERS.md](AUTHORS.md).

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

# Dependencies

## Required

* [python3](https://www.python.org/) >= 3.5 for interpreter;
* [python3-gi](https://pygobject.readthedocs.io/en/latest/getting_started.html) for using GObject introspection with Python 3;
* [gobject-introspection](https://gi.readthedocs.io/en/latest/) for GObject introspection;
* [gir1.2-gtk-3.0](https://www.gtk.org/) for GObject introspection bindings for GTK;
* [python3-mutagen](https://mutagen.readthedocs.io/en/latest/) >= 1.36.2 for metadata parsing;
* [python3-miniupnpc](https://miniupnp.tuxfamily.org/) >= 1.9 for opening ports on your router or `upnpc(1)` if not available;
* [robotframework](https://robotframework.org/) for CI testing.

## Optional

* [gir1.2-appindicator3-0.1](https://lazka.github.io/pgi-docs/AppIndicator3-0.1/index.html) for tray icon;
* [gir1.2-gsound-1.0](https://lazka.github.io/pgi-docs/GSound-1.0/index.html) for sound effects;
* [gir1.2-gspell-1](https://lazka.github.io/pgi-docs/Gspell-1/index.html) for spell checking in chat;
* [gir1.2-notify-0.7](https://lazka.github.io/pgi-docs/Notify-0.7/index.html) for desktop notifications;

# Legal and Privacy

- By using Nicotine+, you agree to abide by the Soulseek [rules](https://www.slsknet.org/news/node/681) and [terms of service](https://www.slsknet.org/news/node/682), as long as you are using the official Soulseek server.
- While Nicotine+ does not collect any user data, the official Soulseek server or a user-configured third-party server may potentially do so.

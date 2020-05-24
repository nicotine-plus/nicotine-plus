# Nicotine+

Nicotine+ is a graphical client for the [Soulseek](https://www.slsknet.org/) peer-to-peer system. It is an attempt to keep [Nicotine](https://web.archive.org/web/20150720173459/http://nicotine.thegraveyard.org/) working with the latest libraries, kill bugs, keep current with the Soulseek protocol, and add some new features that users want and/or need.

# Download Nicotine+
The current stable version of Nicotine+ is 1.4.1

## Linux
If you have no need to modify the Nicotine+ source, you are strongly recommended to use precompiled packages for your distribution. This will save you time.

### Ubuntu PPA (Stable)
To use [stable packages](https://launchpad.net/~nicotine-team/+archive/ubuntu/stable), run the following:

```console
$ sudo add-apt-repository ppa:nicotine-team/stable
$ sudo apt update
$ sudo apt install nicotine
```

### Ubuntu PPA (Unstable)
The project builds [daily unstable snapshots](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-daily) in a separate [unstable PPA](https://code.launchpad.net/~nicotine-team/+archive/ubuntu/unstable). To use it, run the following:

```console
$ sudo add-apt-repository ppa:nicotine-team/unstable
$ sudo apt update
$ sudo apt install nicotine
```

### Other Distributions
Package maintainers, please insert instructions for users to install pre-compiled packages from your respective repositories here.

## Windows
- [Nicotine+ Installer](https://github.com/Nicotine-Plus/nicotine-plus/releases/download/1.4.1/Nicotine.-1.4.1.exe)  
- [Nicotine+ Source](https://github.com/Nicotine-Plus/nicotine-plus/archive/1.4.1.tar.gz)

# License

Nicotine+ is released under the terms of the [GNU Public License v3](https://www.gnu.org/licenses/gpl-3.0-standalone.html) or later.

# Getting Involved
Please come and join us in the `#nicotine+` channel on Freenode!

If you'd like to contribute, you have a couple of options to get started. You can [open an issue ticket](https://github.com/Nicotine-Plus/nicotine-plus/issues) on GitHub, discuss in `#nicotine+`, or post to the project [mailing list](mailto:nicotine-team@lists.launchpad.net). Developers are also encouraged to join the [Launchpad Team](https://launchpad.net/~nicotine-team) or subscribe to the mailing list so that they are automatically notified of failed commits.

There is a current list of things [TODO](doc/TODO.md).

If you'd like to translate Nicotine+ into another language it has not been already, see [TRANSLATIONS](doc/TRANSLATIONS.md).

If you want to contact someone, see [MAINTAINERS](AUTHORS.md).

# Dependencies

## Required

* [python3](https://www.python.org/)
* [python3-gi](https://pygobject.readthedocs.io/en/latest/getting_started.html)
* [gobject-introspection](https://gi.readthedocs.io/en/latest/)
* [gir1.2-gtk-3.0](https://www.gtk.org/)
* [python3-mutagen](https://mutagen.readthedocs.io/en/latest/)

## Optional

* [GeoIP python bindings](https://github.com/maxmind/geoip-api-python) for country lookup.
* [MiniUPnPc python module or binary](https://miniupnp.tuxfamily.org/) for opening ports on your router.
* [Python for Windows Extensions](https://sourceforge.net/projects/pywin32/) for hiding directories from your shares (Windows only).

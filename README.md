# Nicotine+

[![N|Solid](files/icons/96x96/nicotine-plus.png)](https://github.com/Nicotine-Plus/nicotine-plus/)

Nicotine+ is a graphical client for the SoulSeek peer-to-peer system. It is an attempt to keep Nicotine working with the latest libraries, kill bugs, keep current with the SoulSeek protocol, and add some new features that users want and/or need.

## License

Nicotine+ released under the terms of the [GNU Public License v3](https://www.gnu.org/licenses/gpl-3.0-standalone.html) or later.

## Contributing
If you'd like to contribute, you have a couple of options to get started. You can open an issue ticket on GitHub. You can discuss what you'd like to do in the `#nicotine+` on Freenode. Or you can use the [mailing list](nicotine-team@lists.launchpad.net) if you'd like.

Developers are encouraged to join the [Launchpad Team](https://launchpad.net/~nicotine-team) so that they are automatically notified of failed commits.

There is a current list of things [TODO](doc/TODO.md). If you'd like to translate Nicotine+ into another language it has not been already, see [TRANSLATIONS](doc/TRANSLATIONS.md).

You want to contact someone? See: [MAINTAINERS](AUTHORS.md)

## Precompiled Packages
If you have no need to modify the Nicotine+ source, you are strongly recommended to use precompiled packages for your distribution. This will save you time.

### Ubuntu PPA (Unstable)
The project builds [daily unstable snapshots](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-daily) in a separate unstable PPA. To use it, run the following:

```console
$ sudo add-apt-repository ppa:nicotine-team/unstable
$ sudo apt update
$ sudo apt install nicotine
```

### Ubuntu PPA (Stable)
To use stable packages, run the following:

```console
$ sudo add-apt-repository ppa:nicotine-team/stable
$ sudo apt update
$ sudo apt install nicotine
```

## Other Distributions
Package maintainers, please insert instructions for users to install pre-compiled packages from your respective repositories here. For packaging instructions please see [PACKAGING](doc/PACKAGING.md). For downstream packages patches [DISTRO_PATCHES](doc/DISTRO_PATCHES.md).

# Versioning scheme

Nicotine+ uses a versioning scheme similar to what gnome does:

* Stable releases have an even minor version number, ex: 1.**4**.x, 1.**6**.x, ...

* Unstable releases have an odd minor version number, ex: 1.**3**.x, 1.**5**.x, ...

# Run it from git

To run it from git master see: [RUNFROMGIT](doc/RUNFROMGIT.md)

A Debian/Ubuntu repository containing the latest git master-based packages is also available: [GITDEB](doc/GITDEB.md)

### Dependencies

##### Required

* [Python 2.7.X](https://www.python.org/)
* [Gtk+ 2.24.X](http://www.gtk.org/)
* [PyGTK 2.24.X](http://www.pygtk.org/)
* [mutagen](https://github.com/quodlibet/mutagen)

##### Optional

* [GeoIP python bindings](https://dev.maxmind.com/geoip/legacy/downloadable/) for Country lookup: need an alternative (unmaintained).
* [python-notify](http://www.galago-project.org) for notification support: need an alternative (unmaintained).
* [MiniUPnPc python module or binary](https://miniupnp.tuxfamily.org/) for opening ports on your router.
* [Python for Windows Extensions](https://sourceforge.net/projects/pywin32/) for hiding directories from your shares (Windows only).

# Nicotine+

## Notes porting to Python 3

* sudo apt install libcairo2-dev libgirepository1.0-dev
* pip install pygobject
* pip install mutagen

## Intro

A graphical client for the SoulSeek peer-to-peer system.

Nicotine+ is an attempt to keep Nicotine working with the latest libraries,
kill bugs, keep current with the Soulseek protocol,
and add some new features that users want and/or need.

### Links

| Website                              | https://www.nicotine-plus.org                                    |
| :----------------------------------- | :--------------------------------------------------------------- |
| **Code & Bug Tracker**               | **https://github.com/Nicotine-Plus/nicotine-plus**               |
| **IRC**                              | **https://webchat.freenode.net/?channels=nicotine+**             |
| **PPA for Debian/Ubuntu (Stable)**   | **https://launchpad.net/~kip/+archive/ubuntu/nicotine+**         |
| **PPA for Debian/Ubuntu (Unstable)** | **https://launchpad.net/~kip/+archive/ubuntu/nicotine+unstable** |

### Versioning scheme

Nicotine+ uses a versioning scheme similar to what gnome does:

* Stable releases have an even minor version number, ex: 1.**4**.x, 1.**6**.x, ...

* Unstable releases have an odd minor version number, ex: 1.**3**.x, 1.**5**.x, ...

### Run it from git

To run it from git master see: [RUNFROMGIT](doc/RUNFROMGIT.md)

A Debian/Ubuntu repository containing the latest git master-based packages is also available: [GITDEB](doc/GITDEB.md)

### Packaging

For packaging instructions see: [PACKAGING](doc/PACKAGING.md)

For downstream packages patches see: [DISTRO_PATCHES](doc/DISTRO_PATCHES.md)

### Help wanted

You want to help? See a list of things [TODO](doc/TODO.md)

Nicotine+ is not translated in your language? See: [TRANSLATIONS](doc/TRANSLATIONS.md)

You want to contact someone? See: [MAINTAINERS](AUTHORS.md)

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

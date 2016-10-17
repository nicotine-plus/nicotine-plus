# Nicotine+

A graphical client for the SoulSeek peer-to-peer system

| Website                | https://www.nicotine-plus.org                        |
| :--------------------- | :--------------------------------------------------- |
| **Code & Bug Tracker** | **https://github.com/eLvErDe/nicotine-plus**         |
| **IRC**                | **https://webchat.freenode.net/?channels=nicotine+** |

Nicotine+ is an attempt to keep Nicotine working with the latest libraries,
kill bugs, keep current with the Soulseek protocol
and add some new features that users want and/or need.

### Run it from git

To run it from git master see: [RUNFROMGIT](doc/RUNFROMGIT.md)

### Installation / Packaging

For installation / packaging instruction see: [INSTALL](doc/INSTALL.md)

### Help wanted

You want to help ? See a list of things [TODO](doc/TODO.md)

Nicotine+ is not translated in your language ? See: [TRANSLATIONS](doc/TRANSLATIONS.md)

You want to contact someone? See: [MAINTAINERS](doc/MAINTAINERS.md)

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
* [Python for Windows Extensions](https://sourceforge.net/projects/pywin32/) for hidding directories from your shares (Windows only).

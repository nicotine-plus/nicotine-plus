# Installation / Packaging

### GNU/Linux instructions

##### Installation

To install Nicotine from the git repository run:

`sudo python setup.py install`

**WARNING**: Nicotine+ will be installed into the python system directory (typically /usr). There is no easy way to remove it once installed this way.

##### Building a source distribution

To build source distribution files (.tar.bz2 & .tar.gz) from the git repository run:

`python setup.py sdist --formats=bztar,gztar`

The source distribution files will be located in the `dist` subdirectory of your git repository.

##### Building a RPM package

You need to install the RPM building tools first:

* On Redhat/Fedora based distributions: `sudo dnf install rpm-build`

* On Debian/Ubuntu based distributions: `sudo apt-get install rpm`

Then you can create an RPM with:

`python setup.py bdist_rpm`

The RPM package will be located in the `dist` subdirectory of of your git repository.


### Windows

Coming Soon...

# Installation / Packaging

### GNU/Linux instructions

##### Installation

To install Nicotine, from the source tree run:

`python setup.py install --prefix=wanteddir`

**If you omit --prefix Nicotine will be installed into the python system
directory (typically /usr).**

This is not recommended however, as there is no way to uninstall things easily this way.

##### Launching Nicotine+

The recommended way of running Nicotine is from the source tree, which might
seem strange, but is no problem at all, especially if you are the only user of
the system that is interested in running Nicotine. From the source tree run:

`python ./nicotine.py`

##### Building a source distribution

To build source distribution (.tar.bz2 + .tar.gz) run:

`python setup.py sdist --formats=bztar,gztar`

##### Building a rpm package

To create an RPM from the source tree run:

`python setup.py bdist_rpm`

This will create a binary RPM in the dist subdirectory of the source tree.


### Windows

Coming Soon...

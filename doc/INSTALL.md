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

##### Building a frozen application via PyInstaller

First you need to install PyInstaller via pip:

`python.exe -m pip install PyInstaller==3.1.1`

We're using the 3.1.1 version because there's a [bug](https://github.com/pyinstaller/pyinstaller/issues/1974) in the 3.2.0 version (hopefully solved in 3.2.1) requiring to install mcvcr100.dll with would require in turn to install Microsoft Visual C++ 2010 Redistributable Package for the frozen application to work.

Once PyInstaller is installed go to the git root folder and run via cmd.exe or Powershell:

`C:\Python27\Scripts\pyinstaller.exe .\tools\nicotine+-win32.spec`

When the frozen application finish to build you will find it under the `dist/Nicotine+` subdirectory.

##### Building a NSIS installer from the frozen application

Comming soon...

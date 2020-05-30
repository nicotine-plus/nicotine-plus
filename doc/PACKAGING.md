# Packaging

### GNU/Linux instructions

#### Building a source distribution

To build source distribution files (.tar.bz2 & .tar.gz) from the git repository run:

`python setup.py sdist --formats=bztar,gztar`

The source distribution files will be located in the `dist` subdirectory of your git repository.

#### Building a RPM package

You need to install the RPM building tools first:

* On Redhat/Fedora based distributions: `sudo dnf install rpm-build`

* On Debian/Ubuntu based distributions: `sudo apt-get install rpm`

Then you can create an RPM with:

`python setup.py bdist_rpm`

The RPM package will be located in the `dist` subdirectory of your git repository.


### Windows

#### Building a frozen application via PyInstaller

First, follow the instructions on installing MSYS2: [https://pygobject.readthedocs.io/en/latest/getting_started.html#windows-logo-windows](https://pygobject.readthedocs.io/en/latest/getting_started.html#windows-logo-windows)

Then, you need to install PyInstaller via pip (in a Mingw terminal):

`pacman -S mingw-w64-x86_64-python3-pip`  
`pip install PyInstaller`

Once PyInstaller is installed, clone the Nicotine+ git repository:

`pacman -S git`  
`git clone https://github.com/Nicotine-Plus/nicotine-plus`  
`cd nicotine-plus`  

Install dependencies:

`pacman -S mingw-w64-x86_64-libnotify`  
`pip install mutagen`  
`pacman -S mingw-w64-x86_64-miniupnpc`  
`pacman -S mingw-w64-x86_64-gst-python`  

Run PyInstaller:

`pyinstaller nicotine.spec`

When the frozen application finish to build you will find it under the `dist\Nicotine+` subdirectory.

If you want to run the frozen application you can launch the executable `dist\Nicotine+\Nicotine+.exe`.

#### Building a NSIS installer from the frozen application

After building the frozen app download the last zip from [NSIS2 version](https://sourceforge.net/projects/nsis/files/NSIS%202/).

Extract it in the `files\windows` directory.

Then via cmd.exe or Powershell go to `files\windows` directory and run `nsis-$(version)/makensis.exe nicotine+.nsi`

You should now find a `Nicotine+-$(version).exe` installer in the `files\windows` directory.

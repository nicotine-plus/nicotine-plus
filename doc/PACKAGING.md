# Packaging

### Note for packagers
This is a special note for distribution packagers: There is a standard feature of GitHub which enables you to be notified of new package releases: In the top right bar there is the *Watch* option, which has the suboption to be notified of *releases only*. Please subscribe so you won't miss any of our new releases.
Thanks!

### Dependencies
The dependencies for Nicotine+ are described in [DEPENDENCIES.md](DEPENDENCIES.md).

### GNU/Linux instructions

#### Building a source distribution

To build source distribution files (.tar.bz2 & .tar.gz) from the git repository run:

```console
python3 setup.py sdist --formats=bztar,gztar
```

The source distribution files will be located in the `dist` subdirectory of your git repository.

#### Building a Debian package

Unstable and stable PPAs are already provided for pre-compiled packages, as described in the `README.md`. However, if you wish to build your own package perform the following.

Start by installing the build dependencies:

```console
sudo apt build-dep .
```

Generate the "upstream" tarball:

```console
python3 setup.py sdist
mk-origtargz dist/nicotine-plus-*.tar.gz
```

Build the Debian source package:

```console
debuild -S -sa
```

Build the binary from the source package and upstream tarball via `sbuild`:

```console
sbuild ../nicotine_*.dsc
```


### Windows

GitHub Actions currently builds Nicotine+ installers for Windows, but the following information may be useful if you want to generate an installer on your own Windows machine.

#### Building a frozen application via PyInstaller

First, follow the instructions on installing MSYS2: [https://pygobject.readthedocs.io/en/latest/getting_started.html#windows-logo-windows](https://pygobject.readthedocs.io/en/latest/getting_started.html#windows-logo-windows)

Then, install dependencies:

```console
export NICOTINE_GTK_VERSION=3
export ARCH=x86_64
pacman --noconfirm -S --needed mingw-w64-$ARCH-python
python3 packaging/windows/dependencies_core.py
python3 packaging/windows/dependencies_packaging.py
```

Clone the Nicotine+ git repository:

```console
pacman -S git
git clone https://github.com/nicotine-plus/nicotine-plus
cd nicotine-plus
```

Run PyInstaller:

```console
python3 -m pyinstaller packaging/windows/nicotine.spec
```

After the frozen application build finished you can find it in the `dist\Nicotine+` subdirectory.

If you want to run the frozen application you can launch the executable `dist\Nicotine+\Nicotine+.exe`.

#### Building a NSIS installer from the frozen application

Run the following:

```console
python3 packaging/windows/create_installer.py
```

You should now find a `Nicotine+-$(version).exe` installer in the `packaging/windows` directory.

#### Building a 32-bit (i686) application and installer

Start a MinGW 32-bit terminal, and follow the above instructions again, replacing any instance of "x86_64" with "i686" when installing packages.

Preferably, clone a fresh copy of the nicotine-plus git repository before freezing Nicotine+ with PyInstaller again.

# Packaging

## Note for Packagers

This is a special note for distribution packagers: There is a standard feature of GitHub which enables you to be notified of new package releases: In the top right bar there is the *Watch* option, which has the suboption to be notified of *releases only*. Please subscribe so you won't miss any of our new releases.
Thanks!


## Dependencies

Dependencies for Nicotine+ are described in [DEPENDENCIES.md](DEPENDENCIES.md).


## GNU/Linux Instructions

### Building a Source Distribution

To build source distribution files `.tar.bz2` and `.tar.gz` from the Git repository, run:

```sh
python3 setup.py sdist --formats=bztar,gztar
```

The source distribution files will be located in the `dist/` subfolder.

### Building a Debian Package

Unstable and stable PPAs are already provided for pre-compiled packages. However, if you wish to build your own package, perform the following steps.

Start by installing the build dependencies:

```sh
sudo apt build-dep .
```

Generate the "upstream" tarball:

```sh
python3 setup.py sdist
mk-origtargz dist/nicotine-plus-*.tar.gz
```

Build the Debian package:

```sh
debuild -sa -us -uc
```


## Windows

GitHub Actions currently builds Nicotine+ installers for Windows. However, the following instructions may be useful if you wish to generate an installer on your own machine.

### Building a Frozen Application with cx_Freeze

Follow the instructions on installing MSYS2: [https://pygobject.readthedocs.io/en/latest/getting_started.html#windows-logo-windows](https://pygobject.readthedocs.io/en/latest/getting_started.html#windows-logo-windows)

Clone the `nicotine-plus` Git repository:

```sh
pacman -S git
git clone https://github.com/nicotine-plus/nicotine-plus
cd nicotine-plus
```

Install dependencies:

```sh
export NICOTINE_GTK_VERSION=3
export ARCH=x86_64
pacman --noconfirm -S --needed mingw-w64-$ARCH-python
python3 packaging/windows/dependencies_core.py
python3 packaging/windows/dependencies_packaging.py
```

Build the application:

```sh
python3 packaging/windows/setup.py bdist_msi
```

When the application has finished building, it is located in the `build\package\` subfolder. The installer is located in the `dist\` subfolder.

If you want to run the application, you can launch the executable `build\package\Nicotine+.exe`.

### Building a 32-bit (i686) Application and Installer

Start a MinGW 32-bit terminal, and follow the above instructions again. Replace any instance of `x86_64` with `i686` when installing packages.

You are recommended to clone a fresh copy of the `nicotine-plus` Git repository before building a frozen application again.


## macOS

GitHub Actions currently builds Nicotine+ packages for macOS. However, the following instructions may be useful if you wish to generate a package on your own machine.

### Building a Frozen Application with cx_Freeze

Follow the instructions on installing Homebrew: [https://brew.sh/](https://brew.sh/)

Clone the `nicotine-plus` Git repository:

```sh
git clone https://github.com/nicotine-plus/nicotine-plus
cd nicotine-plus
```

Install dependencies:

```sh
export NICOTINE_GTK_VERSION=3
/usr/local/bin/python3 packaging/macos/dependencies_core.py
/usr/local/bin/python3 packaging/macos/dependencies_packaging.py
```

Build the application:

```sh
python3 packaging/macos/setup.py bdist_dmg
```

When the application has finished building, it is located in the `build/` subfolder as a .dmg file.


# Packaging

> **NOTE**: For distribution packagers: There is a standard feature of GitHub
> which enables you to be notified of new package releases: In the top right
> bar there is the **Watch** option, which has the suboption to be notified of
> *releases only*. Please subscribe so you won't miss any of our new releases.
> Thanks!


## Dependencies

Dependencies for Nicotine+ are described in [DEPENDENCIES.md](DEPENDENCIES.md).


## GNU/Linux Instructions

### Building a Source Distribution

To build a source distribution archive `.tar.gz` from the Git repository, run:

```sh
python3 -m build --sdist
```

The source distribution archive will be located in the `dist/` subfolder.

### Building a Debian Package

Unstable and stable PPAs are already provided for pre-compiled packages.
However, if you wish to build your own package, perform the following steps.

Start by installing the build dependencies:

```sh
sudo apt build-dep .
```

Generate the "upstream" tarball:

```sh
python3 -m build --sdist
mk-origtargz dist/nicotine-plus-*.tar.gz
```

Build the Debian package:

```sh
debuild -sa -us -uc
```


## Windows

GitHub Actions currently builds Nicotine+ installers for Windows. However, the
following instructions may be useful if you wish to generate an installer on
your own machine.

### Building a Frozen Application with cx_Freeze

Follow the instructions on [installing MSYS2](https://www.msys2.org/#installation).
Once MSYS2 is installed, launch the MINGW64 environment.

Clone the `nicotine-plus` Git repository:

```sh
pacman -S git
git clone https://github.com/nicotine-plus/nicotine-plus
cd nicotine-plus
```

Install dependencies:

```sh
export ARCH=x86_64
pacman --noconfirm -S --needed mingw-w64-$ARCH-python
python3 packaging/windows/dependencies.py
```

Build the application:

```sh
python3 packaging/windows/setup.py bdist_msi
```

When the application has finished building, it is located in the
`packaging\windows\build\` subfolder.

If you want to run the application, you can launch the executable
`packaging\windows\build\package\Nicotine+\Nicotine+.exe`.


## macOS

GitHub Actions currently builds Nicotine+ packages for macOS. However, the
following instructions may be useful if you wish to generate a package on your
own machine.

### Building a Frozen Application with cx_Freeze

Follow the instructions on [installing Homebrew](https://brew.sh/).

Clone the `nicotine-plus` Git repository:

```sh
git clone https://github.com/nicotine-plus/nicotine-plus
cd nicotine-plus
```

Install dependencies:

```sh
brew install python@3.11
python3.11 -m venv venv
venv/bin/python3 packaging/macos/dependencies.py
```

Build the application:

```sh
venv/bin/python3 packaging/macos/setup.py bdist_dmg
```

When the application has finished building, it is located in the
`packaging/macos/build/` subfolder as a .dmg file.


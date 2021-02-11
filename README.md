# Nicotine+
<img src="files/org.nicotine_plus.Nicotine.svg" align="right" width="128" style="margin: 0 10px">

Nicotine+ is a graphical client for the [Soulseek](https://www.slsknet.org/news/) peer-to-peer file sharing network.

Nicotine+ aims to be a pleasant, Free and Open Source (FOSS) alternative to the official Soulseek client, providing additional functionality while keeping current with the Soulseek protocol.

Check out the [screenshots](files/screenshots/SCREENSHOTS.md) and [source code](https://github.com/Nicotine-Plus/nicotine-plus).
<br clear="right">

# Download Nicotine+
The current stable version of Nicotine+ is 3.0.0, released on February 12, 2021. See the [release notes](NEWS.md).

## GNU/Linux, *BSD
If you have no need to modify the Nicotine+ source, you are strongly recommended to use precompiled packages for your distribution/operating system. This will save you time.

### Ubuntu PPA/Debian (Stable)
To use [stable packages](https://launchpad.net/~nicotine-team/+archive/ubuntu/stable) on Ubuntu and Debian, run the following:

```sh
sudo apt install software-properties-common
sudo add-apt-repository ppa:nicotine-team/stable
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6CEB6050A30E5769
sudo apt update
sudo apt install nicotine
```

### Ubuntu PPA/Debian (Unstable)
The project builds [daily unstable snapshots](https://code.launchpad.net/~nicotine-team/+recipe/nicotine+-daily) in a separate [unstable PPA](https://code.launchpad.net/~nicotine-team/+archive/ubuntu/unstable). To use it, run the following:

```sh
sudo apt install software-properties-common
sudo add-apt-repository ppa:nicotine-team/unstable
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6CEB6050A30E5769
sudo apt update
sudo apt install nicotine
```

### Arch Linux/Manjaro/Parabola (Stable)
Nicotine+ is available in the community repository of Arch Linux, Manjaro and Parabola. To install, run the following:

```sh
sudo pacman -S nicotine+
```

### Void Linux (Stable)
To install Nicotine+ on Void Linux, run the following:

```sh
sudo xbps-install -S nicotine+
```

### Fedora (Stable)
To install Nicotine+ on Fedora, run the following:

```sh
sudo dnf install nicotine+
```

### Guix (Stable)
To install Nicotine+ on Guix, run the following:

```sh
guix install nicotine+
```

### Other Distributions
If Nicotine+ isn't packaged for your distribution/operating system yet, there are other recommended ways of installing Nicotine+.

#### pip (Stable)
Nicotine+ can be installed using [pip](https://pip.pypa.io/en/stable/). Ensure the [dependencies](https://github.com/Nicotine-Plus/nicotine-plus/blob/3.0.0/doc/DEPENDENCIES.md) are installed, and run the following:

```sh
pip3 install nicotine-plus
```

#### Flathub (Stable)
If your distribution supports Flatpak, you can install Nicotine+ from Flathub.

[Download Nicotine+ on Flathub](https://flathub.org/apps/details/org.nicotine_plus.Nicotine)

## Windows

### Stable

Stable Windows installers for Nicotine+ are available to download. Installing Nicotine+ requires administrator privileges.

- [64-bit Installer](https://github.com/Nicotine-Plus/nicotine-plus/releases/download/3.0.0/windows-x86_64-installer.zip)
- [32-bit Installer](https://github.com/Nicotine-Plus/nicotine-plus/releases/download/3.0.0/windows-i686-installer.zip)

If you don't want to, or you aren't able to install Nicotine+ on your system, portable packages are also available. These can be run from your home directory.

- [64-bit Portable Package](https://github.com/Nicotine-Plus/nicotine-plus/releases/download/3.0.0/windows-x86_64-package.zip)
- [32-bit Portable Package](https://github.com/Nicotine-Plus/nicotine-plus/releases/download/3.0.0/windows-i686-package.zip)

### Unstable

Unstable Windows packages are generated after every commit to the master branch, and should only be used for testing. You need to be signed into a GitHub account to download the packages.

- [64/32-bit Installers / Packages](https://github.com/Nicotine-Plus/nicotine-plus/actions?query=branch%3Amaster+event%3Apush+is%3Asuccess+workflow%3A%22Packaging%22)

## macOS

### Stable (Catalina/10.15 and newer)

A stable macOS installer for Nicotine+ is available on macOS version 10.15 (Catalina) and newer.

- [Download Installer](https://github.com/Nicotine-Plus/nicotine-plus/releases/download/3.0.0/macos-installer.zip)

### Stable (Mojave/10.14)

On macOS version 10.14 (Mojave), the recommended approach is to install Nicotine+ using [Homebrew](https://brew.sh).

Once Homebrew is set up, run the following:

```sh
brew install nicotine-plus
```

### Unstable (Catalina/10.15 or newer)

Unstable macOS installers are generated after every commit to the master branch, and should only be used for testing. You need to be signed into a GitHub account to download the installers.

- [Download Installer](https://github.com/Nicotine-Plus/nicotine-plus/actions?query=branch%3Amaster+event%3Apush+is%3Asuccess+workflow%3A%22Packaging%22)

## Building from git (Unstable)
For more experienced users and developers who want to test the latest and greatest changes in Nicotine+, building from git is described in [RUNFROMGIT.md](doc/RUNFROMGIT.md). Also read the next section about getting involved.

# Getting Involved
Please come and join us in the `#nicotine+` channel on Freenode!

If you'd like to contribute, you have a couple of options to get started:

* If you'd like to translate Nicotine+ into another language it has not been already, see [TRANSLATIONS.md](doc/TRANSLATIONS.md).
* If you find a problem or have a feature request you can
  * discuss your findings on the `#nicotine+` channel on the [freenode IRC-Network](https://webchat.freenode.net/)
  * [create a new issue](https://github.com/Nicotine-Plus/nicotine-plus/issues) on GitHub, 
  * or post to the project [mailing list](mailto:nicotine-team@lists.launchpad.net).
* If you're packaging Nicotine+ for a distribution or operating system, see [DEPENDENCIES.md](doc/DEPENDENCIES.md) for a list of dependencies.
* Code contributors, developers and maintainers should read [DEVELOPING.md](doc/DEVELOPING.md) for important information about various aspects of Nicotine+ development. Developers are also encouraged to join the [Launchpad Team](https://launchpad.net/~nicotine-team) or subscribe to the mailing list so that they are automatically notified of failed commits.
* For (unofficial) documentation of the Soulseek protocol, see [SLSKPROTOCOL.md](doc/SLSKPROTOCOL.md)
* For a current list of things to do, see the [issue tracker](https://github.com/Nicotine-Plus/nicotine-plus/issues).
* For a list of contributors to Nicotine+ and its predecessors, see [AUTHORS.md](AUTHORS.md).

# Where did the name Nicotine come from?

> I was in a geeky mood and was browsing [http://www.bash.org](http://www.bash.org)'s QDB.  
I stumbled across this quote:  
>> **\<etc>** so tempting to release a product called 'nicotine' and wait for the patches.  
>> **\<etc>** then i would have a reason to only apply one patch a day. otherwise, i'm going against medical advise.  
>
> So I thought what the hell and bluntly stole etc's idea.  

<p align="right">Hyriand, <i>founder of the Nicotine project</i></p>

# Legal and Privacy

- By using Nicotine+, you agree to abide by the Soulseek [rules](https://www.slsknet.org/news/node/681) and [terms of service](https://www.slsknet.org/news/node/682), as long as you are using the official Soulseek server.
- While Nicotine+ does not collect any user data, the official Soulseek server or a user-configured third-party server may potentially do so.

# License

Nicotine+ is released under the terms of the [GNU Public License v3](https://www.gnu.org/licenses/gpl-3.0-standalone.html) or later.

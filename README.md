<!--
  SPDX-FileCopyrightText: 2013-2025 Nicotine+ Contributors
  SPDX-License-Identifier: GPL-3.0-or-later
-->

# Nicotine+

<img src="data/icons/icon.svg" alt="Nicotine+ Logo" align="right"
 width="128" height="128">

Nicotine+ is a graphical client for the [Soulseek](https://www.slsknet.org/news/)
peer-to-peer network.

Nicotine+ aims to be a lightweight, pleasant, free and open source (FOSS)
alternative to the official Soulseek client, while also providing a
comprehensive set of features.

Nicotine+ is written in Python and uses GTK for its graphical user interface.

Check out the [screenshots](data/screenshots/SCREENSHOTS.md)
and [source code](https://github.com/nicotine-plus/nicotine-plus).


## Features

### 🎵 Preview/Listen Feature

Nicotine+ includes an integrated preview system that allows you to listen to audio files and watch video files directly from the download interface, without waiting for the complete download to finish.

**Key Features:**
- **Integrated Player**: Built-in media player using GStreamer for seamless playback
- **External Player Support**: Automatic fallback to your system's default media player
- **Wide Format Support**: MP3, FLAC, OGG, WAV, M4A, AAC, WMA, Opus, AIFF (audio) + MP4, AVI, MKV, WebM, MOV (video)
- **Cross-Platform**: Works on Windows, macOS, and Linux with automatic dependency detection
- **Smart Fallbacks**: Automatically adapts to available multimedia capabilities on your system

The preview system automatically detects and configures multimedia dependencies, providing the best possible experience without manual setup.

### Installation for Preview Support

#### Windows
Nicotine+ automatically detects GStreamer installations. Choose one of these methods:

```bash
# Option 1: MSYS2 Environment (Recommended for developers)
# First install MSYS2 from https://www.msys2.org/
# Then in MSYS2 terminal:
pacman -S mingw-w64-x86_64-gstreamer mingw-w64-x86_64-gst-plugins-good

# Option 2: Chocolatey Package Manager
# First install Chocolatey from https://chocolatey.org/
choco install gstreamer

# Option 3: Official GStreamer Installer (Easiest for end users)
# Download from: https://gstreamer.freedesktop.org/download/
# Run the .msi installer and follow the wizard
```

#### macOS
Install GStreamer via Homebrew for full preview support:

```bash
# Intel Macs
brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-ugly

# Apple Silicon Macs (recommended path)
/opt/homebrew/bin/brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-ugly
```

#### Linux
Most distributions include GStreamer by default. If needed:

```bash
# Ubuntu/Debian
sudo apt install gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly

# Fedora/RHEL
sudo dnf install gstreamer1-plugins-base gstreamer1-plugins-good gstreamer1-plugins-ugly

# Arch Linux
sudo pacman -S gstreamer gst-plugins-base gst-plugins-good gst-plugins-ugly
```

**Note**: If multimedia dependencies are not available, Nicotine+ will automatically fall back to using your system's default media player for previews.


## Download

The current stable version of Nicotine+ is 3.3.10, released on March 10, 2025.
See the [release notes](NEWS.md).

Downloads are available for:

 - [GNU/Linux, *BSD, Haiku and Solaris](doc/DOWNLOADS.md#gnulinux-bsd-haiku-solaris)
 - [Windows](doc/DOWNLOADS.md#windows)
 - [macOS](doc/DOWNLOADS.md#macos)


## Get Involved

If you feel like contributing to Nicotine+, there are several ways to get
involved:

 - [Issue Tracker](https://github.com/nicotine-plus/nicotine-plus/issues)
     – Report a problem or suggest improvements
 - [Testing](doc/TESTING.md)
     – Download the latest unstable build and help test Nicotine+
 - [Translations](doc/TRANSLATIONS.md)
     – Translate Nicotine+ into another language with [Weblate](https://hosted.weblate.org/engage/nicotine-plus)
 - [Packaging](doc/PACKAGING.md)
     – Package Nicotine+ for a distribution or operating system
 - [Development](doc/DEVELOPING.md)
     – Implement bug fixes, enhancements or new features
 - [IRC Channel](https://web.libera.chat/?channel=#nicotine+)
     – Chat in the #nicotine+ IRC channel on [Libera.Chat](https://libera.chat/)


## Where did the name Nicotine come from?

> I was in a geeky mood and was browsing bash.org's QDB.  
I stumbled across this quote:  
>> **\<etc>** so tempting to release a product called 'nicotine' and wait for
>> the patches.  
>> **\<etc>** then i would have a reason to only apply one patch a day.
>> otherwise, i'm going against medical advise.  
>
> So I thought what the hell and bluntly stole etc's idea.

— <cite>Hyriand, former Nicotine maintainer, 2003</cite>


## Legal and Privacy

The Nicotine+ Team does not collect any data used or stored by the client.
Different policies may apply for data sent to the default Soulseek server,
which is not operated by the Nicotine+ Team.

When connecting to the default Soulseek server, you agree to abide by the
Soulseek [rules](https://www.slsknet.org/news/node/681) and
[terms of service](https://www.slsknet.org/news/node/682).

Soulseek is an unencrypted protocol not intended for secure communication.


## Authors

Nicotine+ is free and open source software, released under the terms of the
[GNU General Public License v3.0 or later](https://www.gnu.org/licenses/gpl-3.0-standalone.html).
Nicotine+ exists thanks to its [authors](AUTHORS.md).

© 2001–2025 Nicotine+, Nicotine and PySoulSeek Contributors

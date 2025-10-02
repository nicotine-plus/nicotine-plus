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

Nicotine+ relies on MSYS2 (CLANG64) to provide full preview support on Windows. Puedes automatizar casi todo el proceso con el script incluido o seguir los pasos manuales descritos mas abajo.

**Quick Start / Guia rapida (script automatizado)**
1. Instala Python 3.11+ desde https://www.python.org/downloads/ marcando "Add Python to PATH" y reinicia Windows.
2. Abre PowerShell como administrador en la carpeta del repositorio de Nicotine+.
3. Ejecuta el instalador automatizado:
   ```powershell
   python build-aux/windows/setup_windows_env.py --create-symlink
   ```
   El script descarga MSYS2, aplica las actualizaciones con pacman, instala las dependencias de CLANG64, anade MSYS2 al PATH y crea `run_nicotine.bat` junto a un enlace opcional en el escritorio.
4. Cuando el script termine, abre `run_nicotine.bat` (o el enlace del escritorio) para iniciar Nicotine+.

**Opciones utiles del script**
- `--installer RUTA`: usa un instalador de MSYS2 ya descargado.
- `--installer-url URL`: indica una URL alternativa del instalador.
- `--skip-install`: omite la instalacion si ya tienes MSYS2.
- `--no-path-update`: evita modificar el PATH del sistema.
- `--skip-run-script`: no genera `run_nicotine.bat`.
- `--create-symlink`: crea un enlace simbolico en el escritorio apuntando a `run_nicotine.bat` (requiere privilegios suficientes).

**Guia manual paso a paso**
1. **Instalar Python 3.11 o superior**: descarga el instalador oficial, marca "Add Python to PATH" y confirma en PowerShell con `python --version`.
2. **Instalar MSYS2 en `C\msys64`** ejecutandolo como administrador.
3. **Actualizar MSYS2** desde la terminal "MSYS2 MSYS": ejecuta `pacman -Syu`, cierra cuando lo pida, vuelve a abrir y ejecuta `pacman -Su`.
4. **Instalar dependencias en CLANG64**: abre "MSYS2 CLANG64" y pega el comando agrupado mostrado en la guia rapida (instala Python, PyGObject, GTK, GStreamer y gettext).
5. **Configurar el `PATH` de Windows** anadiendo `C\msys64\clang64\bin` y `C\msys64\usr\bin` en *Variables de entorno del sistema*; reinicia Windows para aplicar cambios.
6. **Crear el script de lanzamiento** `run_nicotine.bat` o, si prefieres trabajar desde MSYS directamente, crea un alias en tu home:
   ```bash
   ln -s /c/Users/Usuario/Downloads/nicotine-plus-master ~/nicotine-plus
   ```
7. **Verificar dependencias** ejecutando en CLANG64:
   ```bash
   python3 -c "
   import sys; print(f'✅ Python: {sys.version}')
   import gi; print('✅ PyGObject OK')
   gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print('✅ GTK3 OK')
   gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); print('✅ GStreamer OK')
   import pynicotine; print('✅ Nicotine+ Module OK')
   print('🎉 Installation Complete!')
   "
   ```
8. **Actualizar Nicotine+** mas adelante con:
   ```bash
   git pull
   python3 -m pip install --user .
   ```

**Crear enlace simbolico o acceso directo en Windows**
- Para un acceso directo clasico, puedes usar `crear_acceso_simple.ps1` o crear uno manual apuntando a `run_nicotine.bat`.
- Para un enlace simbolico (requiere modo desarrollador o PowerShell como administrador):
  ```powershell
  New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\Desktop\NicotinePlus.bat" -Target "C:\Users\Usuario\Downloads\nicotine-plus-master\run_nicotine.bat"
  ```
  > Ajusta las rutas a tu instalacion. El enlace simbolico te permite iniciar Nicotine+ desde otra ubicacion manteniendo el script original intacto.

**Solucion de problemas**
- `No module named 'gi'`: `pacman -S mingw-w64-clang-x86_64-python-gobject` (MSYS2 CLANG64).
- `python3: command not found`: asegurate de que la terminal diga `CLANG64`.
- `Gtk not found`: `pacman -S mingw-w64-clang-x86_64-gtk3`.
- `bash.exe not found`: revisa las entradas del `PATH` y reinicia Windows.

**Note**: If multimedia dependencies are missing, Nicotine+ automatically falls back to your system's default media player for previews.

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

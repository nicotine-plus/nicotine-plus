#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Automate MSYS2 installation and dependency setup for Nicotine+ on Windows."""

import argparse
import ctypes
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.request import urlretrieve

try:
    import winreg  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - handled at runtime
    winreg = None

MSYS_DEFAULT_ROOT = Path(r"C:\\msys64")
DEFAULT_INSTALLER_URL = "https://repo.msys2.org/distrib/x86_64/msys2-x86_64-latest.exe"
CLANG_PACKAGES = [
    "mingw-w64-clang-x86_64-python",
    "mingw-w64-clang-x86_64-python-gobject",
    "mingw-w64-clang-x86_64-gtk3",
    "mingw-w64-clang-x86_64-python-setuptools",
    "mingw-w64-clang-x86_64-gstreamer",
    "mingw-w64-clang-x86_64-gst-plugins-base",
    "mingw-w64-clang-x86_64-gst-plugins-good",
    "mingw-w64-clang-x86_64-gst-plugins-ugly",
    "mingw-w64-clang-x86_64-gst-plugins-bad",
    "mingw-w64-clang-x86_64-gettext-tools",
]

LOGGER = logging.getLogger("setup_windows_env")


def setup_logging() -> Path:
    """Configure logging to console and to a persistent file."""

    log_dir_base = os.environ.get("TEMP") or str(Path.home())
    log_dir = Path(log_dir_base) / "nicotine-plus-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"installation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    if LOGGER.handlers:
        for handler in list(LOGGER.handlers):
            LOGGER.removeHandler(handler)

    LOGGER.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    LOGGER.addHandler(stream_handler)

    LOGGER.debug("Logging configurado. Archivo: %s", log_file)
    return log_file


LOG_FILE = setup_logging()


def ensure_windows() -> None:
    if os.name != "nt":  # pragma: no cover - guard for non-Windows usage
        raise SystemExit("Este script solo se puede ejecutar en Windows.")


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except OSError:
        return False


def require_admin() -> None:
    if not is_admin():
        raise SystemExit(
            "Debes ejecutar este script desde una consola de PowerShell o CMD "
            "con permisos de administrador."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Instala MSYS2, actualiza pacman e instala dependencias para Nicotine+ en Windows."
    )
    parser.add_argument(
        "--msys-root",
        default=str(MSYS_DEFAULT_ROOT),
        help=r"Directorio de instalacion de MSYS2 (por defecto C:\msys64)",
    )
    parser.add_argument(
        "--installer",
        help="Ruta a un instalador de MSYS2 ya descargado (opcional)",
    )
    parser.add_argument(
        "--installer-url",
        default=DEFAULT_INSTALLER_URL,
        help="URL del instalador de MSYS2 si es necesario descargarlo",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="No intenta instalar MSYS2 si ya esta presente",
    )
    parser.add_argument(
        "--no-path-update",
        action="store_true",
        help="No agrega MSYS2 al PATH del sistema",
    )
    parser.add_argument(
        "--skip-run-script",
        action="store_true",
        help="No genera el archivo run_nicotine.bat",
    )
    parser.add_argument(
        "--create-symlink",
        action="store_true",
        help=(
            "Crea un enlace simbolico a run_nicotine.bat en el escritorio "
            "(requiere permisos)"
        ),
    )
    return parser.parse_args()


def download_installer(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Descargando MSYS2 desde %s ...", url)
    urlretrieve(url, destination)
    LOGGER.info("Instalador guardado en %s", destination)
    return destination


def install_msys2(installer: Path, msys_root: Path) -> None:
    if not installer.exists():
        raise SystemExit(f"No se encuentra el instalador en {installer}")

    LOGGER.info("Instalando MSYS2 en %s ...", msys_root)
    cmd = [
        str(installer),
        "--confirm-command",
        "--accept-messages",
        "--root",
        str(msys_root),
    ]
    subprocess.check_call(cmd)
    LOGGER.info("Instalacion de MSYS2 completada.")


def run_msys_command(msys_root: Path, command: str, msystem: str = "MSYS") -> None:
    bash_path = msys_root / "usr" / "bin" / "bash.exe"

    if not bash_path.exists():
        raise SystemExit(f"No se encontro bash en {bash_path}. Esta MSYS2 instalado correctamente?")

    env = os.environ.copy()
    env["MSYSTEM"] = msystem
    env["CHERE_INVOKING"] = "1"
    env["MSYS2_ARG_CONV_EXCL"] = "*"

    LOGGER.debug("Ejecutando comando MSYS (%s): %s", msystem, command)
    subprocess.check_call([str(bash_path), "-lc", command], env=env)


def ensure_msys_installed(msys_root: Path) -> bool:
    return (msys_root / "usr" / "bin" / "bash.exe").exists()


def update_msys(msys_root: Path) -> None:
    LOGGER.info("Actualizando paquetes base de MSYS2 ...")
    run_msys_command(msys_root, "pacman -Syu --noconfirm", msystem="MSYS")
    run_msys_command(msys_root, "pacman -Su --noconfirm", msystem="MSYS")


def install_clang64_packages(msys_root: Path) -> None:
    package_list = " ".join(CLANG_PACKAGES)
    LOGGER.info("Instalando dependencias CLANG64: %s", package_list)
    run_msys_command(
        msys_root,
        f"pacman -S --noconfirm --needed {package_list}",
        msystem="CLANG64",
    )


def update_system_path(msys_root: Path) -> bool:
    if winreg is None:
        raise SystemExit("winreg no esta disponible. Este script debe ejecutarse con Python de Windows.")

    entries = [str(msys_root / "clang64" / "bin"), str(msys_root / "usr" / "bin")]
    access = winreg.KEY_READ | winreg.KEY_SET_VALUE
    if sys.maxsize > 2**32:  # pragma: no cover - Windows especifico
        access |= winreg.KEY_WOW64_64KEY

    registry_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    changed = False
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path, 0, access) as key:  # type: ignore[arg-type]
        current_value, value_type = winreg.QueryValueEx(key, "Path")
        current_parts = [part for part in current_value.split(";") if part]

        for entry in entries:
            if entry not in current_parts:
                current_parts.append(entry)
                changed = True

        if changed:
            new_value = ";".join(current_parts)
            winreg.SetValueEx(key, "Path", 0, value_type, new_value)

    if changed:
        LOGGER.info("Entradas de MSYS2 agregadas al PATH del sistema.")
        current_env_path = os.environ.get("PATH", "")
        for entry in entries:
            if entry not in current_env_path.split(";"):
                current_env_path = f"{current_env_path};{entry}" if current_env_path else entry
        os.environ["PATH"] = current_env_path
    else:
        LOGGER.debug("Las entradas de MSYS2 ya se encontraban en PATH.")

    return changed


def to_msys_path(path: Path) -> str:
    path = path.resolve()
    drive = path.drive.rstrip(":")

    if not drive:
        raise ValueError(f"Ruta invalida: {path}")

    drive_letter = drive.lower()
    tail = "/".join(path.parts[1:])
    return f"/{drive_letter}/{tail.replace('\\', '/')}"


def create_run_script(project_dir: Path, msys_root: Path) -> Path:
    run_script = project_dir / "run_nicotine.bat"
    msys_project_path = to_msys_path(project_dir)
    bash_path = msys_root / "usr" / "bin" / "bash.exe"

    command = (
        f"{bash_path} -l -c "
        f"\\\"export MSYSTEM=CLANG64 && source /etc/profile && cd "
        f"\\\"{msys_project_path}\\\" && python3 nicotine\\\"\\r\\n"
    )

    content = (
        "@echo off\r\n"
        "echo Iniciando Nicotine+ con soporte completo...\r\n"
        "echo.\r\n"
        f"{command}"
        "pause\r\n"
    )

    with open(run_script, "w", encoding="utf-8", newline="\r\n") as handler:
        handler.write(content)

    LOGGER.info("Archivo run_nicotine.bat creado en %s", run_script)
    return run_script


def create_desktop_symlink(target: Path) -> None:
    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    if not desktop.exists():
        LOGGER.warning("No se encontro el escritorio del usuario. Se omite la creacion del enlace simbolico.")
        return

    link_path = desktop / "NicotinePlus.bat"

    if link_path.exists() or link_path.is_symlink():
        LOGGER.info("Ya existe %s, no se crea un enlace nuevo.", link_path)
        return

    try:
        os.symlink(target, link_path)
        LOGGER.info("Enlace simbolico creado en %s", link_path)
    except OSError as error:
        LOGGER.error("No se pudo crear el enlace simbolico: %s", error)
        LOGGER.info("Puedes crear uno manualmente con: New-Item -ItemType SymbolicLink ...")


def detect_windows_environment(msys_root: Path) -> dict:
    """Collect environment diagnostics to aid troubleshooting."""

    info = {
        "os_version": platform.platform(),
        "architecture": platform.architecture()[0],
        "python_version": sys.version.split()[0],
        "msys_root": str(msys_root),
        "msys_installed": ensure_msys_installed(msys_root),
        "powershell_path": shutil.which("powershell") or "no encontrado",
    }

    try:
        ps_output = subprocess.check_output(
            ["powershell", "-NoProfile", "$PSVersionTable.PSVersion.ToString()"],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
        info["powershell_version"] = ps_output or "desconocida"
    except (subprocess.SubprocessError, FileNotFoundError):
        info["powershell_version"] = "desconocida"

    return info


def validate_base_dependencies(msys_root: Path) -> None:
    """Warn early about missing base dependencies."""

    if shutil.which("powershell") is None:
        LOGGER.warning("No se encontro PowerShell en el PATH. Algunas verificaciones se omitiran.")

    if msys_root.exists() and not ensure_msys_installed(msys_root):
        LOGGER.debug("Se detecto directorio de MSYS2, pero falta bash.exe.")


def main() -> None:
    ensure_windows()
    args = parse_args()
    LOGGER.info("Log detallado disponible en: %s", LOG_FILE)
    require_admin()

    msys_root = Path(args.msys_root).expanduser().resolve()
    validate_base_dependencies(msys_root)
    env_info = detect_windows_environment(msys_root)
    LOGGER.info("Entorno detectado: %s", env_info)

    msys_already_present = env_info["msys_installed"]

    if not msys_already_present:
        if args.skip_install:
            raise SystemExit(
                f"MSYS2 no esta instalado en {msys_root} y se indico --skip-install. "
                "Elimina esa opcion para instalarlo."
            )

        if args.installer:
            installer_path = Path(args.installer).expanduser().resolve()
        else:
            temp_dir = Path(tempfile.mkdtemp(prefix="msys2-installer-"))
            installer_path = download_installer(args.installer_url, temp_dir / "msys2-installer.exe")

        try:
            install_msys2(installer_path, msys_root)
        finally:
            if not args.installer:
                shutil.rmtree(installer_path.parent, ignore_errors=True)

    else:
        LOGGER.info("MSYS2 ya se encuentra en %s. Se omite la instalacion.", msys_root)

    update_msys(msys_root)
    install_clang64_packages(msys_root)

    path_updated = False
    if not args.no_path_update:
        path_updated = update_system_path(msys_root)
        if path_updated:
            LOGGER.info("PATH del sistema actualizado. Reinicia Windows o cierra sesion para aplicar los cambios.")
    else:
        LOGGER.info("Se omitio la actualizacion del PATH tal como se solicito.")

    project_dir = Path(__file__).resolve().parents[2]

    if not args.skip_run_script:
        run_script = create_run_script(project_dir, msys_root)
    else:
        run_script = project_dir / "run_nicotine.bat"
        LOGGER.info("No se genero run_nicotine.bat por peticion del usuario.")

    if args.create_symlink and not args.skip_run_script:
        create_desktop_symlink(run_script)

    LOGGER.info("Proceso completado.")
    if not args.no_path_update and not path_updated:
        LOGGER.info("Puedes usar Nicotine+ de inmediato ejecutando run_nicotine.bat.")
    else:
        LOGGER.info("Despues de reiniciar, ejecuta run_nicotine.bat para iniciar Nicotine+.")


if __name__ == "__main__":
    main()

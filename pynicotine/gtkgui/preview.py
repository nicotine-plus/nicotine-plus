# COPYRIGHT (C) 2025 Nicotine+ Contributors
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
#
# IMPORTANT: This module does NOT import GStreamer at module level
# GStreamer is imported dynamically in initialize_preview_system() to prevent errors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

import os
import platform
import subprocess
import sys
import tempfile
import threading
import urllib.request
from gettext import gettext as _
from typing import Callable
from typing import Optional
from typing import Set

# GTK imports with version requirement
import gi
gi.require_version('Gtk', '4.0')
# CRITICAL: No GStreamer import here - handled dynamically in initialize_preview_system()

from gi.repository import GLib
from gi.repository import Gtk  
from gi.repository import Pango

# GStreamer is imported dynamically in initialize_preview_system() to prevent
# import errors when GStreamer is not available in the system
Gst = None
GST_AVAILABLE = False
PREVIEW_MODE = "UNKNOWN"  # INTEGRATED, EXTERNAL_ONLY, or UNAVAILABLE

from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.logfacility import log


SUPPORTED_AUDIO_EXTENSIONS = {
    '.mp3', '.ogg', '.flac', '.wav', '.m4a', '.aac', '.wma', '.opus', '.aiff'
}

GSTREAMER_CODEC_REQUIREMENTS = {
    '.flac': ['flacdec', 'flacparse'],
    '.mp3': ['mpg123audiodec', 'mpegaudioparse'],  # Use mpg123 instead of mad
    '.ogg': ['vorbisdec', 'oggdemux'],
    '.m4a': ['faad', 'qtdemux'],
    '.aac': ['faad'],
    '.wma': ['avdec_wmav2'],
    '.opus': ['opusdec'],
    '.aiff': ['aiffparse']
}

SUPPORTED_VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mkv', '.webm', '.mov', '.wmv', '.flv', '.m4v'
}

ALL_SUPPORTED_EXTENSIONS = SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS
EXTERNAL_CLEANUP_BASE_TIMEOUT = 300
MAX_CLEANUP_RETRIES = 3
MAX_FILE_SIZE_MB = 100


class MultimediaDependencyManager:
    """Manages multimedia dependencies across different platforms."""

    def __init__(self):
        self.system = platform.system()
        self.deps_available = False
        self.fallback_enabled = False
        self.gstreamer_paths = []

    def ensure_dependencies(self) -> tuple[bool, str]:
        """Ensure multimedia dependencies are available.
        
        Returns:
            tuple: (success, mode) where mode is 'INTEGRATED', 'EXTERNAL_ONLY', or 'UNAVAILABLE'
        """
        # 1. Check if dependencies are already available
        if self._check_system_deps():
            self._setup_gstreamer_environment()
            return True, "INTEGRATED"
        
        # 2. Try to find and configure existing installations
        if self._find_and_configure_deps():
            return True, "INTEGRATED"
        
        # 3. Check if external player functionality is available
        if self._check_external_player_support():
            return True, "EXTERNAL_ONLY"
        
        # 4. No multimedia support available
        return False, "UNAVAILABLE"

    def _check_system_deps(self) -> bool:
        """Check if GStreamer is available in the system."""
        try:
            import gi
            gi.require_version('Gst', '1.0')
            from gi.repository import Gst
            
            Gst.init(None)
            
            # Test critical elements
            critical_elements = ['playbin', 'autoaudiosink']
            for element in critical_elements:
                if Gst.ElementFactory.make(element) is None:
                    log.add_transfer("Missing critical GStreamer element: %s", element)
                    return False
            
            return True
        except (ImportError, ValueError, AttributeError) as e:
            log.add_transfer("GStreamer not available: %s", e)
            return False

    def _find_and_configure_deps(self) -> bool:
        """Find and configure GStreamer installations."""
        if self.system == "Windows":
            return self._configure_windows_gstreamer()
        elif self.system == "Darwin":
            return self._configure_macos_gstreamer()
        else:
            return self._configure_linux_gstreamer()

    def _configure_windows_gstreamer(self) -> bool:
        """Configure GStreamer on Windows."""
        possible_paths = [
            "C:\\gstreamer\\1.0\\x86_64",
            "C:\\Program Files\\GStreamer\\1.0\\x86_64",
            os.path.expanduser("~\\AppData\\Local\\gstreamer"),
            "C:\\msys64\\mingw64",  # MSYS2 installation
        ]
        
        for base_path in possible_paths:
            if os.path.exists(base_path):
                gst_bin = os.path.join(base_path, "bin")
                gst_lib = os.path.join(base_path, "lib", "gstreamer-1.0")
                
                if os.path.exists(gst_bin) and os.path.exists(gst_lib):
                    # Add to PATH
                    if gst_bin not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = gst_bin + os.pathsep + os.environ["PATH"]
                    
                    # Set plugin path
                    os.environ["GST_PLUGIN_PATH"] = gst_lib
                    
                    # Try to initialize GStreamer
                    if self._test_gstreamer_init():
                        log.add_transfer("Configured GStreamer from: %s", base_path)
                        return True
        
        return False

    def _configure_macos_gstreamer(self) -> bool:
        """Configure GStreamer on macOS."""
        possible_paths = [
            "/usr/local",  # Homebrew Intel
            "/opt/homebrew",  # Homebrew Apple Silicon
            "/Library/Frameworks/GStreamer.framework",  # Official installer
        ]
        
        for base_path in possible_paths:
            if base_path.endswith(".framework"):
                # Framework installation
                if os.path.exists(base_path):
                    lib_path = os.path.join(base_path, "Libraries")
                    if os.path.exists(lib_path):
                        os.environ["GST_PLUGIN_PATH"] = lib_path
                        if self._test_gstreamer_init():
                            return True
            else:
                # Homebrew installation
                gst_lib = os.path.join(base_path, "lib", "gstreamer-1.0")
                if os.path.exists(gst_lib):
                    os.environ["GST_PLUGIN_PATH"] = gst_lib
                    if self._test_gstreamer_init():
                        return True
        
        return False

    def _configure_linux_gstreamer(self) -> bool:
        """Configure GStreamer on Linux."""
        # On Linux, GStreamer is usually properly installed via package manager
        return self._test_gstreamer_init()

    def _test_gstreamer_init(self) -> bool:
        """Test if GStreamer can be initialized."""
        try:
            import gi
            gi.require_version('Gst', '1.0')
            from gi.repository import Gst
            
            Gst.init(None)
            
            # Test playbin creation
            playbin = Gst.ElementFactory.make("playbin")
            if playbin is None:
                return False
            
            return True
        except Exception as e:
            log.add_transfer("GStreamer test failed: %s", e)
            return False

    def _setup_gstreamer_environment(self) -> None:
        """Setup GStreamer environment variables if needed."""
        if self.system == "Windows":
            # Ensure Windows-specific environment is set
            if not os.environ.get("GST_REGISTRY"):
                gst_cache = os.path.join(tempfile.gettempdir(), "gstreamer-registry")
                os.environ["GST_REGISTRY"] = gst_cache

    def _check_external_player_support(self) -> bool:
        """Check if external player functionality is available."""
        try:
            # Test if we can open URIs (basic requirement for external player)
            if self.system == "Windows":
                # Windows should always be able to use default app associations
                return True
            elif self.system == "Darwin":
                # macOS should always be able to use 'open' command
                return True
            else:
                # Linux: check for xdg-open or similar
                return subprocess.run(["which", "xdg-open"], 
                                    capture_output=True).returncode == 0
        except Exception:
            return False

    def get_capabilities_message(self, mode: str) -> str:
        """Get user-friendly message about preview capabilities."""
        if mode == "INTEGRATED":
            return _("Preview: Integrated player available")
        elif mode == "EXTERNAL_ONLY":
            return _("Preview: External player only")
        else:
            return _("Preview: Not available")


def initialize_preview_system() -> tuple[bool, str]:
    """Initialize the preview system with automatic platform detection.
    
    Returns:
        tuple: (gst_available, preview_mode)
    """
    global Gst, GST_AVAILABLE, PREVIEW_MODE
    
    log.add_transfer("Initializing preview system on %s", platform.system())
    
    # Create dependency manager
    dep_manager = MultimediaDependencyManager()
    
    # Try to ensure dependencies
    success, mode = dep_manager.ensure_dependencies()
    
    if success and mode == "INTEGRATED":
        try:
            # Import GStreamer after configuration
            import gi
            gi.require_version('Gst', '1.0')
            from gi.repository import Gst as GstModule
            
            GstModule.init(None)
            
            # Set global Gst variable after successful initialization
            global Gst
            Gst = GstModule
            
            GST_AVAILABLE = True
            PREVIEW_MODE = "INTEGRATED"
            
            log.add_transfer("Preview system initialized: Integrated player")
            
        except Exception as e:
            log.add_transfer("Failed to initialize GStreamer: %s", e)
            GST_AVAILABLE = False
            PREVIEW_MODE = "EXTERNAL_ONLY"
    else:
        GST_AVAILABLE = False
        PREVIEW_MODE = mode
        
        if mode == "EXTERNAL_ONLY":
            log.add_transfer("Preview system initialized: External player only")
        else:
            log.add_transfer("Preview system unavailable")
    
    return GST_AVAILABLE, PREVIEW_MODE


# Initialize the preview system when module is loaded
GST_AVAILABLE, PREVIEW_MODE = initialize_preview_system()


def _format_nanoseconds(nanoseconds: int) -> str:

    if nanoseconds <= 0:
        return "00:00"

    seconds = nanoseconds // 1_000_000_000
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _check_gstreamer_codecs(file_ext: str) -> bool:
    """Check if required GStreamer elements are available for file type."""
    if not GST_AVAILABLE:
        return False
        
    required_elements = GSTREAMER_CODEC_REQUIREMENTS.get(file_ext, [])
    if not required_elements:
        return True
        
    for element_name in required_elements:
        element = Gst.ElementFactory.make(element_name, None)
        if element is None:
            log.add_transfer("Missing GStreamer element for %s: %s", (file_ext, element_name))
            return False
    
    return True


def _validate_preview_file(path: str) -> None:
    """Validate that a file is safe and suitable for preview."""
    if not path:
        raise ValueError("File path cannot be empty")
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"Preview file not found: {path}")
    
    if not os.path.isfile(path):
        raise ValueError(f"Path is not a file: {path}")
    
    if not os.access(path, os.R_OK):
        raise PermissionError(f"Cannot read preview file: {path}")
    
    file_size = os.path.getsize(path)
    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        raise ValueError(f"File too large for preview: {file_size / 1024 / 1024:.1f}MB > {MAX_FILE_SIZE_MB}MB")
    
    file_ext = os.path.splitext(path)[1].lower()
    if file_ext not in ALL_SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {file_ext}")
    
    if not _check_gstreamer_codecs(file_ext):
        raise ValueError(f"Required codecs not available for {file_ext}")


class PreviewPlayer:
    """Thread-safe wrapper around GStreamer playback for the preview panel."""

    def __init__(self, finished_callback: Callable[[], None], error_callback: Callable):

        self._pipeline = None
        self._bus = None
        self._uri = None
        self._finished_callback = finished_callback
        self._error_callback = error_callback
        self._lock = threading.RLock()
        self._is_destroyed = False
        self._platform = platform.system()

    def prepare(self, path: str) -> None:
        """Prepare the player with validated file path."""
        with self._lock:
            if self._is_destroyed:
                raise RuntimeError("Player has been destroyed")
            
            if not GST_AVAILABLE:
                raise RuntimeError("GStreamer support is not available")
            
            _validate_preview_file(path)
            
            self.stop()
            
            try:
                pipeline = Gst.ElementFactory.make("playbin", "preview-playbin")
                
                if pipeline is None:
                    raise RuntimeError("Unable to initialise GStreamer playbin element")
                
                uri = Gst.filename_to_uri(path)
                pipeline.set_property("uri", uri)
                
                # Platform-specific audio/video sink configuration
                self._configure_platform_sinks(pipeline)
                
                bus = pipeline.get_bus()
                bus.add_signal_watch()
                bus.connect("message", self._on_bus_message)
                
                self._pipeline = pipeline
                self._bus = bus
                self._uri = uri
                
            except Exception as e:
                self.stop()
                raise RuntimeError(f"Failed to prepare player: {e}") from e
    
    def _configure_platform_sinks(self, pipeline):
        """Configure audio/video sinks based on platform."""
        try:
            if self._platform == "Windows":
                # Windows: prefer DirectSound for audio, Direct3D for video
                audio_sink = Gst.ElementFactory.make("directsoundsink")
                if audio_sink is None:
                    audio_sink = Gst.ElementFactory.make("autoaudiosink")
                
                video_sink = Gst.ElementFactory.make("d3dvideosink")
                if video_sink is None:
                    video_sink = Gst.ElementFactory.make("autovideosink")
                    
            elif self._platform == "Darwin":
                # macOS: prefer CoreAudio for audio, OpenGL for video
                audio_sink = Gst.ElementFactory.make("osxaudiosink")
                if audio_sink is None:
                    audio_sink = Gst.ElementFactory.make("autoaudiosink")
                
                video_sink = Gst.ElementFactory.make("glimagesink")
                if video_sink is None:
                    video_sink = Gst.ElementFactory.make("autovideosink")
                    
            else:
                # Linux: use auto sinks (usually ALSA/PulseAudio + X11/Wayland)
                audio_sink = Gst.ElementFactory.make("autoaudiosink")
                video_sink = Gst.ElementFactory.make("autovideosink")
            
            if audio_sink:
                pipeline.set_property("audio-sink", audio_sink)
            if video_sink:
                pipeline.set_property("video-sink", video_sink)
                
        except Exception as e:
            log.add_transfer("Warning: Could not configure platform sinks: %s", e)
            # Continue with default auto sinks

    def play(self) -> None:
        """Start playback if pipeline is ready."""
        with self._lock:
            if self._is_destroyed or self._pipeline is None:
                return
            
            try:
                self._pipeline.set_state(Gst.State.PLAYING)
            except Exception as e:
                log.add_transfer("Failed to start playback: %s", e)

    def pause(self) -> None:
        """Pause playback if pipeline is ready."""
        with self._lock:
            if self._is_destroyed or self._pipeline is None:
                return
            
            try:
                self._pipeline.set_state(Gst.State.PAUSED)
            except Exception as e:
                log.add_transfer("Failed to pause playback: %s", e)

    def stop(self) -> None:
        """Stop playback and cleanup resources."""
        with self._lock:
            if self._is_destroyed:
                return
                
            if self._pipeline is not None:
                try:
                    self._pipeline.set_state(Gst.State.NULL)
                except Exception as e:
                    log.add_transfer("Error stopping pipeline: %s", e)
            
            if self._bus is not None:
                try:
                    self._bus.remove_signal_watch()
                except Exception as e:
                    log.add_transfer("Error removing bus signal watch: %s", e)
            
            self._pipeline = None
            self._bus = None
            self._uri = None

    def is_playing(self) -> bool:
        """Check if currently playing."""
        with self._lock:
            if self._is_destroyed or self._pipeline is None:
                return False
            
            try:
                _res, state, _pending = self._pipeline.get_state(0)
                return state == Gst.State.PLAYING
            except Exception:
                return False

    def query_position(self) -> tuple[int, int]:
        """Query current position and duration."""
        with self._lock:
            if self._is_destroyed or self._pipeline is None:
                return (0, 0)
            
            try:
                success, position = self._pipeline.query_position(Gst.Format.TIME)
                success_duration, duration = self._pipeline.query_duration(Gst.Format.TIME)
                
                if not success:
                    position = 0
                if not success_duration:
                    duration = 0
                
                return position, duration
            except Exception:
                return (0, 0)

    def destroy(self) -> None:
        """Mark player as destroyed and cleanup."""
        with self._lock:
            self._is_destroyed = True
            self.stop()
    
    # Internal #

    def _on_bus_message(self, _bus, message):

        message_type = message.type

        if message_type == Gst.MessageType.EOS:
            GLib.idle_add(self._finished_callback)

        elif message_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            # Add platform context to error
            platform_context = f"Platform: {self._platform}"
            enhanced_debug = f"{debug}\n{platform_context}" if debug else platform_context
            GLib.idle_add(self._error_callback, err, enhanced_debug)
            
        elif message_type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            log.add_transfer("GStreamer warning on %s: %s", self._platform, warn.message)


class PreviewController:
    """Handles preview playback UI and reacts to preview lifecycle events."""

    UPDATE_INTERVAL_MS = 200

    def __init__(self, window):

        self.window = window
        self.current_transfer = None
        self.current_key = None
        self.current_path = None
        self.current_state = None
        self.progress_timeout_id = None
        self._is_destroyed = False
        self._cleanup_retry_count = 0

        self.player: Optional[PreviewPlayer] = None
        self._external_cleanup_id = None

        # Initialize player based on available capabilities
        if GST_AVAILABLE:
            self.player = PreviewPlayer(self._on_player_finished, self._on_player_error)
        else:
            self.player = None
            log.add_transfer("Preview mode: %s", PREVIEW_MODE)

        self._build_ui()
        events.connect("preview-update", self.on_preview_update)

    # UI helpers #

    def _build_ui(self):

        self.revealer = Gtk.Revealer()
        self.revealer.set_reveal_child(False)
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.revealer.set_transition_duration(200)

        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        container.set_margin_start(12)
        container.set_margin_end(12)
        container.set_margin_top(6)
        container.set_margin_bottom(6)

        if GTK_API_VERSION >= 4:
            self.revealer.set_child(container)
            self.window.container.append(self.revealer)
        else:
            self.revealer.add(container)
            self.window.container.pack_end(self.revealer, False, False, 0)

        self.play_button = self._create_icon_button("media-playback-start-symbolic")
        self.play_button.set_sensitive(False)
        self.play_button.connect("clicked", self.on_play_clicked)

        self.stop_button = self._create_icon_button("process-stop-symbolic")
        self.stop_button.connect("clicked", self.on_stop_clicked)

        details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        details_box.set_hexpand(True)

        self.title_label = Gtk.Label(xalign=0)
        self.title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.title_label.set_use_markup(True)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_hexpand(True)

        self.info_label = Gtk.Label(xalign=0)
        self.info_label.set_ellipsize(Pango.EllipsizeMode.END)

        if GTK_API_VERSION >= 4:
            container.append(self.play_button)
            container.append(self.stop_button)
            details_box.append(self.title_label)
            details_box.append(self.progress_bar)
            details_box.append(self.info_label)
            container.append(details_box)
        else:
            container.pack_start(self.play_button, False, False, 0)
            container.pack_start(self.stop_button, False, False, 0)
            details_box.pack_start(self.title_label, False, False, 0)
            details_box.pack_start(self.progress_bar, False, False, 0)
            details_box.pack_start(self.info_label, False, False, 0)
            container.pack_start(details_box, True, True, 0)

    def _create_icon_button(self, icon_name: str) -> Gtk.Button:

        if GTK_API_VERSION >= 4:
            button = Gtk.Button()
            icon = Gtk.Image.new_from_icon_name(icon_name)
            button.set_child(icon)
        else:
            button = Gtk.Button.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)

        button.get_style_context().add_class("image-button")
        return button

    def _set_play_icon(self, icon_name: str) -> None:

        if GTK_API_VERSION >= 4:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            self.play_button.set_child(icon)
        else:
            self.play_button.set_image(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON))

    def _set_status(self, message: str) -> None:
        self.info_label.set_text(message)

    def _set_title(self, transfer) -> None:

        if transfer is None:
            self.title_label.set_text("")
            return

        username = transfer.username
        filename = transfer.virtual_path.rpartition("\\")[2] or transfer.virtual_path
        escaped_username = GLib.markup_escape_text(username)
        escaped_filename = GLib.markup_escape_text(filename)
        self.title_label.set_markup(f"<b>{escaped_username} — {escaped_filename}</b>")

    # Playback helpers #

    def _cancel_progress_update(self) -> None:

        if self.progress_timeout_id is not None:
            GLib.source_remove(self.progress_timeout_id)
            self.progress_timeout_id = None

    def _start_progress_update(self) -> None:

        self._cancel_progress_update()

        if self.player is None:
            return

        self.progress_timeout_id = GLib.timeout_add(self.UPDATE_INTERVAL_MS, self._update_progress)

    def _update_progress(self):

        if self.player is None:
            return False

        position, duration = self.player.query_position()

        if duration <= 0:
            return True

        fraction = max(0.0, min(1.0, position / duration))
        self.progress_bar.set_fraction(fraction)
        self.progress_bar.set_text(f"{_format_nanoseconds(position)} / {_format_nanoseconds(duration)}")
        return True

    def _stop_playback(self, delete_file: bool = False) -> None:
        """Stop playback and cleanup resources safely."""
        if self._is_destroyed:
            return
            
        self._cancel_progress_update()

        if self.player is not None:
            try:
                self.player.stop()
            except Exception as e:
                log.add_transfer("Error stopping player: %s", e)

        if self._external_cleanup_id is not None:
            try:
                GLib.source_remove(self._external_cleanup_id)
            except Exception as e:
                log.add_transfer("Error removing cleanup timeout: %s", e)
            finally:
                self._external_cleanup_id = None

        if delete_file and self.current_path:
            try:
                core.downloads.discard_preview_file(self.current_path)
            except Exception as e:
                log.add_transfer("Error discarding preview file: %s", e)

        try:
            self._set_play_icon("media-playback-start-symbolic")
            self.play_button.set_sensitive(False)
            self.progress_bar.set_fraction(0)
            self.progress_bar.set_text("")
        except Exception as e:
            log.add_transfer("Error updating UI during stop: %s", e)
            
        self.current_path = None

    def _close_panel(self, delete_file: bool = False) -> None:
        """Close preview panel and cleanup state."""
        if self._is_destroyed:
            return
            
        self._stop_playback(delete_file=delete_file)
        
        try:
            self.revealer.set_reveal_child(False)
            self.title_label.set_text("")
            self._set_status("")
        except Exception as e:
            log.add_transfer("Error updating UI during panel close: %s", e)
            
        self.current_transfer = None
        self.current_key = None
        self.current_state = None
        self._cleanup_retry_count = 0

    def _open_external_player(self, path: str) -> None:
        """Open file in external player with progressive cleanup timeout."""
        try:
            success = self._launch_platform_player(path)
            if not success:
                raise RuntimeError("Failed to launch external player")

        except Exception as error:
            log.add_transfer("Unable to launch external player for preview: %s", error)
            self._set_status(self._get_platform_error_message(error))
            return

        self._set_status(_("Opened in external player"))
        self._cleanup_retry_count = 0
        self._schedule_external_cleanup(path)
    
    def _launch_platform_player(self, path: str) -> bool:
        """Launch external player using platform-specific method."""
        system = platform.system()
        
        try:
            if system == "Windows":
                return self._launch_windows_player(path)
            elif system == "Darwin":
                return self._launch_macos_player(path)
            else:
                return self._launch_linux_player(path)
        except Exception as e:
            log.add_transfer("Platform player launch failed: %s", e)
            return False
    
    def _launch_windows_player(self, path: str) -> bool:
        """Launch external player on Windows."""
        try:
            # Method 1: Use GTK URI handler
            uri = GLib.filename_to_uri(path, None)
            if GTK_API_VERSION >= 4:
                Gtk.show_uri(None, uri, GLib.get_monotonic_time())
            else:
                Gtk.show_uri_on_window(self.window.widget, uri, GLib.get_monotonic_time())
            return True
        except Exception:
            try:
                # Method 2: Use Windows start command
                subprocess.run(["start", "", path], shell=True, check=True)
                return True
            except Exception:
                try:
                    # Method 3: Use os.startfile
                    os.startfile(path)
                    return True
                except Exception:
                    return False
    
    def _launch_macos_player(self, path: str) -> bool:
        """Launch external player on macOS."""
        try:
            # Method 1: Use GTK URI handler
            uri = GLib.filename_to_uri(path, None)
            if GTK_API_VERSION >= 4:
                Gtk.show_uri(None, uri, GLib.get_monotonic_time())
            else:
                Gtk.show_uri_on_window(self.window.widget, uri, GLib.get_monotonic_time())
            return True
        except Exception:
            try:
                # Method 2: Use macOS open command
                subprocess.run(["open", path], check=True)
                return True
            except Exception:
                return False
    
    def _launch_linux_player(self, path: str) -> bool:
        """Launch external player on Linux."""
        try:
            # Method 1: Use GTK URI handler
            uri = GLib.filename_to_uri(path, None)
            if GTK_API_VERSION >= 4:
                Gtk.show_uri(None, uri, GLib.get_monotonic_time())
            else:
                Gtk.show_uri_on_window(self.window.widget, uri, GLib.get_monotonic_time())
            return True
        except Exception:
            try:
                # Method 2: Use xdg-open
                subprocess.run(["xdg-open", path], check=True)
                return True
            except Exception:
                return False
    
    def _is_external_player_available(self) -> bool:
        """Check if external player functionality is available."""
        return PREVIEW_MODE in ["INTEGRATED", "EXTERNAL_ONLY"]
    
    def _schedule_external_cleanup(self, path: str) -> None:
        """Schedule cleanup with progressive timeout increase."""
        if self._is_destroyed:
            return
            
        timeout = EXTERNAL_CLEANUP_BASE_TIMEOUT * (self._cleanup_retry_count + 1)
        
        def cleanup_external_preview():
            if self._is_destroyed:
                return False
                
            try:
                core.downloads.discard_preview_file(path)
                self._external_cleanup_id = None
                return False
            except Exception as e:
                log.add_transfer("Error during external cleanup: %s", e)
                
                self._cleanup_retry_count += 1
                if self._cleanup_retry_count < MAX_CLEANUP_RETRIES:
                    self._schedule_external_cleanup(path)
                else:
                    log.add_transfer("Max cleanup retries reached for: %s", path)
                    self._external_cleanup_id = None
                return False

        self._external_cleanup_id = GLib.timeout_add_seconds(timeout, cleanup_external_preview)

    # Event callbacks #

    def on_preview_update(self, transfer, state, **kwargs):

        if state == "queued":
            if transfer is None:
                return

            if self.current_transfer is not None:
                self._stop_playback(delete_file=True)

            self.current_transfer = transfer
            self.current_key = (transfer.username, transfer.virtual_path)
            self.current_state = state

            self._set_title(transfer)
            self._set_status(_("Waiting for preview"))
            self.revealer.set_reveal_child(True)
            return

        if transfer is None:
            # Generic failure not tied to a transfer
            self._set_status(kwargs.get("reason", _("Preview failed")))
            self._close_panel(delete_file=True)
            return

        key = (transfer.username, transfer.virtual_path)

        if self.current_key and key != self.current_key:
            return

        self.current_transfer = transfer
        self.current_key = key
        self.current_state = state

        if state == "started":
            self._set_status(_("Request accepted, buffering"))

        elif state == "ready":
            path = kwargs.get("path")

            if not path:
                self._set_status(_("Error: No file path provided"))
                return

            try:
                _validate_preview_file(path)
            except (ValueError, FileNotFoundError, PermissionError) as e:
                log.add_transfer("Preview file validation failed: %s", e)
                self._set_status(str(e))
                self._close_panel(delete_file=True)
                return

            self.current_path = path
            self.play_button.set_sensitive(True)

            if self.player is not None and PREVIEW_MODE == "INTEGRATED":
                try:
                    self.player.prepare(path)
                except Exception as error:
                    log.add_transfer("Preview playback error: %s", error)
                    user_msg = self._get_user_friendly_error(error)
                    self._set_status(user_msg)
                    self.play_button.set_sensitive(False)
                    
                    # Fallback to external player if integrated fails
                    if self._is_external_player_available():
                        self._set_status(_("Falling back to external player"))
                        self._open_external_player(path)
                else:
                    self._set_status(_("Playing preview"))
                    self._set_play_icon("media-playback-pause-symbolic")
                    self.player.play()
                    self._start_progress_update()
            elif PREVIEW_MODE == "EXTERNAL_ONLY":
                self._set_status(_("Opening in external player"))
                self._open_external_player(path)
            else:
                self._set_status(_("Preview not available"))
                self.play_button.set_sensitive(False)

        elif state == "finished":
            self._set_status(_("Download complete"))

        elif state in {"failed", "cancelled"}:
            reason = kwargs.get("reason") or _("Preview failed")
            user_msg = self._get_user_friendly_error(reason)
            self._set_status(user_msg)
            self._close_panel(delete_file=True)

    def on_play_clicked(self, *_args):

        if self.player is None:
            return

        if self.current_path is None:
            return

        if self.player.is_playing():
            self.player.pause()
            self._set_play_icon("media-playback-start-symbolic")
            self._set_status(_("Paused"))
            self._cancel_progress_update()

        else:
            try:
                if self.player.query_position() == (0, 0):
                    self.player.prepare(self.current_path)
            except Exception as error:
                log.add_transfer("Preview playback error: %s", error)
                user_msg = self._get_user_friendly_error(error)
                self._set_status(user_msg)
                self.play_button.set_sensitive(False)
                return

            self.player.play()
            self._set_play_icon("media-playback-pause-symbolic")
            self._set_status(_("Playing preview"))
            self._start_progress_update()

    def on_stop_clicked(self, *_args):

        if self.current_transfer is not None and self.current_state not in {"failed", "cancelled", "finished"}:
            core.downloads.cancel_preview(self.current_transfer.username, self.current_transfer.virtual_path)

        self._close_panel(delete_file=True)

    # Player callbacks #

    def _on_player_finished(self):

        if self.current_path is None:
            return

        self._stop_playback(delete_file=True)
        self._set_status(_("Preview finished"))

    def _on_player_error(self, err, debug):

        if GST_AVAILABLE and err.domain == Gst.StreamError.quark():
            handled_codes = {
                Gst.StreamError.DECODE,
                Gst.StreamError.TYPE_NOT_FOUND,
                Gst.StreamError.FORMAT,
                Gst.StreamError.FAILED,
                Gst.StreamError.NOT_IMPLEMENTED,
                Gst.StreamError.CAPS
            }

            if err.code in handled_codes or "data stream" in err.message.lower():
                log.add_transfer("Preview stream finished early (%s): %s", err.code, err.message)
                self._on_player_finished()
                return

        log.add_transfer("Preview playback error: %s", err.message)
        user_msg = self._get_user_friendly_error(err.message)
        self._set_status(user_msg)
        self.play_button.set_sensitive(False)
        self._cancel_progress_update()

    def _get_user_friendly_error(self, error) -> str:
        """Convert technical errors to user-friendly messages."""
        error_str = str(error).lower()
        system = platform.system()
        
        if "file not found" in error_str or "no such file" in error_str:
            return _("File not found or was removed")
        elif "permission" in error_str or "access" in error_str:
            return _("Cannot access file (permission denied)")
        elif "unsupported" in error_str or "format" in error_str or "codec" in error_str:
            if system == "Windows":
                return _("Unsupported file format. Install media codecs or use external player.")
            elif system == "Darwin":
                return _("Unsupported file format. Install via Homebrew: brew install gst-plugins-ugly")
            else:
                return _("Unsupported file format. Install additional codecs.")
        elif "too large" in error_str:
            return _("File too large for preview")
        elif "gstreamer" in error_str or "playbin" in error_str:
            if system == "Windows":
                return _("Media system unavailable. Install GStreamer for Windows.")
            elif system == "Darwin":
                return _("Media system unavailable. Install via: brew install gstreamer")
            else:
                return _("Media system unavailable. Install gstreamer packages.")
        elif "network" in error_str or "connection" in error_str:
            return _("Network error during preview")
        else:
            return _("Preview error: {}").format(str(error)[:100])
    
    def _get_platform_error_message(self, error) -> str:
        """Get platform-specific error message for external player failures."""
        system = platform.system()
        
        if system == "Windows":
            return _("Cannot open external player. Check file associations.")
        elif system == "Darwin":
            return _("Cannot open external player. Check default app settings.")
        else:
            return _("Cannot open external player. Install xdg-utils or default media player.")
    
    # Lifecycle #

    def destroy(self):
        """Cleanup all resources safely."""
        self._is_destroyed = True
        
        self._close_panel(delete_file=True)
        
        if self.player is not None:
            try:
                self.player.destroy()
            except Exception as e:
                log.add_transfer("Error destroying player: %s", e)
                
        try:
            events.disconnect("preview-update", self.on_preview_update)
        except (ValueError, AttributeError):
            pass

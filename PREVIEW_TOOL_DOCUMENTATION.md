<!--
  SPDX-FileCopyrightText: 2025 Nicotine+ Contributors
  SPDX-License-Identifier: GPL-3.0-or-later
-->

# Documentación de la Herramienta de Previsualización de Nicotine+

## Descripción General

La herramienta de previsualización de Nicotine+ permite reproducir archivos de audio y video directamente desde la interfaz de descarga sin necesidad de esperar a que la descarga se complete. Utiliza GStreamer como backend de reproducción y está diseñada con un enfoque de seguridad y robustez.

## Arquitectura del Sistema

### Componentes Principales

1. **PreviewPlayer**: Wrapper thread-safe para GStreamer
2. **PreviewController**: Controlador de UI y eventos del ciclo de vida
3. **Validación de Archivos**: Sistema de validación de seguridad
4. **Gestión de Codecs**: Verificación de disponibilidad de elementos GStreamer

## Dependencias y Librerías

### Librerías Core
- **GStreamer 1.0**: Backend principal de reproducción multimedia
- **GTK 4.0**: Framework de interfaz gráfica
- **GLib**: Utilidades de programación (timeouts, markup, URIs)
- **Pango**: Renderizado de texto (ellipsize)

### Módulos Python
```python
import os                    # Operaciones de archivos
import threading             # Sincronización thread-safe
from gettext import gettext  # Internacionalización
from typing import *         # Type hints
```

### Integración con Nicotine+
```python
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.logfacility import log
```

## Formatos Soportados

### Extensiones de Audio
```python
SUPPORTED_AUDIO_EXTENSIONS = {
    '.mp3', '.ogg', '.flac', '.wav', '.m4a', 
    '.aac', '.wma', '.opus', '.aiff'
}
```

### Extensiones de Video
```python
SUPPORTED_VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mkv', '.webm', '.mov', 
    '.wmv', '.flv', '.m4v'
}
```

### Requisitos de Codecs GStreamer
```python
GSTREAMER_CODEC_REQUIREMENTS = {
    '.flac': ['flacdec', 'flacparse'],
    '.mp3': ['mpg123audiodec', 'mpegaudioparse'],
    '.ogg': ['vorbisdec', 'oggdemux'],
    '.m4a': ['faad', 'qtdemux'],
    '.aac': ['faad'],
    '.wma': ['avdec_wmav2'],
    '.opus': ['opusdec'],
    '.aiff': ['aiffparse']
}
```

## Limitaciones de Seguridad

### Tamaño de Archivo
- **Límite máximo**: 100MB por archivo
- **Razón**: Prevenir ataques de denegación de servicio

### Validaciones de Seguridad
```python
def _validate_preview_file(path: str) -> None:
    # Verificación de existencia
    # Verificación de permisos de lectura
    # Validación de tamaño
    # Verificación de extensión soportada
    # Validación de codecs disponibles
```

## Clase PreviewPlayer

### Características Principales
- **Thread-safe**: Utiliza `threading.RLock()`
- **Gestión de Estados**: Manejo seguro de pipeline GStreamer
- **Cleanup Automático**: Liberación de recursos garantizada

### Métodos Principales
```python
def prepare(self, path: str) -> None:
    """Prepara el reproductor con validación de archivo"""

def play(self) -> None:
    """Inicia reproducción"""

def pause(self) -> None:
    """Pausa reproducción"""

def stop(self) -> None:
    """Detiene y limpia recursos"""

def query_position(self) -> tuple[int, int]:
    """Consulta posición y duración actual"""
```

### Pipeline GStreamer
```python
pipeline = Gst.ElementFactory.make("playbin", "preview-playbin")
uri = Gst.filename_to_uri(path)
pipeline.set_property("uri", uri)
```

## Clase PreviewController

### Responsabilidades
1. **Gestión de UI**: Construcción y actualización de interfaz
2. **Eventos**: Manejo de callbacks del reproductor
3. **Estados**: Seguimiento del ciclo de vida de preview
4. **Cleanup**: Limpieza de archivos temporales

### Componentes de UI

#### Revealer Container
```python
self.revealer = Gtk.Revealer()
self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
self.revealer.set_transition_duration(200)
```

#### Controles de Reproducción
- **Play/Pause Button**: `media-playback-start/pause-symbolic`
- **Stop Button**: `process-stop-symbolic`
- **Progress Bar**: Muestra tiempo y progreso
- **Labels**: Título del archivo y estado

### Sistema de Estados

#### Estados del Preview
1. **queued**: Preview solicitado, esperando
2. **strted**: Solicitud aceptada, buffering
3. **ready**: Archivo listo, iniciando reproducción
4. **finished**: Descarga completa
5. **failed/cancelled**: Error o cancelación

### Actualización de Progreso
```python
UPDATE_INTERVAL_MS = 200  # Actualización cada 200ms

def _update_progress(self):
    position, duration = self.player.query_position()
    fraction = position / duration
    self.progress_bar.set_fraction(fraction)
    # Formato: "MM:SS / MM:SS"
```

## Gestión de Archivos Externos

### Reproductor Externo
```python
def _open_external_player(self, path: str) -> None:
    uri = GLib.filename_to_uri(path, None)
    if GTK_API_VERSION >= 4:
        Gtk.show_uri(None, uri, GLib.get_monotonic_time())
```

### Cleanup Progresivo
- **Timeout Base**: 300 segundos (5 minutos)
- **Reintentos**: Hasta 3 intentos con timeout incremental
- **Cleanup Automático**: Eliminación de archivos temporales

## Manejo de Errores

### Validación de Archivos
```python
# Errores comunes y mensajes user-friendly
"file not found" → "File not found or was removed"
"permission" → "Cannot access file (permission denied)"
"unsupported format" → "Unsupported file format"
"too large" → "File too large for preview"
```

### Errores de GStreamer
```python
# Manejo específico de errores de stream
GST_STREAM_ERROR_CODES = {
    Gst.StreamError.DECODE,
    Gst.StreamError.TYPE_NOT_FOUND,
    Gst.StreamError.FORMAT,
    Gst.StreamError.FAILED
}
```

## Sistema de Eventos

### Event System Integration
```python
events.connect("preview-update", self.on_preview_update)

# Tipos de eventos manejados:
# - "queued": Preview en cola
# - "started": Iniciando preview
# - "ready": Archivo listo
# - "finished": Completado
# - "failed"/"cancelled": Error
```

## Compatibilidad GTK

### Soporte Multi-versión
```python
if GTK_API_VERSION >= 4:
    # Usar API GTK4
    self.revealer.set_child(container)
    container.append(widget)
else:
    # Usar API GTK3
    self.revealer.add(container)
    container.pack_start(widget)
```

## Concurrencia y Thread Safety

### Protección de Recursos
```python
self._lock = threading.RLock()  # Reentrant lock
self._is_destroyed = False      # Estado de destrucción

with self._lock:
    # Operaciones thread-safe
```

### GLib Integration
```python
# Callbacks seguros en main thread
GLib.idle_add(self._finished_callback)
GLib.timeout_add(self.UPDATE_INTERVAL_MS, self._update_progress)
```

## Ciclo de Vida y Cleanup

### Destrucción Segura
```python
def destroy(self):
    self._is_destroyed = True
    self._close_panel(delete_file=True)
    if self.player:
        self.player.destroy()
    events.disconnect("preview-update", self.on_preview_update)
```

### Gestión de Memoria
- **Cleanup automático** de pipelines GStreamer
- **Eliminación de timeouts** activos
- **Liberación de watchers** de bus
- **Desconexión de eventos** global

## Configuración y Constantes

```python
MAX_FILE_SIZE_MB = 100                    # Límite de archivo
EXTERNAL_CLEANUP_BASE_TIMEOUT = 300      # Timeout base cleanup
MAX_CLEANUP_RETRIES = 3                  # Máximo reintentos
UPDATE_INTERVAL_MS = 200                 # Intervalo actualización UI
```

## Consideraciones de Diseño

### Principios Aplicados
1. **Seguridad Primero**: Validación exhaustiva de inputs
2. **Thread Safety**: Acceso sincronizado a recursos compartidos
3. **Robustez**: Manejo comprehensivo de errores
4. **User Experience**: Mensajes de error amigables
5. **Rendimiento**: Cleanup eficiente de recursos

### Patrones Utilizados
- **Wrapper Pattern**: PreviewPlayer envuelve GStreamer
- **Observer Pattern**: Sistema de eventos
- **State Machine**: Estados de preview bien definidos
- **Resource Management**: RAII-style cleanup

## Posibles Mejoras Futuras

1. **Soporte para más formatos**: Añadir codec requirements
2. **Preview de imágenes**: Extender para formatos de imagen
3. **Seek functionality**: Navegación dentro del archivo
4. **Volume control**: Control de volumen integrado
5. **Playlist support**: Cola de archivos para preview

Esta documentación proporciona una visión completa del diseño, implementación y funcionamiento de la herramienta de previsualización de Nicotine+.

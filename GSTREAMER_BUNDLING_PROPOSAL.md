# Propuesta: Bundling Automático de GStreamer con Nicotine+

## Objetivo
Integrar GStreamer automáticamente en los builds de Nicotine+ para que los usuarios obtengan funcionalidad de preview sin configuración manual.

## Estado Actual vs Propuesto

### ❌ Estado Actual:
- Usuario instala Nicotine+ → Preview no funciona
- Usuario debe instalar GStreamer manualmente  
- Experiencia fragmentada

### ✅ Estado Propuesto:
- Usuario instala Nicotine+ → Preview funciona inmediatamente
- GStreamer incluido automáticamente
- Experiencia unificada

## Implementación por Plataforma

### 1. Windows (MSYS2 Build)

#### Cambios en `packaging/windows/dependencies.py`:
```python
def install_pacman():
    arch = os.environ.get("ARCH", "x86_64")
    prefix = "mingw-w64-clang-aarch64" if arch == "arm64" else "mingw-w64-clang-x86_64"

    packages = [
        # Dependencias existentes
        f"{prefix}-ca-certificates",
        f"{prefix}-gettext-tools", 
        f"{prefix}-gtk4",
        f"{prefix}-libadwaita",
        f"{prefix}-python-build",
        f"{prefix}-python-cx-freeze",
        f"{prefix}-python-gobject",
        f"{prefix}-python-pycodestyle",
        f"{prefix}-python-pylint",
        f"{prefix}-python-setuptools",
        f"{prefix}-python-wheel",
        f"{prefix}-webp-pixbuf-loader",
        
        # ✅ NUEVAS: Dependencias multimedia
        f"{prefix}-gstreamer",
        f"{prefix}-gst-plugins-base",
        f"{prefix}-gst-plugins-good", 
        f"{prefix}-gst-plugins-ugly",
        f"{prefix}-gst-plugins-bad",      # Para formatos adicionales
        f"{prefix}-gst-libav",            # Para más codecs
    ]
```

#### Cambios en `packaging/windows/setup.py`:
```python
# Asegurar que las DLLs de GStreamer se incluyan en el bundle
include_files = [
    # Archivos existentes...
    
    # ✅ NUEVOS: Archivos GStreamer
    (gst_bin_path, "gstreamer/bin"),
    (gst_plugins_path, "gstreamer/lib/gstreamer-1.0"),
    (gst_typelibs_path, "gstreamer/lib/girepository-1.0"),
]
```

**Impacto en tamaño**: +~50MB (aceptable para funcionalidad completa)

### 2. macOS (Homebrew Build)

#### Cambios en `packaging/macos/dependencies.py`:
```python
def install_brew():
    packages = [
        # Dependencias existentes
        "gettext",
        "gobject-introspection", 
        "gtk4",
        "libadwaita",
        "librsvg",
        
        # ✅ NUEVAS: Dependencias multimedia
        "gstreamer",
        "gst-plugins-base",
        "gst-plugins-good",
        "gst-plugins-ugly", 
        "gst-plugins-bad",
        "gst-libav",
    ]
```

#### Bundling en DMG:
```python
# Incluir frameworks GStreamer en el app bundle
frameworks_to_bundle = [
    "/usr/local/lib/GStreamer.framework",
    "/opt/homebrew/lib/gstreamer-1.0/*",  # Plugins
]
```

**Impacto en tamaño**: +~60MB

### 3. Linux (Flatpak/Snap)

#### Flatpak Manifest (`build-aux/flatpak/org.nicotine_plus.Nicotine.json`):
```json
{
    "modules": [
        {
            "name": "gstreamer-multimedia",
            "buildsystem": "simple",
            "build-commands": [
                "echo 'GStreamer plugins for multimedia support'"
            ]
        }
    ],
    "finish-args": [
        "--socket=pulseaudio",
        "--device=dri",
        "--share=ipc"
    ]
}
```

#### Snap (`build-aux/snap/snapcraft.yaml`):
```yaml
parts:
  nicotine-plus:
    stage-packages:
      - gstreamer1.0-plugins-base
      - gstreamer1.0-plugins-good
      - gstreamer1.0-plugins-ugly
      - gstreamer1.0-plugins-bad
      - gstreamer1.0-libav
```

## Beneficios

### 🎯 **Para Usuarios:**
- **Instalación única**: Preview funciona inmediatamente
- **Sin configuración**: Detección automática de capacidades
- **Experiencia consistente**: Mismo comportamiento en todas las plataformas
- **Menor fricción**: No hay pasos adicionales

### 🔧 **Para Desarrolladores:**
- **Menos soporte**: Reducción de issues relacionados con configuración
- **Testing uniforme**: Mismas capacidades en todos los builds
- **CI/CD simple**: Tests automáticos de funcionalidad multimedia

### 📊 **Métricas de Impacto:**
- **Tamaño de instalador**: +50-60MB (justificable)
- **Tiempo de instalación**: +30-60 segundos (mínimo)
- **Compatibilidad**: 99% de usuarios tendrán preview funcional

## Implementación Gradual

### Fase 1: ✅ **Desarrollo Local**
- Modificar scripts de dependencies
- Probar builds locales
- Validar funcionalidad

### Fase 2: 🔄 **CI/CD Integration** 
- Actualizar workflows de GitHub Actions
- Probar builds automáticos
- Validar artifacts

### Fase 3: 🚀 **Release**
- Documentar cambios en changelog
- Actualizar README con nueva info
- Release con bundling completo

## Consideraciones Técnicas

### **Licencias:**
- GStreamer: LGPL (compatible con GPL de Nicotine+)
- Plugins: Mezcla de LGPL/GPL (verificar legal)

### **Distribución:**
- Flatpak/Snap: Sin problemas (ecosistemas abiertos)
- Windows/macOS: Revisar términos de distribución

### **Mantenimiento:**
- Actualizaciones de GStreamer en dependencies
- Testing de compatibilidad con nuevas versiones
- Monitoreo de tamaño de builds

## Propuesta de Timeline

- **Semana 1-2**: Implementación Windows + macOS
- **Semana 3**: Testing exhaustivo multiplataforma  
- **Semana 4**: Integración CI/CD y documentación
- **Semana 5**: Review final y merge a main

## Conclusión

Esta propuesta hace que Nicotine+ ofrezca **preview multimedia out-of-the-box**, eliminando la fricción para usuarios y mejorando significativamente la experiencia de uso. El impacto en tamaño es mínimo comparado con el beneficio funcional.
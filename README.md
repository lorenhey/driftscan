# DriftScan

> **The telescope stays still. The sky does the scanning.**

`DriftScan` turns fixed-telescope time series into sky-coordinate drift profiles. Plan source transits, convert timestamps to sidereal/sky coordinates, fit beam crossings and compare scans across observing nights.

## Características

- **Time to Sky**: Convierte series temporales (tiempo -> potencia) en perfiles angulares físicos.
- **Geometría Rigurosa**: Modelos `MeridianTransit`, `FixedEquatorial` y `FixedAltAz` basados en transformaciones de `Astropy`.
- **Ejes Siderales y Civiles**: Alterná visualizaciones entre UTC, LST, Hour Angle, o Angular Offset.
- **What will cross my beam?**: Planificador predictivo para la observación.
- **Ajuste y Medición (Fitting)**: Sustracción robusta de baseline y fitting de perfil de haz gaussiano (FWHM temporal y angular).
- **GUI & CLI**: Interfaz interactiva de alta velocidad (`pyqtgraph`) y utilidades CLI para automatización.

## Instalación

DriftScan puede ser instalado mediante `uv`:

```bash
uv tool install driftscan
```

## Demostración Rápida

Generá datos sintéticos y corré un análisis:

```bash
driftscan demo
```

Abrí la interfaz gráfica:

```bash
driftscan gui
```

## Arquitectura

El núcleo del software se asegura de no asumir características implícitas (por ejemplo, el manido `15°/hour`), y calcula la separación angular verdadera sobre la esfera celeste basándose en la altitud, azimut y latitud. Soporta trabajar _offline_ usando las efemérides cacheadas de `astropy`.

DriftScan no es un control de telescopios ni un reductor genérico. Es un banco de trabajo dedicado **exclusivamente al drift scanning**.

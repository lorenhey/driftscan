"""
Generador de datos sintéticos con "verdad conocida".
"""

import numpy as np
from astropy.time import Time, TimeDelta
from astropy.coordinates import EarthLocation
from driftscan.core import MeridianTransit, FixedTarget, DriftObservation

def generate_meridian_transit(
    location: EarthLocation,
    target: FixedTarget,
    start_time: Time,
    duration_sec: float = 3600,
    cadence_sec: float = 1.0,
    noise_level: float = 0.05,
    beam_fwhm_deg: float = 2.0,
    alt: float = 45.0
) -> DriftObservation:
    """
    Genera un tránsito de meridiano ideal (HA=0).
    """
    timestamps = start_time + TimeDelta(np.arange(0, duration_sec, cadence_sec), format='sec')
    
    geometry = MeridianTransit(alt=alt, az=0.0)
    
    # Calcular separación angular verdadera
    sep_deg = geometry.signed_offset(timestamps, location, target)
    
    # Modelo Gaussiano para el beam
    sigma = beam_fwhm_deg / (2 * np.sqrt(2 * np.log(2)))
    
    # Respuesta ideal
    signal = np.exp(-(sep_deg**2) / (2 * sigma**2))
    
    # Ruido
    signal += np.random.normal(0, noise_level, size=len(signal))
    
    obs = DriftObservation(timestamps, signal)
    obs.set_site(location)
    obs.set_geometry(geometry)
    obs.set_target(target)
    
    return obs

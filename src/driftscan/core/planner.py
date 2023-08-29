"""
Módulo para la planificación de tránsitos.
"""

from astropy.time import Time, TimeDelta
from astropy.coordinates import EarthLocation
import astropy.units as u
import numpy as np
from scipy.optimize import minimize_scalar

from driftscan.core.geometry import DriftGeometry, Target

class TransitPlanner:
    def __init__(self, location: EarthLocation, geometry: DriftGeometry):
        self.location = location
        self.geometry = geometry

    def closest_approach(self, target: Target, time_range: tuple[Time, Time]) -> dict:
        """
        Encuentra el instante de máxima aproximación entre el haz y el target dentro de un rango de tiempo.
        """
        t_start, t_end = time_range
        duration_sec = (t_end - t_start).sec
        
        # Función a minimizar: la separación angular en función del tiempo transcurrido (s)
        def objective_func(dt_sec):
            t = t_start + TimeDelta(dt_sec, format='sec')
            # angular_separation acepta arrays o escalares, pero scipy minimize_scalar pasa escalares.
            t_arr = Time([t])
            sep = self.geometry.angular_separation(t_arr, self.location, target)[0]
            return sep

        # Optimizador 1D acotado al rango temporal
        res = minimize_scalar(objective_func, bounds=(0, duration_sec), method='bounded', options={'xatol': 1e-1}) # precisión de 0.1s
        
        t_closest = t_start + TimeDelta(res.x, format='sec')
        min_sep = res.fun
        
        # Calcular LST, Alt/Az, etc. en el momento de máximo acercamiento
        t_arr = Time([t_closest])
        lst = t_arr.sidereal_time('apparent', longitude=self.location.lon).to_value(u.deg)[0]
        target_coord = target.get_coords(t_arr, self.location)
        
        return {
            'time_utc': t_closest,
            'min_separation_deg': min_sep,
            'lst_deg': lst,
            'target_ra': target_coord.ra.to_value(u.deg)[0] if target_coord.shape else target_coord.ra.to_value(u.deg),
            'target_dec': target_coord.dec.to_value(u.deg)[0] if target_coord.shape else target_coord.dec.to_value(u.deg),
        }

    def will_it_cross(self, target: Target, time_range: tuple[Time, Time], beam_radius_deg: float) -> str:
        """
        Determina si el target cruzará el haz dentro del radio dado.
        YES: separación mínima <= beam_radius / 2
        GRAZING: separación mínima > beam_radius / 2 y <= beam_radius
        NO: separación mínima > beam_radius
        """
        res = self.closest_approach(target, time_range)
        min_sep = res['min_separation_deg']
        
        if min_sep <= beam_radius_deg * 0.5:
            return "YES"
        elif min_sep <= beam_radius_deg:
            return "GRAZING"
        else:
            return "NO"

    def recording_window(self, closest_approach_time: Time, duration_sec: float) -> tuple[Time, Time]:
        """
        Sugiere una ventana de observación centrada en el momento de mayor acercamiento.
        """
        half = TimeDelta(duration_sec / 2.0, format='sec')
        return closest_approach_time - half, closest_approach_time + half

"""
Manejo estricto del tiempo, UTC y Sidereal Time.
"""

from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u
from astropy.utils.iers import conf
import numpy as np

# Configurar Astropy para que no falle si la red está inaccesible (Offline fallback)
conf.auto_download = True
conf.auto_max_age = None  # Si hay archivos viejos, que no falle y los use

class TimeHandler:
    @staticmethod
    def get_lst(times: Time, location: EarthLocation, apparent: bool = True) -> np.ndarray:
        """
        Calcula el Local Sidereal Time para un arreglo de tiempos en una ubicación.
        Por defecto utiliza el tiempo sideral aparente (Apparent Sidereal Time),
        que toma en cuenta la nutación y es el más exacto para observaciones astronómicas reales.
        """
        kind = 'apparent' if apparent else 'mean'
        # astropy Time.sidereal_time soporta arrays vectorizados
        lst = times.sidereal_time(kind, longitude=location.lon)
        return lst.to_value(u.hourangle)

    @staticmethod
    def from_utc_strings(timestamps: list[str]) -> Time:
        """
        Convierte una lista de strings UTC (ej. ISO 8601) a un objeto Time.
        """
        return Time(timestamps, format='isot', scale='utc')

    @staticmethod
    def from_mjd(mjd_array: np.ndarray) -> Time:
        """
        Convierte de MJD a un objeto Time de Astropy
        """
        return Time(mjd_array, format='mjd', scale='utc')

    @staticmethod
    def elapsed_seconds(times: Time) -> np.ndarray:
        """
        Devuelve el tiempo transcurrido en segundos desde el primer timestamp.
        """
        if len(times) == 0:
            return np.array([])
        dt = (times - times[0]).sec
        return dt

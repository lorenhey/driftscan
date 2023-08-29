"""
Modelos geométricos del Drift Scan.
"""

from abc import ABC, abstractmethod
from astropy.coordinates import EarthLocation, SkyCoord, AltAz, ICRS, get_sun, get_body
from astropy.time import Time
import astropy.units as u
import numpy as np

class Target(ABC):
    @abstractmethod
    def get_coords(self, times: Time, location: EarthLocation) -> SkyCoord:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

class FixedTarget(Target):
    def __init__(self, name: str, ra: float, dec: float, frame: str = 'icrs'):
        self._name = name
        self._coord = SkyCoord(ra=ra*u.deg, dec=dec*u.deg, frame=frame)
        
    def get_coords(self, times: Time, location: EarthLocation) -> SkyCoord:
        # Para fuentes fijas, la coordenada es constante en el frame ecuatorial
        return self._coord

    @property
    def name(self) -> str:
        return self._name

class SunTarget(Target):
    def get_coords(self, times: Time, location: EarthLocation) -> SkyCoord:
        return get_sun(times)
        
    @property
    def name(self) -> str:
        return "Sun"

class DriftGeometry(ABC):
    @abstractmethod
    def sky_path(self, times: Time, location: EarthLocation) -> SkyCoord:
        """
        Calcula las coordenadas celestes (RA, Dec) hacia las que apunta el haz en función del tiempo.
        """
        pass
        
    def angular_separation(self, times: Time, location: EarthLocation, target: Target) -> np.ndarray:
        """
        Calcula la separación angular (unsigned) entre el haz y el target en cada instante.
        Retorna la separación en grados.
        """
        beam_coords = self.sky_path(times, location)
        target_coords = target.get_coords(times, location)
        sep = beam_coords.separation(target_coords)
        return sep.to_value(u.deg)

    @abstractmethod
    def signed_offset(self, times: Time, location: EarthLocation, target: Target) -> np.ndarray:
        """
        Calcula el offset angular con signo (signed) si la geometría permite definir
        una dirección de scan. Por ejemplo, en Meridian Transit, se cruza en AR, 
        por lo que podemos dar un signo a la separación basado en la diferencia en tiempo/AR.
        Si no hay convención, retorna el unsigned.
        """
        pass

class FixedAltAz(DriftGeometry):
    """
    El telescopio apunta a una posición Alt/Az fija.
    El camino en el cielo es la traza de esa coordenada al moverse la Tierra.
    """
    def __init__(self, alt: float, az: float):
        self.alt = alt
        self.az = az

    def sky_path(self, times: Time, location: EarthLocation) -> SkyCoord:
        altaz_frame = AltAz(obstime=times, location=location)
        beam_altaz = SkyCoord(alt=self.alt*u.deg, az=self.az*u.deg, frame=altaz_frame)
        return beam_altaz.transform_to(ICRS)

    def signed_offset(self, times: Time, location: EarthLocation, target: Target) -> np.ndarray:
        # Para un AltAz genérico, la dirección del vector de cruce varía, 
        # pero podemos proyectar usando la componente horizontal.
        # Por ahora regresamos unsigned separation a menos que apliquemos una regla estricta.
        # El requerimiento dice: "Si no existe una orientación clara del corte: usar angular separation."
        return self.angular_separation(times, location, target)

class MeridianTransit(FixedAltAz):
    """
    Caso clásico: Alt fija, Az = 0 (Norte) o 180 (Sur).
    Cruza el meridiano local.
    """
    def __init__(self, alt: float, az: float = 0.0):
        if not (np.isclose(az, 0.0) or np.isclose(az, 180.0)):
            raise ValueError("MeridianTransit requiere Az = 0 (Norte) o Az = 180 (Sur).")
        super().__init__(alt=alt, az=az)

    def signed_offset(self, times: Time, location: EarthLocation, target: Target) -> np.ndarray:
        """
        Para Meridian Transit, la dirección es de Este a Oeste en el cielo.
        El cruce del meridiano (HA=0) implica LST = RA.
        Podemos aproximar el offset con signo usando el HA de la fuente.
        HA = LST - RA.
        Cuando HA < 0, la fuente está al Este (antes del cruce si apuntamos al meridiano).
        Cuando HA > 0, está al Oeste.
        Usaremos el signo del HA para darle signo a la separación.
        """
        sep = self.angular_separation(times, location, target)
        
        target_coords = target.get_coords(times, location)
        # Obtenemos LST
        lst = times.sidereal_time('apparent', longitude=location.lon)
        ha = lst - target_coords.ra
        ha.wrap_at('180d', inplace=True)
        
        # Signo de HA nos indica el lado del meridiano
        sign = np.sign(ha.to_value(u.deg))
        # Si la fuente pasa exactamente por el cenit, la definición es estable.
        # Devuelve separación con el signo del hour angle.
        return sep * sign

class FixedEquatorial(DriftGeometry):
    """
    El telescopio está montado de forma ecuatorial y aparcado en un Hour Angle (HA) y Declinación fijos.
    El motor está apagado.
    """
    def __init__(self, ha: float, dec: float):
        self.ha = ha
        self.dec = dec

    def sky_path(self, times: Time, location: EarthLocation) -> SkyCoord:
        lst = times.sidereal_time('apparent', longitude=location.lon).to_value(u.deg)
        # RA = LST - HA
        ra = (lst - self.ha) % 360.0
        return SkyCoord(ra=ra*u.deg, dec=self.dec*u.deg, frame='icrs')

    def signed_offset(self, times: Time, location: EarthLocation, target: Target) -> np.ndarray:
        sep = self.angular_separation(times, location, target)
        
        target_coords = target.get_coords(times, location)
        lst = times.sidereal_time('apparent', longitude=location.lon)
        
        # El telescopio está fijo en un HA. 
        # El HA de la fuente avanza con el tiempo: ha_fuente = lst - RA.
        # Cuando ha_fuente < self.ha, aún no ha llegado al haz de cruce (está al este del haz).
        # Cuando ha_fuente > self.ha, ya pasó.
        ha_fuente = lst - target_coords.ra
        ha_diff = ha_fuente - (self.ha * u.deg)
        ha_diff.wrap_at('180d', inplace=True)
        
        sign = np.sign(ha_diff.to_value(u.deg))
        return sep * sign

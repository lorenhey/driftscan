import pytest
import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u

from driftscan.core import (
    TimeHandler,
    MeridianTransit,
    FixedAltAz,
    FixedTarget,
    TransitPlanner
)

def test_meridian_transit_ha():
    location = EarthLocation(lat=-34.0*u.deg, lon=-58.0*u.deg, height=20*u.m)
    target = FixedTarget("Cas A", ra=350.85, dec=58.815)
    
    # Supongamos que la fuente cruza el meridiano. 
    # El HA debe ser 0.
    # LST = RA -> LST_deg = 350.85
    t0 = Time("2026-09-14T00:00:00", scale='utc')
    
    planner = TransitPlanner(location, MeridianTransit(alt=45.0, az=0.0))
    res = planner.closest_approach(target, (t0, t0 + 1*u.day))
    
    t_closest = res['time_utc']
    
    # En t_closest, el LST debería ser igual a la RA *aparente* de la fuente.
    lst = TimeHandler.get_lst(Time([t_closest]), location, apparent=True)[0] * 15.0 # convertir hora_angular a deg
    
    # Obtener RA aparente usando TETE (True Equator, True Equinox)
    from astropy.coordinates import TETE
    apparent_coord = target.get_coords(t_closest, location).transform_to(TETE(obstime=t_closest))
    ra_apparent = apparent_coord.ra.to_value(u.deg)
    
    # La diferencia angular entre LST y RA debe ser prácticamente cero,
    # pero el problema de optimización en scipy puede tener un pequeño margen numérico
    # y los efectos de refracción atmosférica no están en MeridianTransit.
    # Aún así, la precisión de 0.1 grados (unos 24 segundos) es razonable.
    
    assert np.isclose(lst, ra_apparent, atol=0.1)

def test_signed_offset_east_west():
    location = EarthLocation(lat=-34.0*u.deg, lon=-58.0*u.deg, height=20*u.m)
    target = FixedTarget("Test", ra=100.0, dec=-34.0)
    geom = MeridianTransit(alt=90.0, az=0.0)
    
    # Find transit time
    planner = TransitPlanner(location, geom)
    res = planner.closest_approach(target, (Time("2026-01-01T00:00:00"), Time("2026-01-02T00:00:00")))
    t_transit = res['time_utc']
    
    t_before = t_transit - 1*u.hour
    t_after = t_transit + 1*u.hour
    
    offset_before = geom.signed_offset(Time([t_before]), location, target)[0]
    offset_after = geom.signed_offset(Time([t_after]), location, target)[0]
    
    # Before transit, HA < 0 -> offset should be negative
    assert offset_before < -10.0
    # After transit, HA > 0 -> offset should be positive
    assert offset_after > 10.0

"""
Catálogo local y objetos móviles.
"""

from driftscan.core.geometry import FixedTarget, SunTarget, Target

class Catalog:
    def __init__(self):
        self._sources: dict[str, Target] = {}
        # Incorporar Sol por defecto
        self._sources["Sun"] = SunTarget()

    def add_fixed_target(self, name: str, ra: float, dec: float, frame: str = 'icrs'):
        """ Agrega un target fijo con coordenadas en grados """
        self._sources[name] = FixedTarget(name, ra, dec, frame)

    def get(self, name: str) -> Target:
        if name not in self._sources:
            raise KeyError(f"Target '{name}' no encontrado en el catálogo.")
        return self._sources[name]

    def list_names(self) -> list[str]:
        return list(self._sources.keys())

# Catálogo global por defecto
default_catalog = Catalog()
default_catalog.add_fixed_target("Cas A", 350.85, 58.815)
default_catalog.add_fixed_target("Cyg A", 299.868, 40.733)
default_catalog.add_fixed_target("Tau A", 83.633, 22.014)
default_catalog.add_fixed_target("Vir A", 187.705, 12.391)

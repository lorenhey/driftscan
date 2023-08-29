"""
Modelo principal de observación de Drift Scan.
"""

from astropy.time import Time
from astropy.coordinates import EarthLocation
import numpy as np

from driftscan.core.geometry import DriftGeometry, Target
from driftscan.core.time import TimeHandler
from driftscan.core.fitting import DriftFitter

class DriftObservation:
    def __init__(self, timestamps: Time, signal: np.ndarray, metadata: dict = None):
        if len(timestamps) != len(signal):
            raise ValueError("Timestamps y signal deben tener el mismo tamaño.")
        self.timestamps = timestamps
        self.signal = signal
        self.metadata = metadata or {}
        
        # Site and Geometry
        self.location: EarthLocation | None = None
        self.geometry: DriftGeometry | None = None
        self.target: Target | None = None
        
        # State
        self.mask = np.zeros(len(signal), dtype=bool) # True = masked/RFI
        
        # Fit results
        self.baseline_coefs = None
        self.baseline_method = None
        self.transit_popt = None
        self.transit_pcov = None
        self.is_extended = False

    def set_site(self, location: EarthLocation):
        self.location = location

    def set_geometry(self, geometry: DriftGeometry):
        self.geometry = geometry

    def set_target(self, target: Target):
        self.target = target

    def mask_region(self, start_idx: int, end_idx: int):
        self.mask[start_idx:end_idx] = True

    def unmask_region(self, start_idx: int, end_idx: int):
        self.mask[start_idx:end_idx] = False

    def get_valid_data(self) -> tuple[np.ndarray, np.ndarray]:
        valid_idx = ~self.mask
        return self.timestamps[valid_idx], self.signal[valid_idx]

    def elapsed_seconds(self) -> np.ndarray:
        return TimeHandler.elapsed_seconds(self.timestamps)

    def get_axis(self, axis_type: str) -> np.ndarray:
        """
        Retorna el eje X (tiempo, LST, offset angular, etc.) correspondiente a cada timestamp.
        """
        if axis_type == 'utc':
            return self.timestamps.to_value('isot')
        elif axis_type == 'elapsed':
            return self.elapsed_seconds()
        elif axis_type == 'lst':
            if not self.location:
                raise ValueError("Location is required for LST axis.")
            return TimeHandler.get_lst(self.timestamps, self.location)
        elif axis_type == 'angular_offset':
            if not self.location or not self.geometry or not self.target:
                raise ValueError("Location, geometry, and target required for angular offset.")
            return self.geometry.signed_offset(self.timestamps, self.location, self.target)
        else:
            raise ValueError(f"Unknown axis type: {axis_type}")

    def fit_baseline(self, baseline_regions: list[tuple[int, int]], method: str = 'linear'):
        """
        Calcula el baseline utilizando sólo los índices que caen en las regiones indicadas
        y que no estén enmascarados.
        """
        x_elapsed = self.elapsed_seconds()
        
        valid_x = []
        valid_y = []
        for start_idx, end_idx in baseline_regions:
            for i in range(start_idx, end_idx):
                if not self.mask[i]:
                    valid_x.append(x_elapsed[i])
                    valid_y.append(self.signal[i])
        
        valid_x = np.array(valid_x)
        valid_y = np.array(valid_y)
        
        coefs, meta = DriftFitter.fit_baseline(valid_x, valid_y, method=method)
        self.baseline_coefs = coefs
        self.baseline_method = method

    def get_baseline(self) -> np.ndarray:
        if self.baseline_coefs is None:
            return np.zeros_like(self.signal)
        return DriftFitter.evaluate_baseline(self.elapsed_seconds(), self.baseline_coefs, self.baseline_method)

    def fit_transit(self, p0: list):
        """
        Ajusta el perfil gaussiano sobre la señal menos el baseline,
        solo usando datos válidos (no enmascarados).
        p0 = [amplitude, center_elapsed_sec, sigma_sec]
        """
        if self.baseline_coefs is None:
            raise ValueError("Fit baseline first.")
            
        x_elapsed = self.elapsed_seconds()
        y_corr = self.signal - self.get_baseline()
        
        valid_idx = ~self.mask
        x_valid = x_elapsed[valid_idx]
        y_valid = y_corr[valid_idx]
        
        popt, pcov = DriftFitter.fit_transit_gaussian(x_valid, y_valid, p0=p0)
        self.transit_popt = popt
        self.transit_pcov = pcov

    def get_transit_fit(self) -> np.ndarray:
        """ Devuelve el ajuste Gaussiano en todo el eje (incluyendo el baseline) """
        if self.transit_popt is None:
            return np.zeros_like(self.signal)
        x_elapsed = self.elapsed_seconds()
        from driftscan.core.fitting import gaussian_beam_cut
        return gaussian_beam_cut(x_elapsed, *self.transit_popt) + self.get_baseline()

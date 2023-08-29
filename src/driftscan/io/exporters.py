"""
Exportadores para DriftScan.
"""

from pathlib import Path
import json
import numpy as np

from driftscan.core import DriftObservation

class Exporter:
    @staticmethod
    def to_csv(obs: DriftObservation, filepath: str | Path):
        """ Exporta la observación procesada a CSV """
        filepath = Path(filepath)
        valid_x, valid_y = obs.get_valid_data()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("utc_time,elapsed_sec,signal,baseline,fit,mask\n")
            
            times_iso = obs.timestamps.to_value('isot')
            elapsed = obs.elapsed_seconds()
            baseline = obs.get_baseline()
            fit = obs.get_transit_fit() if obs.transit_popt is not None else np.zeros_like(elapsed)
            
            for i in range(len(obs.timestamps)):
                f.write(f"{times_iso[i]},{elapsed[i]},{obs.signal[i]},{baseline[i]},{fit[i]},{obs.mask[i]}\n")
                
    @staticmethod
    def save_session(obs: DriftObservation, filepath: str | Path):
        """ Guarda la sesión de análisis en JSON """
        filepath = Path(filepath)
        session = {
            'metadata': obs.metadata,
            'mask_indices': np.where(obs.mask)[0].tolist(),
            'baseline': {
                'method': obs.baseline_method,
                'coefs': obs.baseline_coefs.tolist() if obs.baseline_coefs is not None else None
            },
            'transit': {
                'popt': obs.transit_popt.tolist() if obs.transit_popt is not None else None,
            }
        }
        if obs.location:
            session['location'] = {
                'lat': obs.location.lat.deg,
                'lon': obs.location.lon.deg,
                'height': obs.location.height.to_value('m')
            }
        # Geometry and target should also be serialized. For V1 we can keep it simple.
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session, f, indent=4)

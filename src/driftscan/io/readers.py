"""
Lectores de datos para DriftScan.
"""

import numpy as np
from astropy.time import Time
from pathlib import Path
import json

from driftscan.core import DriftObservation, TimeHandler

class CSVReader:
    @staticmethod
    def read(filepath: str | Path, time_col: str = None, signal_col: str = None) -> DriftObservation:
        """
        Lee un archivo CSV/TSV e intenta parsear tiempos y señal.
        """
        filepath = Path(filepath)
        
        # Detectar delimitador leyendo la primera línea
        with open(filepath, 'r') as f:
            header_line = f.readline().strip()
            
        delimiter = ','
        if '\t' in header_line:
            delimiter = '\t'
        elif ';' in header_line:
            delimiter = ';'
            
        # Usar genfromtxt para extraer nombres de columnas y datos
        data = np.genfromtxt(filepath, delimiter=delimiter, names=True, dtype=None, encoding='utf-8')
        
        if len(data.shape) == 0:
            raise ValueError(f"El archivo {filepath} no contiene suficientes datos.")
            
        col_names = data.dtype.names
        
        # Autodetección básica si no se proveen nombres
        if not time_col:
            time_candidates = ['time', 'timestamp', 'utc', 'datetime', 't']
            for c in col_names:
                if c.lower() in time_candidates:
                    time_col = c
                    break
        if not signal_col:
            sig_candidates = ['signal', 'power', 'db', 'counts', 'amplitude', 'y', 'p']
            for c in col_names:
                if c.lower() in sig_candidates:
                    signal_col = c
                    break
                    
        if not time_col or not signal_col:
            # Fallback a primera y segunda columna
            time_col = col_names[0]
            signal_col = col_names[1]
            
        raw_times = data[time_col]
        signal_array = data[signal_col].astype(float)
        
        # Parsear timestamps
        if np.issubdtype(raw_times.dtype, np.number):
            # Asumimos MJD si empieza en > 40000, o segundos desde un inicio
            if raw_times[0] > 40000:
                times = TimeHandler.from_mjd(raw_times)
            else:
                # Si son tiempos relativos, necesitamos un sidecar para el startTime, 
                # pero por ahora lo hacemos absoluto si es posible.
                times = Time(raw_times, format='unix') # Fallback temporal
        else:
            times = TimeHandler.from_utc_strings(list(raw_times))
            
        # Buscar sidecar de metadatos (archivo .json con el mismo nombre)
        meta_path = filepath.with_suffix('.json')
        metadata = {}
        if meta_path.exists():
            with open(meta_path, 'r') as f:
                metadata = json.load(f)
                
        # Crear y devolver la observación
        obs = DriftObservation(times, signal_array, metadata)
        return obs

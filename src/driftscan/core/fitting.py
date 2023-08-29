"""
Módulo para ajustar baselines y tránsitos a observaciones de Drift Scan.
"""

import numpy as np
from scipy.optimize import curve_fit

def constant_baseline(x, c):
    return np.full_like(x, c)

def linear_baseline(x, m, c):
    return m * x + c

def quadratic_baseline(x, a, b, c):
    return a * x**2 + b * x + c

def gaussian_beam_cut(x, amplitude, center, sigma):
    """
    Modelo de perfil Gaussiano.
    """
    return amplitude * np.exp(-((x - center)**2) / (2 * sigma**2))

def gaussian_with_linear_baseline(x, amplitude, center, sigma, m, c):
    return gaussian_beam_cut(x, amplitude, center, sigma) + linear_baseline(x, m, c)

class DriftFitter:
    @staticmethod
    def fit_baseline(x: np.ndarray, y: np.ndarray, method: str = 'linear') -> tuple[np.ndarray, dict]:
        """
        Ajusta una línea de base (baseline) usando sólo las regiones que no están enmascaradas.
        Se asume que `x` e `y` pasados ya corresponden a las regiones de baseline puras.
        Devuelve (coeficientes, metadata).
        """
        if method == 'constant':
            popt, pcov = curve_fit(constant_baseline, x, y)
            return popt, {'method': 'constant'}
        elif method == 'linear':
            popt, pcov = curve_fit(linear_baseline, x, y)
            return popt, {'method': 'linear'}
        elif method == 'quadratic':
            popt, pcov = curve_fit(quadratic_baseline, x, y)
            return popt, {'method': 'quadratic'}
        else:
            raise ValueError(f"Método de baseline {method} no soportado.")

    @staticmethod
    def evaluate_baseline(x: np.ndarray, coefs: np.ndarray, method: str) -> np.ndarray:
        if method == 'constant':
            return constant_baseline(x, *coefs)
        elif method == 'linear':
            return linear_baseline(x, *coefs)
        elif method == 'quadratic':
            return quadratic_baseline(x, *coefs)
        return np.zeros_like(x)

    @staticmethod
    def fit_transit_gaussian(x: np.ndarray, y: np.ndarray, p0: list) -> tuple[np.ndarray, np.ndarray]:
        """
        Ajusta un modelo Gaussiano (con baseline sustraída o no, dependiendo de lo que reciba).
        Asume que y ya tiene el baseline sustraído.
        Devuelve (popt, pcov). popt = [amplitude, center, sigma]
        """
        popt, pcov = curve_fit(gaussian_beam_cut, x, y, p0=p0)
        return popt, pcov

    @staticmethod
    def calculate_fwhm(sigma: float) -> float:
        """ FWHM = 2 * sqrt(2 * ln(2)) * sigma """
        return 2 * np.sqrt(2 * np.log(2)) * sigma

    @staticmethod
    def center_residual(predicted_center: float, observed_center: float) -> float:
        return observed_center - predicted_center

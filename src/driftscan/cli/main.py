"""
Interfaz de Línea de Comandos para DriftScan.
"""

import typer
from rich.console import Console
from rich.table import Table
from pathlib import Path

from driftscan.core import Catalog, default_catalog, MeridianTransit, TransitPlanner
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u

app = typer.Typer(help="DriftScan CLI: Convierte rotación terrestre en ciencia.")
console = Console()

@app.command()
def plan(
    target: str = typer.Argument(..., help="Nombre del target (ej. 'Cas A')"),
    lat: float = typer.Option(..., help="Latitud del sitio (grados)"),
    lon: float = typer.Option(..., help="Longitud del sitio (grados)"),
    alt: float = typer.Option(90.0, help="Altitud del telescopio (grados) para Meridian Transit"),
    date: str = typer.Option("2026-09-14T00:00:00", help="Fecha inicial (UTC)"),
    duration_hours: float = typer.Option(24.0, help="Rango de búsqueda en horas")
):
    """
    Planifica el tránsito de una fuente por el haz.
    """
    location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg)
    geom = MeridianTransit(alt=alt)
    planner = TransitPlanner(location, geom)
    
    t_target = default_catalog.get(target)
    
    t0 = Time(date, format='isot', scale='utc')
    t1 = t0 + duration_hours * u.hour
    
    res = planner.closest_approach(t_target, (t0, t1))
    
    console.print(f"[bold green]Plan de Tránsito para {target}[/bold green]")
    table = Table("Métrica", "Valor")
    table.add_row("Closest Approach (UTC)", res['time_utc'].isot)
    table.add_row("LST en cruce (grados)", f"{res['lst_deg']:.2f}")
    table.add_row("Separación Mínima (grados)", f"{res['min_separation_deg']:.3f}")
    
    console.print(table)

@app.command()
def demo():
    """
    Ejecuta una demostración de DriftScan generando datos sintéticos.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from demo.synthetic import generate_meridian_transit
    console.print("[bold cyan]Generando Drift Scan sintético (Meridian Transit)...[/bold cyan]")
    
    # VLA location para ver Cas A bien alto
    location = EarthLocation(lat=34.07*u.deg, lon=-107.61*u.deg)
    t_target = default_catalog.get("Cas A")
    
    # Encontremos el tránsito real para centrar la demo
    from driftscan.core import TransitPlanner, MeridianTransit
    
    # Cas A dec = 58.8. Culmination altitude = 90 - |34.07 - 58.8| = 90 - 24.73 = 65.27
    planner = TransitPlanner(location, MeridianTransit(alt=65.27, az=0.0))
    res = planner.closest_approach(t_target, (Time("2026-09-14T00:00:00"), Time("2026-09-15T00:00:00")))
    
    # Comenzar 1 hora antes del tránsito
    t0 = res['time_utc'] - 3600 * u.s
    
    obs = generate_meridian_transit(location, t_target, t0, duration_sec=7200, beam_fwhm_deg=2.5, alt=65.27)
    
    console.print(f"Generadas {len(obs.timestamps)} muestras.")
    
    # Simulate a fit
    # We cheat the regions for the demo
    obs.fit_baseline([(0, 1000), (6000, 7200)], method='constant')
    
    # A guess for the gaussian
    obs.fit_transit(p0=[1.0, 3600.0, 500.0])
    
    table = Table("Parámetro", "Valor Recuperado")
    from driftscan.core.fitting import DriftFitter
    fwhm_sec = DriftFitter.calculate_fwhm(obs.transit_popt[2])
    
    table.add_row("Amplitud Peak", f"{obs.transit_popt[0]:.3f}")
    table.add_row("Centro (s desde inicio)", f"{obs.transit_popt[1]:.1f}")
    table.add_row("FWHM (tiempo)", f"{fwhm_sec:.1f} s")
    
    console.print(table)
    console.print("[green]Demostración finalizada exitosamente.[/green]")

@app.command()
def gui():
    """
    Abre la interfaz gráfica principal de DriftScan.
    """
    from driftscan.gui.main import main as gui_main
    gui_main()

if __name__ == "__main__":
    app()

"""
Interfaz Gráfica Principal de DriftScan.
"""

import sys
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, HttpWidget, QWidget,
    QHBoxLayout, QPushButton, QComboBox, QLabel, QFileDialog, QSplitter
)
from PySide6.QtCore import Qt
import pyqtgraph as pg

from astropy.time import Time
from driftscan.io.readers import CSVReader
from driftscan.core import DriftObservation, TransitPlanner

class DriftScanGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drift")
        self.resize(1000, 600)
        
        self.obs: DriftObservation | None = None
        
        # UI Setup
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QHBoxLayout(main_widget)
        
        # Left Panel (Controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.btn_open = QPushButton("Abrir CSV")
        self.btn_open.clicked.connect(self.open_file)
        left_layout.addWidget(self.btn_open)
        
        left_layout.addWidget(QLabel("Eje X:"))
        self.combo_x = QComboBox()
        self.combo_x.addItems(["elapsed", "utc", "lst", "angular_offset"])
        self.combo_x.currentTextChanged.connect(self.update_plot)
        left_layout.addWidget(self.combo_x)
        
        self.lbl_info = QLabel("Ninguna observación cargada.")
        self.lbl_info.setWordWrap(True)
        left_layout.addWidget(self.lbl_info)
        
        # Right Panel (Plot)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.setLabel('left', 'Señal')
        self.plot_item.setLabel('bottom', 'Tiempo transcurrido (s)')
        
        self.curve = self.plot_item.plot(pen=pg.mkPen('b', width=2))
        self.baseline_curve = self.plot_item.plot(pen=pg.mkPen('r', width=2, style=Qt.PenStyle.DashLine))
        self.fit_curve = self.plot_item.plot(pen=pg.mkPen('g', width=2))
        
        # Crosshair
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.plot_item.addItem(self.vLine, ignoreBounds=True)
        self.plot_item.addItem(self.hLine, ignoreBounds=True)
        
        self.proxy = pg.SignalProxy(self.plot_item.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.plot_widget)
        splitter.setStretchFactor(1, 4)
        
        layout.addWidget(splitter)
        
        # Demo button
        self.btn_demo = QPushButton("Cargar Demo")
        self.btn_demo.clicked.connect(self.load_demo)
        left_layout.addWidget(self.btn_demo)

    def open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Abrir Observación", "", "CSV Files (*.csv);;All Files (*)")
        if filepath:
            try:
                self.obs = CSVReader.read(filepath)
                self.lbl_info.setText(f"Cargado: {filepath}\nMuestras: {len(self.obs.timestamps)}")
                self.update_plot()
            except Exception as e:
                self.lbl_info.setText(f"Error: {e}")

    def load_demo(self):
        import astropy.units as u
        from astropy.coordinates import EarthLocation
        from driftscan.core import default_catalog, MeridianTransit
        from driftscan.demo.synthetic import generate_meridian_transit
        
        location = EarthLocation(lat=34.07*u.deg, lon=-107.61*u.deg)
        t_target = default_catalog.get("Cas A")
        
        from driftscan.core import TransitPlanner
        planner = TransitPlanner(location, MeridianTransit(alt=65.27, az=0.0))
        res = planner.closest_approach(t_target, (Time("2026-09-14T00:00:00"), Time("2026-09-15T00:00:00")))
        t0 = res['time_utc'] - 3600 * u.s
        
        self.obs = generate_meridian_transit(location, t_target, t0, duration_sec=7200, beam_fwhm_deg=2.5, alt=65.27)
        self.obs.fit_baseline([(0, 1000), (6000, 7200)], method='constant')
        self.obs.fit_transit(p0=[1.0, 3600.0, 500.0])
        
        self.lbl_info.setText(f"Demo cargado (Cas A)\nMuestras: {len(self.obs.timestamps)}\nAmplitud: {self.obs.transit_popt[0]:.2f}")
        self.update_plot()

    def update_plot(self):
        if not self.obs:
            return
            
        axis_type = self.combo_x.currentText()
        
        try:
            x_data = self.obs.get_axis(axis_type)
            
            # UTC to elapsed conceptually for plotting if strings (pyqtgraph uses numbers)
            if axis_type == 'utc':
                # No podemos plotear strings UTC en pyqtgraph facilmente,
                # normalmente plotteamos timestamps unix
                x_data = self.obs.timestamps.unix
                self.plot_item.setLabel('bottom', 'Tiempo Unix')
            else:
                self.plot_item.setLabel('bottom', axis_type)
                
            y_data = self.obs.signal
            self.curve.setData(x_data, y_data)
            
            if self.obs.baseline_coefs is not None:
                self.baseline_curve.setData(x_data, self.obs.get_baseline())
                
            if self.obs.transit_popt is not None:
                self.fit_curve.setData(x_data, self.obs.get_transit_fit())
                
        except Exception as e:
            self.lbl_info.setText(f"Error de Eje: {e}")

    def mouseMoved(self, evt):
        if not self.obs: return
        pos = evt[0]
        if self.plot_item.sceneBoundingRect().contains(pos):
            mousePoint = self.plot_item.vb.mapSceneToView(pos)
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())
            # Idealmente buscamos el índice más cercano
            axis_type = self.combo_x.currentText()
            try:
                x_data = self.obs.get_axis(axis_type)
                if axis_type == 'utc':
                    x_data = self.obs.timestamps.unix
                
                idx = (np.abs(x_data - mousePoint.x())).argmin()
                time_utc = self.obs.timestamps[idx].isot
                sig = self.obs.signal[idx]
                
                self.plot_widget.setTitle(f"X: {mousePoint.x():.2f} | Señal: {sig:.3f} | UTC: {time_utc}")
            except:
                pass

def main():
    app = QApplication(sys.argv)
    window = DriftScanGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

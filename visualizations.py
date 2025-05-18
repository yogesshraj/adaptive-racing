import pyqtgraph as pg
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QGraphicsRectItem
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass

# Constants for visualization
HISTORY_LENGTH = 500  # Number of data points to keep in history
TRACK_MAP_SIZE = 600  # Size of track map in pixels
GRAPH_HEIGHT = 150   # Height of each telemetry graph

@dataclass
class TelemetryHistory:
    """Class to store telemetry history for plotting"""
    timestamps: deque
    speed: deque
    throttle: deque
    brake: deque
    steering: deque
    rpm: deque
    gear: deque
    tire_temps: List[deque]  # List of 4 deques for each tire
    lap_distance: deque

class TelemetryVisualizer:
    def __init__(self, parent_widget):
        """Initialize the telemetry visualizer"""
        self.parent = parent_widget
        self.history = TelemetryHistory(
            timestamps=deque(maxlen=HISTORY_LENGTH),
            speed=deque(maxlen=HISTORY_LENGTH),
            throttle=deque(maxlen=HISTORY_LENGTH),
            brake=deque(maxlen=HISTORY_LENGTH),
            steering=deque(maxlen=HISTORY_LENGTH),
            rpm=deque(maxlen=HISTORY_LENGTH),
            gear=deque(maxlen=HISTORY_LENGTH),
            tire_temps=[deque(maxlen=HISTORY_LENGTH) for _ in range(4)],
            lap_distance=deque(maxlen=HISTORY_LENGTH)
        )
        
        # Setup layout
        self.layout = pg.GraphicsLayoutWidget()
        self.layout.setBackground('w')  # White background
        
        # Create plots
        self.setup_telemetry_plots()
        self.setup_track_map()
        self.setup_tire_visualization()
        
        # Initialize track position
        self.current_position = 0
        self.track_length = 0
        self.sector_boundaries = []

    def setup_telemetry_plots(self):
        """Setup the real-time telemetry plots"""
        # Speed plot
        self.speed_plot = self.layout.addPlot(row=0, col=0)
        self.speed_plot.setTitle('Speed (km/h)', color='k')
        self.speed_plot.showGrid(x=True, y=True)
        self.speed_curve = self.speed_plot.plot(pen=pg.mkPen('b', width=2), name='Speed')
        self.speed_plot.setYRange(0, 350)  # F1 cars max speed around 350 km/h
        self.speed_plot.enableAutoRange(y=True)
        
        self.layout.nextRow()
        
        # Throttle/Brake plot
        self.pedals_plot = self.layout.addPlot(row=1, col=0)
        self.pedals_plot.setTitle('Throttle/Brake (%)', color='k')
        self.pedals_plot.showGrid(x=True, y=True)
        self.pedals_plot.addLegend()
        self.throttle_curve = self.pedals_plot.plot(pen=pg.mkPen('g', width=2), name='Throttle')
        self.brake_curve = self.pedals_plot.plot(pen=pg.mkPen('r', width=2), name='Brake')
        self.pedals_plot.setYRange(0, 100)
        
        self.layout.nextRow()
        
        # Steering plot
        self.steering_plot = self.layout.addPlot(row=2, col=0)
        self.steering_plot.setTitle('Steering Angle', color='k')
        self.steering_plot.showGrid(x=True, y=True)
        self.steering_curve = self.steering_plot.plot(pen=pg.mkPen('y', width=2), name='Steering')
        self.steering_plot.setYRange(-100, 100)
        
        # Set common properties
        for plot in [self.speed_plot, self.pedals_plot, self.steering_plot]:
            plot.setLabel('left', color='k')
            plot.setLabel('bottom', 'Time', color='k')
            plot.getAxis('left').setPen('k')
            plot.getAxis('bottom').setPen('k')
            plot.setMouseEnabled(x=True, y=False)  # Allow x-axis zoom only
            plot.setMenuEnabled(False)  # Disable right-click menu

    def setup_track_map(self):
        """Setup the track map visualization"""
        self.track_map = self.layout.addViewBox(row=0, col=1, rowspan=2)
        self.track_map.setAspectLocked(True)
        
        # Create track outline placeholder
        self.track_outline = pg.PlotCurveItem(pen=pg.mkPen('k', width=3))
        self.track_map.addItem(self.track_outline)
        
        # Create car position indicator
        self.car_position = pg.ScatterPlotItem(size=15, pen=pg.mkPen('b', width=2), brush=pg.mkBrush('r'))
        self.track_map.addItem(self.car_position)
        
        # Create sector markers
        self.sector_lines = []
        for _ in range(2):  # 2 sector boundaries
            line = pg.InfiniteLine(angle=90, pen=pg.mkPen('g', width=2, style=Qt.DashLine))
            self.track_map.addItem(line)
            self.sector_lines.append(line)
            
        # Add sector labels
        self.sector_labels = []
        for i in range(3):
            label = pg.TextItem(f"S{i+1}", color='k', anchor=(0.5, 0))
            self.track_map.addItem(label)
            self.sector_labels.append(label)

    def setup_tire_visualization(self):
        """Setup the tire temperature visualization"""
        self.tire_view = self.layout.addViewBox(row=2, col=1)
        self.tire_view.setAspectLocked(True)
        
        # Create tire temperature indicators with labels
        self.tire_indicators = []
        self.tire_labels = []
        positions = [(0, 0), (1, 0), (0, 1), (1, 1)]  # 2x2 grid for 4 tires
        labels = ['FL', 'FR', 'RL', 'RR']
        
        for pos, label in zip(positions, labels):
            # Create tire rectangle
            rect = QGraphicsRectItem(pos[0] * 60, pos[1] * 60, 50, 50)
            rect.setPen(pg.mkPen('k', width=2))
            self.tire_indicators.append(rect)
            self.tire_view.addItem(rect)
            
            # Add temperature label
            temp_label = pg.TextItem('0°C', anchor=(0.5, 0.5))
            temp_label.setPos(pos[0] * 60 + 25, pos[1] * 60 + 25)
            self.tire_labels.append(temp_label)
            self.tire_view.addItem(temp_label)
            
            # Add tire position label
            pos_label = pg.TextItem(label, anchor=(0.5, 0))
            pos_label.setPos(pos[0] * 60 + 25, pos[1] * 60 - 15)
            self.tire_view.addItem(pos_label)

    def update_telemetry(self, telemetry_data: Dict):
        """Update all visualizations with new telemetry data"""
        # Add new data to history
        timestamp = len(self.history.timestamps)
        self.history.timestamps.append(timestamp)
        self.history.speed.append(telemetry_data.get('speed', 0))
        self.history.throttle.append(telemetry_data.get('throttle', 0) * 100)
        self.history.brake.append(telemetry_data.get('brake', 0) * 100)
        self.history.steering.append(telemetry_data.get('steer', 0) * 100)  # Scale to percentage
        self.history.rpm.append(telemetry_data.get('rpm', 0))
        self.history.gear.append(telemetry_data.get('gear', 0))
        self.history.lap_distance.append(telemetry_data.get('lap_distance', 0))
        
        # Update tire temperatures
        temps = telemetry_data.get('tyresSurfaceTemperature', [0, 0, 0, 0])
        for i, temp in enumerate(temps):
            self.history.tire_temps[i].append(temp)
        
        # Update plots
        self._update_telemetry_plots()
        self._update_track_position()
        self._update_tire_temperatures()

    def _update_telemetry_plots(self):
        """Update the telemetry plot curves"""
        x = list(self.history.timestamps)
        
        # Update speed plot
        self.speed_curve.setData(x, list(self.history.speed))
        
        # Update throttle/brake plot
        self.throttle_curve.setData(x, list(self.history.throttle))
        self.brake_curve.setData(x, list(self.history.brake))
        
        # Update steering plot
        self.steering_curve.setData(x, list(self.history.steering))

    def _update_track_position(self):
        """Update the car position on track map"""
        if not self.track_length:
            return
            
        # Calculate position on track (simplified circular track for now)
        lap_distance = self.history.lap_distance[-1]
        angle = (lap_distance / self.track_length) * 2 * np.pi
        radius = TRACK_MAP_SIZE / 3
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        
        self.car_position.setData([x], [y])

    def _update_tire_temperatures(self):
        """Update the tire temperature visualization"""
        for i, temps in enumerate(self.history.tire_temps):
            if not temps:
                continue
                
            temp = temps[-1]
            # Color scale: blue (cold) -> green (optimal) -> red (hot)
            # Assuming optimal temp range is 90-100°C
            if temp < 80:
                color = QColor(0, 0, 255, 200)  # Blue
            elif temp > 100:
                color = QColor(255, 0, 0, 200)  # Red
            else:
                color = QColor(0, 255, 0, 200)  # Green
            
            self.tire_indicators[i].setBrush(pg.mkBrush(color))
            self.tire_labels[i].setText(f"{temp}°C")

    def set_track_info(self, track_length: float, sector_distances: List[float]):
        """Set track information for visualization"""
        self.track_length = track_length
        self.sector_boundaries = sector_distances
        
        # Create simplified circular track
        angles = np.linspace(0, 2*np.pi, 100)
        radius = TRACK_MAP_SIZE / 3
        x = radius * np.cos(angles)
        y = radius * np.sin(angles)
        self.track_outline.setData(x, y)
        
        # Update sector lines and labels
        for i, distance in enumerate(sector_distances):
            angle = (distance / track_length) * 2 * np.pi
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            self.sector_lines[i].setPos(x)
            
            # Position sector labels
            label_angle = (distance / track_length * 2 * np.pi + np.pi/8)
            label_x = (radius + 30) * np.cos(label_angle)
            label_y = (radius + 30) * np.sin(label_angle)
            self.sector_labels[i].setPos(label_x, label_y)
        
        # Position the last sector label
        last_label_angle = np.pi/8
        label_x = (radius + 30) * np.cos(last_label_angle)
        label_y = (radius + 30) * np.sin(last_label_angle)
        self.sector_labels[2].setPos(label_x, label_y)

    def clear_history(self):
        """Clear all telemetry history"""
        self.history = TelemetryHistory(
            timestamps=deque(maxlen=HISTORY_LENGTH),
            speed=deque(maxlen=HISTORY_LENGTH),
            throttle=deque(maxlen=HISTORY_LENGTH),
            brake=deque(maxlen=HISTORY_LENGTH),
            steering=deque(maxlen=HISTORY_LENGTH),
            rpm=deque(maxlen=HISTORY_LENGTH),
            gear=deque(maxlen=HISTORY_LENGTH),
            tire_temps=[deque(maxlen=HISTORY_LENGTH) for _ in range(4)],
            lap_distance=deque(maxlen=HISTORY_LENGTH)
        ) 
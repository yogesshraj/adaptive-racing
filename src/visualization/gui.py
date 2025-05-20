from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
import sys
from src.telemetry.listener import F1TelemetryListener, TelemetryData

class TelemetryDisplay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("F1 22 Telemetry")
        self.setMinimumSize(800, 400)

        # Initialize telemetry listener
        self.telemetry = F1TelemetryListener()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create telemetry displays
        self.create_telemetry_widgets()
        layout.addLayout(self.telemetry_layout)

        # Setup update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(16)  # ~60 FPS update rate

        # Start telemetry listener
        self.telemetry.start()

    def create_telemetry_widgets(self):
        self.telemetry_layout = QVBoxLayout()
        
        # Speed display
        speed_layout = QHBoxLayout()
        self.speed_label = QLabel("Speed:")
        self.speed_value = QLabel("0 km/h")
        speed_layout.addWidget(self.speed_label)
        speed_layout.addWidget(self.speed_value)
        self.telemetry_layout.addLayout(speed_layout)

        # RPM display
        rpm_layout = QHBoxLayout()
        self.rpm_label = QLabel("RPM:")
        self.rpm_bar = QProgressBar()
        self.rpm_bar.setRange(0, 12000)
        rpm_layout.addWidget(self.rpm_label)
        rpm_layout.addWidget(self.rpm_bar)
        self.telemetry_layout.addLayout(rpm_layout)

        # Throttle display
        throttle_layout = QHBoxLayout()
        self.throttle_label = QLabel("Throttle:")
        self.throttle_bar = QProgressBar()
        self.throttle_bar.setRange(0, 100)
        throttle_layout.addWidget(self.throttle_label)
        throttle_layout.addWidget(self.throttle_bar)
        self.telemetry_layout.addLayout(throttle_layout)

        # Brake display
        brake_layout = QHBoxLayout()
        self.brake_label = QLabel("Brake:")
        self.brake_bar = QProgressBar()
        self.brake_bar.setRange(0, 100)
        brake_layout.addWidget(self.brake_label)
        brake_layout.addWidget(self.brake_bar)
        self.telemetry_layout.addLayout(brake_layout)

        # Steering display
        steering_layout = QHBoxLayout()
        self.steering_label = QLabel("Steering:")
        self.steering_value = QLabel("0°")
        steering_layout.addWidget(self.steering_label)
        steering_layout.addWidget(self.steering_value)
        self.telemetry_layout.addLayout(steering_layout)

        # Gear display
        gear_layout = QHBoxLayout()
        self.gear_label = QLabel("Gear:")
        self.gear_value = QLabel("N")
        gear_layout.addWidget(self.gear_label)
        gear_layout.addWidget(self.gear_value)
        self.telemetry_layout.addLayout(gear_layout)

        # Lap time display
        laptime_layout = QHBoxLayout()
        self.laptime_label = QLabel("Current Lap:")
        self.laptime_value = QLabel("00:00.000")
        laptime_layout.addWidget(self.laptime_label)
        laptime_layout.addWidget(self.laptime_value)
        self.telemetry_layout.addLayout(laptime_layout)

    def update_telemetry(self):
        """Update all telemetry displays with latest data."""
        data = self.telemetry.get_current_telemetry()
        
        # Update displays
        self.speed_value.setText(f"{data.speed:.1f} km/h")
        self.rpm_bar.setValue(int(data.engine_rpm))
        self.throttle_bar.setValue(int(data.throttle * 100))
        self.brake_bar.setValue(int(data.brake * 100))
        self.steering_value.setText(f"{data.steering:.1f}°")
        
        # Convert gear number to display format
        gear_display = {
            -1: "R",
            0: "N",
        }.get(data.gear, str(data.gear))
        self.gear_value.setText(gear_display)

        # Format lap time as mm:ss.ms
        minutes = int(data.current_lap_time / 60)
        seconds = int(data.current_lap_time % 60)
        milliseconds = int((data.current_lap_time * 1000) % 1000)
        self.laptime_value.setText(f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}")

    def closeEvent(self, event):
        """Clean up when the window is closed."""
        self.telemetry.stop()
        event.accept() 
from PyQt5.QtWidgets import (QMainWindow, QApplication, QTabWidget, QWidget, 
                            QVBoxLayout, QLabel, QPushButton, QHBoxLayout, 
                            QFrame, QGridLayout, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
import sys
from ..telemetry.listener import TelemetryListener
from ..telemetry.models import TelemetryData

class MainWindow(QMainWindow):
    telemetry_signal = pyqtSignal(object)  # Will emit TelemetryData

    def __init__(self):
        super().__init__()
        self.setWindowTitle("F1 22 Telemetry - Modern")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize telemetry listener
        self.telemetry_listener = TelemetryListener()
        self.current_telemetry = TelemetryData()
        
        # Connect the signal to the UI update slot
        self.telemetry_signal.connect(self._on_telemetry_update_mainthread)
        
        # Set modern color scheme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #007acc;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #3a3a3a;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0098ff;
            }
            QPushButton:pressed {
                background-color: #005999;
            }
            QProgressBar {
                border: 2px solid #3a3a3a;
                border-radius: 4px;
                text-align: center;
                background-color: #2d2d2d;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                border-radius: 2px;
            }
        """)

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Create header
        header = QFrame()
        header.setStyleSheet("background-color: #007acc; padding: 10px;")
        header_layout = QHBoxLayout(header)
        
        title = QLabel("F1 22 Telemetry")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        header_layout.addWidget(title)
        
        # Add status indicator
        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet("color: #ff4444; font-size: 16px;")
        header_layout.addWidget(self.status_label, alignment=Qt.AlignRight)
        
        main_layout.addWidget(header)

        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(True)
        
        # Add tabs with modern content
        self.tabs.addTab(self._make_live_tab(), "Live Telemetry")
        self.tabs.addTab(self._make_session_tab(), "Session Data")
        self.tabs.addTab(self._make_analysis_tab(), "Analysis")
        self.tabs.addTab(self._make_visualization_tab(), "Visualizations")
        
        main_layout.addWidget(self.tabs)

        # Start telemetry listener
        self.telemetry_listener.start(self._on_telemetry_update_threadsafe)
        
        # Update status periodically
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(1000)  # Update every second

    def _on_telemetry_update_threadsafe(self, telemetry: TelemetryData):
        """Called from background thread, emits signal to main thread."""
        self.telemetry_signal.emit(telemetry)

    def _on_telemetry_update_mainthread(self, telemetry: TelemetryData):
        """Handle new telemetry data in the main thread."""
        self.current_telemetry = telemetry
        self._update_live_tab()

    def _update_status(self):
        """Update connection status"""
        if self.telemetry_listener.running:
            self.status_label.setText("● Connected")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 16px;")
        else:
            self.status_label.setText("● Disconnected")
            self.status_label.setStyleSheet("color: #ff4444; font-size: 16px;")

    def _update_live_tab(self):
        """Update live telemetry display"""
        if not hasattr(self, 'speed_label'):
            return

        try:
            # Update speed
            self.speed_label.setText(f"{self.current_telemetry.speed} km/h")
            
            # Update RPM
            self.rpm_label.setText(str(self.current_telemetry.rpm))
            
            # Update gear
            gear_text = "N" if self.current_telemetry.gear == 0 else "R" if self.current_telemetry.gear == -1 else str(self.current_telemetry.gear)
            self.gear_label.setText(gear_text)
            
            # Update throttle and brake (ensure values are between 0 and 100)
            throttle_value = max(0, min(100, int(self.current_telemetry.throttle * 100)))
            brake_value = max(0, min(100, int(self.current_telemetry.brake * 100)))
            self.throttle_bar.setValue(throttle_value)
            self.brake_bar.setValue(brake_value)
            
            # Update DRS
            drs_text = "ON" if self.current_telemetry.drs == 1 else "OFF"
            self.drs_label.setText(drs_text)
        except Exception as e:
            print(f"Error updating UI: {e}")
            # Don't re-raise the exception to keep the UI running

    def _make_live_tab(self):
        widget = QWidget()
        layout = QGridLayout()
        
        # Speed display
        speed_frame = self._create_metric_frame("SPEED", "0 km/h")
        self.speed_label = speed_frame.findChild(QLabel, "value")
        layout.addWidget(speed_frame, 0, 0)
        
        # RPM display
        rpm_frame = self._create_metric_frame("RPM", "0")
        self.rpm_label = rpm_frame.findChild(QLabel, "value")
        layout.addWidget(rpm_frame, 0, 1)
        
        # Gear display
        gear_frame = self._create_metric_frame("GEAR", "N")
        self.gear_label = gear_frame.findChild(QLabel, "value")
        layout.addWidget(gear_frame, 0, 2)
        
        # Throttle display
        throttle_frame = self._create_metric_frame("THROTTLE", "0%")
        self.throttle_bar = QProgressBar()
        self.throttle_bar.setRange(0, 100)
        self.throttle_bar.setValue(0)
        throttle_frame.layout().addWidget(self.throttle_bar)
        layout.addWidget(throttle_frame, 1, 0)
        
        # Brake display
        brake_frame = self._create_metric_frame("BRAKE", "0%")
        self.brake_bar = QProgressBar()
        self.brake_bar.setRange(0, 100)
        self.brake_bar.setValue(0)
        brake_frame.layout().addWidget(self.brake_bar)
        layout.addWidget(brake_frame, 1, 1)
        
        # DRS display
        drs_frame = self._create_metric_frame("DRS", "OFF")
        self.drs_label = drs_frame.findChild(QLabel, "value")
        layout.addWidget(drs_frame, 1, 2)
        
        widget.setLayout(layout)
        return widget

    def _make_session_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Session controls
        controls = QHBoxLayout()
        self.start_button = QPushButton("Start Recording")
        self.stop_button = QPushButton("Stop Recording")
        self.stop_button.setEnabled(False)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addStretch()
        
        layout.addLayout(controls)
        
        # Session info
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #2d2d2d; padding: 10px; border-radius: 4px;")
        info_layout = QVBoxLayout(info_frame)
        
        self.session_status = QLabel("Not Recording")
        self.current_lap = QLabel("Lap: 0")
        self.last_lap = QLabel("Last Lap: --:--:---")
        
        info_layout.addWidget(self.session_status)
        info_layout.addWidget(self.current_lap)
        info_layout.addWidget(self.last_lap)
        
        layout.addWidget(info_frame)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget

    def _make_analysis_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Analysis controls
        controls = QHBoxLayout()
        controls.addWidget(QPushButton("Load Session"))
        controls.addWidget(QPushButton("Export Data"))
        controls.addStretch()
        
        layout.addLayout(controls)
        
        # Analysis content
        content = QFrame()
        content.setStyleSheet("background-color: #2d2d2d; padding: 10px; border-radius: 4px;")
        content_layout = QVBoxLayout(content)
        
        self.best_lap = QLabel("Best Lap: --:--:---")
        self.avg_lap = QLabel("Average Lap: --:--:---")
        
        content_layout.addWidget(self.best_lap)
        content_layout.addWidget(self.avg_lap)
        
        layout.addWidget(content)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget

    def _make_visualization_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Visualization controls
        controls = QHBoxLayout()
        controls.addWidget(QPushButton("3D View"))
        controls.addWidget(QPushButton("2D View"))
        controls.addWidget(QPushButton("Track Map"))
        controls.addStretch()
        
        layout.addLayout(controls)
        
        # Visualization content
        content = QFrame()
        content.setStyleSheet("background-color: #2d2d2d; padding: 10px; border-radius: 4px;")
        content_layout = QVBoxLayout(content)
        
        content_layout.addWidget(QLabel("Visualization Area"))
        content_layout.addStretch()
        
        layout.addWidget(content)
        
        widget.setLayout(layout)
        return widget

    def _create_metric_frame(self, title, value):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 4px;
                padding: 10px;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; color: #888888;")
        title_label.setAlignment(Qt.AlignCenter)
        
        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        value_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return frame

    def closeEvent(self, event):
        """Clean up when window is closed"""
        self.telemetry_listener.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 
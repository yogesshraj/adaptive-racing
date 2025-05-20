from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QProgressBar, QPushButton, QMessageBox, QFileDialog,
                               QTextEdit, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout)
from PyQt6.QtCore import Qt, QTimer, QCoreApplication
import sys
import csv
import json # For JSON summary
from datetime import datetime
import os # For path manipulation
from src.telemetry.listener import F1TelemetryListener, TelemetryData, CompletedLap # Import new classes

# Helper to format MS to MM:SS.mmm
def format_time_ms(time_ms):
    if time_ms is None or time_ms == 0 or time_ms == float('inf') or not isinstance(time_ms, (int, float)):
         return "00:00.000"
    if time_ms < 0: time_ms = 0 # Should not happen, but guard
    seconds_total = time_ms / 1000.0
    minutes = int(seconds_total / 60)
    seconds = int(seconds_total % 60)
    milliseconds = int((seconds_total * 1000) % 1000)
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

class TelemetryDisplay(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Adaptive Racing Telemetry (F1 2022)")
        self.setMinimumSize(950, 700) 

        self.telemetry_listener = F1TelemetryListener()
        self.current_session_log_path = None
        self.csv_writer = None
        self.csv_file = None
        self.active_session_laps_for_json = [] # Store completed laps for JSON summary of current session
        self._was_session_active = False 
        self._displayed_lap_numbers_in_table = set() # To prevent duplicate rows in table from different events

        # Main UI Setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.create_live_telemetry_tab()
        self.create_session_analysis_tab()

        # Timer for UI updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui_elements)
        self.timer.start(50)  # Update rate ~20 FPS for UI (listener has its own rate)

        self.telemetry_listener.start()

    def create_live_telemetry_tab(self):
        self.live_tab = QWidget()
        self.tabs.addTab(self.live_tab, "Live Telemetry")
        layout = QVBoxLayout(self.live_tab)

        # Speed display
        self.speed_value = QLabel("0 km/h")
        layout.addWidget(self.create_labeled_widget("Speed:", self.speed_value))

        # RPM display
        self.rpm_bar = QProgressBar()
        self.rpm_bar.setRange(0, 15000) # Increased typical max RPM
        self.rpm_bar.setFormat("%v RPM")
        layout.addWidget(self.create_labeled_widget("RPM:", self.rpm_bar))

        # Throttle display
        self.throttle_bar = QProgressBar()
        self.throttle_bar.setRange(0, 100)
        layout.addWidget(self.create_labeled_widget("Throttle:", self.throttle_bar))

        # Brake display
        self.brake_bar = QProgressBar()
        self.brake_bar.setRange(0, 100)
        layout.addWidget(self.create_labeled_widget("Brake:", self.brake_bar))

        # Steering display
        self.steering_value = QLabel("0.0")
        layout.addWidget(self.create_labeled_widget("Steering:", self.steering_value))

        # Gear display
        self.gear_value = QLabel("N")
        layout.addWidget(self.create_labeled_widget("Gear:", self.gear_value))
        layout.addStretch()

    def create_labeled_widget(self, label_text, widget):
        container = QWidget()
        layout = QHBoxLayout(container)
        label = QLabel(label_text)
        label.setFixedWidth(100) # Adjusted width
        layout.addWidget(label)
        layout.addWidget(widget)
        layout.setContentsMargins(0,0,0,0)
        return container

    def create_session_analysis_tab(self):
        self.analysis_tab = QWidget()
        self.tabs.addTab(self.analysis_tab, "Session Analysis")
        tab_layout = QVBoxLayout(self.analysis_tab)

        # Session Info Section (GridLayout for alignment)
        session_info_group = QWidget()
        session_info_layout = QGridLayout(session_info_group)
        tab_layout.addWidget(session_info_group)

        self.session_status_label = QLabel("Session: Inactive")
        self.track_label = QLabel("N/A")
        self.car_label = QLabel("N/A")
        self.weather_label = QLabel("N/A")
        self.session_type_label = QLabel("N/A")
        self.total_time_label = QLabel("00:00.000")
        
        session_info_layout.addWidget(self.session_status_label, 0, 0, 1, 4)
        session_info_layout.addWidget(QLabel("Track:"), 1, 0); session_info_layout.addWidget(self.track_label, 1, 1)
        session_info_layout.addWidget(QLabel("Car:"), 1, 2); session_info_layout.addWidget(self.car_label, 1, 3)
        session_info_layout.addWidget(QLabel("Weather:"), 2, 0); session_info_layout.addWidget(self.weather_label, 2, 1)
        session_info_layout.addWidget(QLabel("Session Type:"), 2, 2); session_info_layout.addWidget(self.session_type_label, 2, 3)
        session_info_layout.addWidget(QLabel("Total Time:"), 3, 0); session_info_layout.addWidget(self.total_time_label, 3, 1)

        # Current Lap Info Section
        current_lap_group = QWidget()
        current_lap_layout = QGridLayout(current_lap_group)
        tab_layout.addWidget(current_lap_group)

        self.current_lap_num_label = QLabel("0")
        self.current_lap_time_label = QLabel("00:00.000")
        self.current_lap_valid_label = QLabel("Yes")
        self.current_sector_label = QLabel("0")
        self.sector1_time_label = QLabel("00:00.000")
        self.sector2_time_label = QLabel("00:00.000")
        self.sector3_time_label = QLabel("N/A")

        current_lap_layout.addWidget(QLabel("Current Lap:"), 0, 0); current_lap_layout.addWidget(self.current_lap_num_label, 0, 1)
        current_lap_layout.addWidget(QLabel("Lap Valid:"), 0, 2); current_lap_layout.addWidget(self.current_lap_valid_label, 0, 3)
        current_lap_layout.addWidget(QLabel("Lap Time:"), 1, 0); current_lap_layout.addWidget(self.current_lap_time_label, 1, 1)
        current_lap_layout.addWidget(QLabel("Sector:"), 1, 2); current_lap_layout.addWidget(self.current_sector_label, 1, 3)
        current_lap_layout.addWidget(QLabel("S1 Time:"), 2, 0); current_lap_layout.addWidget(self.sector1_time_label, 2, 1)
        current_lap_layout.addWidget(QLabel("S2 Time:"), 2, 2); current_lap_layout.addWidget(self.sector2_time_label, 2, 3)
        current_lap_layout.addWidget(QLabel("S3 Time:"), 3, 0); current_lap_layout.addWidget(self.sector3_time_label, 3, 1)
        
        # Completed Laps Table
        self.completed_laps_table = QTableWidget()
        self.completed_laps_table.setColumnCount(6)
        self.completed_laps_table.setHorizontalHeaderLabels(["Lap", "Lap Time", "S1", "S2", "S3", "Valid"]) 
        self.completed_laps_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.completed_laps_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tab_layout.addWidget(self.completed_laps_table)

    def update_ui_elements(self):
        data = self.telemetry_listener.get_current_telemetry()
        is_session_now_active = data.session_active

        if is_session_now_active and not self._was_session_active:
            self.start_session_logging_and_ui_reset(data)
        elif not is_session_now_active and self._was_session_active:
            self.end_session_logging(data)
        
        self._was_session_active = is_session_now_active

        # Update Live Telemetry Tab
        self.speed_value.setText(f"{data.speed:.0f} km/h")
        self.rpm_bar.setValue(int(data.engine_rpm))
        self.throttle_bar.setValue(int(data.throttle * 100))
        self.brake_bar.setValue(int(data.brake * 100))
        self.steering_value.setText(f"{data.steering:.2f}")
        gear_map = {-1: "R", 0: "N"}
        self.gear_value.setText(gear_map.get(data.gear, str(data.gear)))

        # Update Session Analysis Tab - Session Info
        self.session_status_label.setText(f"Session: {'Active' if data.session_active else 'Inactive'}")
        self.track_label.setText(f"{data.track_name}")
        self.car_label.setText(f"{data.car_name}")
        self.weather_label.setText(f"{data.weather_str}")
        self.session_type_label.setText(f"{data.session_type_str}")
        self.total_time_label.setText(f"{format_time_ms(data.session_time_elapsed * 1000)}")

        # Update Session Analysis Tab - Current Lap Info
        self.current_lap_num_label.setText(f"{data.current_lap_num}")
        self.current_lap_time_label.setText(f"{format_time_ms(data.current_lap_time_sec * 1000)}")
        self.current_lap_valid_label.setText(f"{'No' if data.current_lap_invalid else 'Yes'}")
        self.current_sector_label.setText(f"{data.current_sector}")
        self.sector1_time_label.setText(f"{format_time_ms(data.current_sector1_time_ms)}")
        self.sector2_time_label.setText(f"{format_time_ms(data.current_sector2_time_ms)}")
        self.sector3_time_label.setText("N/A")

        # Process newly completed lap from EVENT packet (for immediate CSV and potentially quick table add)
        if data.newly_completed_lap_event:
            event_lap = data.newly_completed_lap_event
            if event_lap.lap_number not in self._displayed_lap_numbers_in_table:
                self.add_lap_to_table(event_lap, from_event=True)
                self._displayed_lap_numbers_in_table.add(event_lap.lap_number)
                if self.csv_writer and data.session_active: # Log to CSV
                    try:
                        self.csv_writer.writerow([
                            event_lap.lap_number, 
                            event_lap.lap_time_ms / 1000.0 if event_lap.lap_time_ms else 0,
                            event_lap.sector1_time_ms / 1000.0 if event_lap.sector1_time_ms else 0,
                            event_lap.sector2_time_ms / 1000.0 if event_lap.sector2_time_ms else 0,
                            event_lap.sector3_time_ms / 1000.0 if event_lap.sector3_time_ms else 0, # S3 calculated in listener for event
                            'Valid' if event_lap.is_valid else 'Invalid'
                        ])
                        if self.csv_file: self.csv_file.flush()
                    except Exception as e: print(f"Error writing event lap to CSV: {e}")
                # Add to JSON list if it's not already there from history (history is preferred)
                if not any(l.lap_number == event_lap.lap_number for l in self.active_session_laps_for_json):
                    self.active_session_laps_for_json.append(event_lap)
        
        # Refresh table from completed_laps_history (source of truth)
        # This ensures table is accurate even if LAFN event is missed or history arrives later.
        for hist_lap in data.completed_laps_history:
            if hist_lap.lap_number not in self._displayed_lap_numbers_in_table:
                self.add_lap_to_table(hist_lap, from_event=False)
                self._displayed_lap_numbers_in_table.add(hist_lap.lap_number)
                # If CSV writer is active and this lap wasn't logged by event, log it now.
                # This is a bit complex to de-duplicate from event logging perfectly without more state.
                # For now, SessionHistory processing in listener tries to be the main source for completed_laps_history.
                # The CSV primarily logs from the LAFN event for immediacy.
            # Update existing row if history has more accurate data (e.g. S3 or definitive validity)
            else: 
                self.update_lap_in_table(hist_lap)

            # Ensure JSON data reflects the most accurate history data
            existing_json_lap_idx = next((idx for idx, l_json in enumerate(self.active_session_laps_for_json) if l_json.lap_number == hist_lap.lap_number), -1)
            if existing_json_lap_idx != -1:
                self.active_session_laps_for_json[existing_json_lap_idx] = hist_lap # Replace with more accurate history version
            elif not any(l.lap_number == hist_lap.lap_number for l in self.active_session_laps_for_json):
                 self.active_session_laps_for_json.append(hist_lap) # Add if missing
        self.active_session_laps_for_json.sort(key=lambda x: x.lap_number) # Keep sorted

    def add_lap_to_table(self, lap: CompletedLap, from_event: bool = False):
        # Check again if lap number is already displayed to be absolutely sure
        if lap.lap_number in self._displayed_lap_numbers_in_table and not from_event:
             # If it's from history and already shown (likely by an event), update it instead
             self.update_lap_in_table(lap)
             return
        if lap.lap_number in self._displayed_lap_numbers_in_table and from_event:
            return # Already shown by a previous event or history

        row_position = self.completed_laps_table.rowCount()
        self.completed_laps_table.insertRow(row_position)
        self.completed_laps_table.setItem(row_position, 0, QTableWidgetItem(str(lap.lap_number)))
        self.completed_laps_table.setItem(row_position, 1, QTableWidgetItem(format_time_ms(lap.lap_time_ms)))
        self.completed_laps_table.setItem(row_position, 2, QTableWidgetItem(format_time_ms(lap.sector1_time_ms)))
        self.completed_laps_table.setItem(row_position, 3, QTableWidgetItem(format_time_ms(lap.sector2_time_ms)))
        self.completed_laps_table.setItem(row_position, 4, QTableWidgetItem(format_time_ms(lap.sector3_time_ms)))
        self.completed_laps_table.setItem(row_position, 5, QTableWidgetItem("Yes" if lap.is_valid else "No"))
        self.completed_laps_table.scrollToBottom()
        self._displayed_lap_numbers_in_table.add(lap.lap_number)
    
    def update_lap_in_table(self, lap: CompletedLap):
        for row in range(self.completed_laps_table.rowCount()):
            if self.completed_laps_table.item(row, 0).text() == str(lap.lap_number):
                self.completed_laps_table.setItem(row, 1, QTableWidgetItem(format_time_ms(lap.lap_time_ms)))
                self.completed_laps_table.setItem(row, 2, QTableWidgetItem(format_time_ms(lap.sector1_time_ms)))
                self.completed_laps_table.setItem(row, 3, QTableWidgetItem(format_time_ms(lap.sector2_time_ms)))
                self.completed_laps_table.setItem(row, 4, QTableWidgetItem(format_time_ms(lap.sector3_time_ms)))
                self.completed_laps_table.setItem(row, 5, QTableWidgetItem("Yes" if lap.is_valid else "No"))
                return

    def start_session_logging_and_ui_reset(self, data: TelemetryData):
        print("GUI: Session started, initiating logging and UI reset.")
        self.completed_laps_table.setRowCount(0) 
        self.active_session_laps_for_json.clear()
        self._displayed_lap_numbers_in_table.clear()
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        track_name_safe = data.track_name.replace(" ", "_").replace("(", "").replace(")", "") if data.track_name != "N/A" else "UnknownTrack"
        log_dir = "telemetry_logs"
        try:
            os.makedirs(log_dir, exist_ok=True)
            self.current_session_log_path = os.path.join(log_dir, f"session_{track_name_safe}_{timestamp_str}.csv")
            self.csv_file = open(self.current_session_log_path, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(["Lap", "LapTimeSec", "S1Sec", "S2Sec", "S3Sec", "Validity"])
            print(f"Logging session to: {self.current_session_log_path}")
        except Exception as e:
            print(f"Error starting CSV logging: {e}")
            if self.csv_file: self.csv_file.close()
            self.csv_file = None; self.csv_writer = None; self.current_session_log_path = None

    def end_session_logging(self, data: TelemetryData):
        print("GUI: Session ended, finalizing logs.")
        if self.csv_file:
            try: self.csv_file.close()
            except Exception as e: print(f"Error closing CSV file: {e}")
            self.csv_file = None; self.csv_writer = None

        if self.active_session_laps_for_json and self.current_session_log_path:
            best_lap_time_ms = float('inf'); best_s1_ms = float('inf'); best_s2_ms = float('inf'); best_s3_ms = float('inf')
            for lap_obj in self.active_session_laps_for_json:
                if lap_obj.is_valid:
                    if lap_obj.lap_time_ms > 0 and lap_obj.lap_time_ms < best_lap_time_ms: best_lap_time_ms = lap_obj.lap_time_ms
                    if lap_obj.sector1_time_ms > 0 and lap_obj.sector1_time_ms < best_s1_ms: best_s1_ms = lap_obj.sector1_time_ms
                    if lap_obj.sector2_time_ms > 0 and lap_obj.sector2_time_ms < best_s2_ms: best_s2_ms = lap_obj.sector2_time_ms
                    if lap_obj.sector3_time_ms > 0 and lap_obj.sector3_time_ms < best_s3_ms: best_s3_ms = lap_obj.sector3_time_ms
            summary_data = {
                "track_name": data.track_name, "car_name": data.car_name, "weather": data.weather_str,
                "session_type": data.session_type_str,
                "best_lap_time": format_time_ms(best_lap_time_ms),
                "best_sector1_time": format_time_ms(best_s1_ms),
                "best_sector2_time": format_time_ms(best_s2_ms),
                "best_sector3_time": format_time_ms(best_s3_ms),
                "total_laps_recorded": len(self.active_session_laps_for_json)
            }
            json_path = self.current_session_log_path.replace(".csv", "_summary.json")
            try:
                with open(json_path, 'w') as f_json: json.dump(summary_data, f_json, indent=4)
                print(f"JSON summary saved: {json_path}")
            except Exception as e: print(f"Error saving JSON summary: {e}")
        self.current_session_log_path = None
        self.active_session_laps_for_json.clear()
        self._was_session_active = False
        self._displayed_lap_numbers_in_table.clear() # Clear for next potential session in same app run

    def closeEvent(self, event):
        current_data = self.telemetry_listener.get_current_telemetry() 
        if self._was_session_active : # If session was active when closing, try to finalize
             self.end_session_logging(current_data)
        self.telemetry_listener.stop()
        event.accept()

if __name__ == "__main__":
    QCoreApplication.setApplicationName("Adaptive Racing Telemetry")
    QCoreApplication.setOrganizationName("AdaptiveRacing")
    app = QApplication(sys.argv)
    window = TelemetryDisplay()
    window.show()
    sys.exit(app.exec()) 
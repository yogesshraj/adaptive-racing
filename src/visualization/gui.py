import tkinter as tk
from tkinter import ttk
import time
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass
from config.default_config import GUI_UPDATE_INTERVAL
from datetime import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, QThread, QTimer
import sys
from src.visualization.plots import TelemetryVisualizer

# Initialize Qt Application
qt_app = QApplication.instance()
if not qt_app:
    qt_app = QApplication(sys.argv)

@dataclass
class TelemetryData:
    """Class to store current telemetry data"""
    speed: int = 0
    rpm: int = 0
    gear: int = 0
    throttle: float = 0.0
    brake: float = 0.0
    steer: float = 0.0
    lap_time: int = 0  # in milliseconds
    drs: int = 0
    sector1_time: int = 0  # in milliseconds
    sector2_time: int = 0  # in milliseconds
    sector3_time: int = 0  # in milliseconds
    current_sector: int = 0  # 0-based sector number (0, 1, 2)
    lap_distance: float = 0.0  # Distance around current lap in meters
    tyresSurfaceTemperature: List[int] = None  # Surface temperature of each tire [FL, FR, RL, RR]
    
    def __post_init__(self):
        if self.tyresSurfaceTemperature is None:
            self.tyresSurfaceTemperature = [0, 0, 0, 0]

class TelemetryGUI:
    def __init__(self):
        # Ensure we're in the main thread
        if QThread.currentThread() != QApplication.instance().thread():
            raise RuntimeError("GUI must be created in the main thread")
            
        self.root = tk.Tk()
        self.root.title("F1 22 Telemetry")
        self.root.geometry("1200x800")  # Increased window size for better visualization
        
        # Current telemetry data
        self.telemetry = TelemetryData()
        self.pending_telemetry_update = None
        
        # Create Qt timer for visualization updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_visualizations)
        self.update_timer.setInterval(GUI_UPDATE_INTERVAL)
        
        self._setup_gui()
        self._setup_styles()
        
        # Start the update timer
        self.update_timer.start()

    def _update_visualizations(self):
        """Update visualizations using Qt timer"""
        if hasattr(self, 'visualizer') and self.visualization_active:
            if self.pending_telemetry_update:
                self.visualizer.update_telemetry(self.pending_telemetry_update)
                self.pending_telemetry_update = None
            self.visualizer.layout.update()

    def _format_time(self, time_ms: int) -> str:
        """Format milliseconds into MM:SS.mmm"""
        if not time_ms or time_ms <= 0:
            return "--:--:---"
        minutes = time_ms // 60000
        seconds = (time_ms % 60000) // 1000
        milliseconds = time_ms % 1000
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    def _setup_styles(self):
        """Setup ttk styles for widgets"""
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Helvetica", 24))
        style.configure("Header.TLabel", font=("Helvetica", 16))
        style.configure("Data.TLabel", font=("Helvetica", 14))
        style.configure("Small.TLabel", font=("Helvetica", 12))

    def _setup_gui(self):
        """Setup the main GUI elements"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create tabs
        self.live_tab = ttk.Frame(self.notebook)
        self.session_tab = ttk.Frame(self.notebook)
        self.analysis_tab = ttk.Frame(self.notebook)
        self.viz_tab = ttk.Frame(self.notebook)  # New visualizations tab
        
        self.notebook.add(self.live_tab, text="Live Telemetry")
        self.notebook.add(self.session_tab, text="Session Data")
        self.notebook.add(self.analysis_tab, text="Analysis")
        self.notebook.add(self.viz_tab, text="Visualizations")
        
        self._setup_live_tab()
        self._setup_session_tab()
        self._setup_analysis_tab()
        self._setup_visualization_tab()

    def _setup_live_tab(self):
        """Setup the live telemetry display tab"""
        # Create main frame with two columns
        main_frame = ttk.Frame(self.live_tab)
        main_frame.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Left column for car telemetry
        car_frame = ttk.LabelFrame(main_frame, text="Car Telemetry")
        car_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        # Speed display
        speed_frame = ttk.Frame(car_frame)
        speed_frame.pack(fill='x', padx=10, pady=5)
        
        self.speed_label = ttk.Label(speed_frame, text="SPEED", style="Header.TLabel")
        self.speed_label.pack()
        
        self.speed_value = ttk.Label(speed_frame, text="0 km/h", style="Title.TLabel")
        self.speed_value.pack()
        
        # RPM and Gear
        engine_frame = ttk.Frame(car_frame)
        engine_frame.pack(fill='x', padx=10, pady=5)
        
        self.rpm_label = ttk.Label(engine_frame, text="RPM", style="Header.TLabel")
        self.rpm_label.pack(side='left', padx=20)
        
        self.rpm_value = ttk.Label(engine_frame, text="0", style="Data.TLabel")
        self.rpm_value.pack(side='left', padx=20)
        
        self.gear_label = ttk.Label(engine_frame, text="GEAR", style="Header.TLabel")
        self.gear_label.pack(side='left', padx=20)
        
        self.gear_value = ttk.Label(engine_frame, text="N", style="Data.TLabel")
        self.gear_value.pack(side='left', padx=20)
        
        # Pedals
        pedals_frame = ttk.Frame(car_frame)
        pedals_frame.pack(fill='x', padx=10, pady=5)
        
        # Throttle
        self.throttle_label = ttk.Label(pedals_frame, text="THROTTLE", style="Header.TLabel")
        self.throttle_label.pack()
        
        self.throttle_bar = ttk.Progressbar(pedals_frame, length=200, mode='determinate')
        self.throttle_bar.pack(pady=5)
        
        # Brake
        self.brake_label = ttk.Label(pedals_frame, text="BRAKE", style="Header.TLabel")
        self.brake_label.pack()
        
        self.brake_bar = ttk.Progressbar(pedals_frame, length=200, mode='determinate')
        self.brake_bar.pack(pady=5)
        
        # Right column for timing information
        timing_frame = ttk.LabelFrame(main_frame, text="Timing Information")
        timing_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        # Current Lap Time
        self.current_lap_time_label = ttk.Label(timing_frame, text="CURRENT LAP", style="Header.TLabel")
        self.current_lap_time_label.pack(pady=5)
        self.current_lap_time_value = ttk.Label(timing_frame, text="00:00.000", style="Title.TLabel")
        self.current_lap_time_value.pack(pady=5)
        
        # Sector Times
        sectors_frame = ttk.Frame(timing_frame)
        sectors_frame.pack(fill='x', pady=10)
        
        # Create sector time displays
        self.sector_frames = []
        self.sector_times = []
        for i in range(3):
            frame = ttk.Frame(sectors_frame)
            frame.pack(fill='x', pady=5)
            
            label = ttk.Label(frame, text=f"Sector {i+1}", style="Header.TLabel")
            label.pack()
            
            time_var = ttk.Label(frame, text="--:--:---", style="Data.TLabel")
            time_var.pack()
            
            self.sector_frames.append(frame)
            self.sector_times.append(time_var)

    def _setup_session_tab(self):
        """Setup the session data tab"""
        # Session Controls
        controls_frame = ttk.Frame(self.session_tab)
        controls_frame.pack(fill='x', padx=10, pady=5)
        
        self.record_button = ttk.Button(controls_frame, text="Start Recording")
        self.record_button.pack(side='left', padx=5)
        
        self.stop_button = ttk.Button(controls_frame, text="Stop Recording", state='disabled')
        self.stop_button.pack(side='left', padx=5)
        
        # Current Session Info
        session_info_frame = ttk.LabelFrame(self.session_tab, text="Current Session")
        session_info_frame.pack(fill='x', padx=10, pady=5)
        
        self.session_status = ttk.Label(session_info_frame, text="Not Recording", style="Data.TLabel")
        self.session_status.pack(pady=5)
        
        self.current_lap = ttk.Label(session_info_frame, text="Lap: -", style="Data.TLabel")
        self.current_lap.pack(pady=5)
        
        self.current_lap_status = ttk.Label(session_info_frame, text="Current Lap: Valid", style="Data.TLabel")
        self.current_lap_status.pack(pady=5)
        
        self.last_lap_time = ttk.Label(session_info_frame, text="Last Lap: -", style="Data.TLabel")
        self.last_lap_time.pack(pady=5)
        
        # Lap Times List
        laptimes_frame = ttk.LabelFrame(self.session_tab, text="Lap Times")
        laptimes_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.laptimes_tree = ttk.Treeview(laptimes_frame, columns=('lap', 'time', 'valid'),
                                         show='headings', height=10)
        self.laptimes_tree.heading('lap', text='Lap')
        self.laptimes_tree.heading('time', text='Time')
        self.laptimes_tree.heading('valid', text='Valid')
        
        scrollbar = ttk.Scrollbar(laptimes_frame, orient='vertical', 
                                command=self.laptimes_tree.yview)
        self.laptimes_tree.configure(yscrollcommand=scrollbar.set)
        
        self.laptimes_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def _setup_analysis_tab(self):
        """Setup the analysis tab"""
        # Session Summary
        summary_frame = ttk.LabelFrame(self.analysis_tab, text="Session Summary")
        summary_frame.pack(fill='x', padx=10, pady=5)
        
        self.best_lap_label = ttk.Label(summary_frame, text="Best Lap: -", style="Data.TLabel")
        self.best_lap_label.pack(pady=2)
        
        self.consistency_label = ttk.Label(summary_frame, text="Consistency: -", style="Data.TLabel")
        self.consistency_label.pack(pady=2)
        
        # Best Sector Times
        sectors_frame = ttk.LabelFrame(self.analysis_tab, text="Best Sectors")
        sectors_frame.pack(fill='x', padx=10, pady=5)
        
        self.sector_labels = []
        for i in range(3):
            label = ttk.Label(sectors_frame, 
                            text=f"Sector {i+1}: -", 
                            style="Data.TLabel")
            label.pack(pady=2)
            self.sector_labels.append(label)
        
        # Lap Comparison
        comparison_frame = ttk.LabelFrame(self.analysis_tab, text="Lap Comparison")
        comparison_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.comparison_tree = ttk.Treeview(comparison_frame, 
                                          columns=('lap', 'time', 'delta', 's1', 's2', 's3'),
                                          show='headings', 
                                          height=10)
        
        self.comparison_tree.heading('lap', text='Lap')
        self.comparison_tree.heading('time', text='Time')
        self.comparison_tree.heading('delta', text='Delta')
        self.comparison_tree.heading('s1', text='S1')
        self.comparison_tree.heading('s2', text='S2')
        self.comparison_tree.heading('s3', text='S3')
        
        scrollbar = ttk.Scrollbar(comparison_frame, orient='vertical',
                                command=self.comparison_tree.yview)
        self.comparison_tree.configure(yscrollcommand=scrollbar.set)
        
        self.comparison_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def _setup_visualization_tab(self):
        """Setup the visualizations tab with proper Qt integration"""
        # Create main frame for visualizations
        main_frame = ttk.Frame(self.viz_tab)
        main_frame.pack(fill='both', expand=True)
        
        # Create Qt widget container in the main thread
        self.viz_container = QWidget()
        self.viz_container.setMinimumSize(800, 600)
        
        # Create layout for Qt widget
        layout = QVBoxLayout(self.viz_container)
        
        # Create visualizer
        self.visualizer = TelemetryVisualizer(self.viz_container)
        
        # Add visualizer's layout widget to container's layout
        layout.addWidget(self.visualizer.layout)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a Tkinter window ID for embedding
        viz_window = tk.Frame(main_frame)
        viz_window.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Embed Qt widget into Tkinter
        self.viz_container.show()
        self.viz_container.winId()
        
        # Add control buttons
        controls_frame = ttk.Frame(self.viz_tab)
        controls_frame.pack(fill='x', padx=5, pady=5)
        
        self.pause_button = ttk.Button(controls_frame, text="Pause", command=self._toggle_visualization)
        self.pause_button.pack(side='left', padx=5)
        
        self.clear_button = ttk.Button(controls_frame, text="Clear", command=self.visualizer.clear_history)
        self.clear_button.pack(side='left', padx=5)
        
        self.visualization_active = True

    def _toggle_visualization(self):
        """Toggle visualization updates"""
        self.visualization_active = not self.visualization_active
        self.pause_button.config(text="Resume" if not self.visualization_active else "Pause")

    def update_telemetry(self, telemetry: TelemetryData):
        """Update the live telemetry display"""
        self.telemetry = telemetry
        
        # Update speed
        self.speed_value.config(text=f"{telemetry.speed} km/h")
        
        # Update RPM
        self.rpm_value.config(text=str(telemetry.rpm))
        
        # Update gear
        gear_text = "N" if telemetry.gear == 0 else "R" if telemetry.gear == -1 else str(telemetry.gear)
        self.gear_value.config(text=gear_text)
        
        # Update throttle and brake
        self.throttle_bar['value'] = telemetry.throttle * 100
        self.brake_bar['value'] = telemetry.brake * 100
        
        # Update current lap time
        self.current_lap_time_value.config(text=self._format_time(telemetry.lap_time))
        
        # Update sector times
        if telemetry.sector1_time > 0:
            self.sector_times[0].config(text=self._format_time(telemetry.sector1_time))
        if telemetry.sector2_time > 0:
            self.sector_times[1].config(text=self._format_time(telemetry.sector2_time))
        if telemetry.sector3_time > 0:
            self.sector_times[2].config(text=self._format_time(telemetry.sector3_time))
        
        # Highlight current sector
        for i in range(3):
            if i == telemetry.current_sector:
                self.sector_frames[i].configure(style='Active.TFrame')
            else:
                self.sector_frames[i].configure(style='TFrame')
        
        # Update visualizations if active
        if self.visualization_active:
            # Convert telemetry data to dict for visualizer
            self.pending_telemetry_update = {
                'speed': telemetry.speed,
                'throttle': telemetry.throttle,
                'brake': telemetry.brake,
                'steer': telemetry.steer,
                'rpm': telemetry.rpm,
                'gear': telemetry.gear,
                'lap_distance': getattr(telemetry, 'lap_distance', 0),
                'tyresSurfaceTemperature': getattr(telemetry, 'tyresSurfaceTemperature', [0, 0, 0, 0])
            }

    def update_session_info(self, lap_number: int, last_lap_time: int, is_recording: bool, is_current_lap_valid: bool = True):
        """Update the session information display"""
        status_text = "Recording" if is_recording else "Not Recording"
        self.session_status.config(text=status_text)
        self.current_lap.config(text=f"Lap: {lap_number}")
        
        # Update current lap validity status with color
        self.current_lap_status.config(
            text=f"Current Lap: {'Valid' if is_current_lap_valid else 'Invalid'}",
            foreground='green' if is_current_lap_valid else 'red'
        )
        
        if last_lap_time > 0:
            minutes = last_lap_time // 60000
            seconds = (last_lap_time % 60000) // 1000
            milliseconds = last_lap_time % 1000
            time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            self.last_lap_time.config(text=f"Last Lap: {time_str}")

    def add_lap_time(self, lap_number: int, lap_time: int, is_valid: bool):
        """Add a lap time to the lap times list"""
        minutes = lap_time // 60000
        seconds = (lap_time % 60000) // 1000
        milliseconds = lap_time % 1000
        time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        valid_str = "Valid" if is_valid else "Invalid"
        
        item = self.laptimes_tree.insert('', 'end', values=(lap_number, time_str, valid_str))
        
        # Set the row color based on validity
        if not is_valid:
            self.laptimes_tree.tag_configure('invalid', foreground='red')
            self.laptimes_tree.item(item, tags=('invalid',))

    def update_analysis(self, session_summary: Dict):
        """Update the analysis tab with session summary data"""
        # Update best lap
        best_time = session_summary.get('best_lap_time')
        if best_time:
            time_str = self._format_time(best_time)
            self.best_lap_label.config(text=f"Best Lap: {time_str} (Lap {session_summary['best_lap_number']})")
        else:
            self.best_lap_label.config(text="Best Lap: No valid laps")
        
        # Update consistency
        consistency_ms = session_summary.get('lap_time_consistency', 0)
        if consistency_ms > 0:
            self.consistency_label.config(text=f"Consistency: ±{consistency_ms/1000:.3f}s")
        else:
            self.consistency_label.config(text="Consistency: Not enough valid laps")
        
        # Update best sectors
        best_sectors = session_summary.get('best_sectors', [])
        if best_sectors and len(best_sectors) == 3:
            for idx, sector_data in enumerate(best_sectors):
                if sector_data and isinstance(sector_data, tuple) and len(sector_data) == 2:
                    time, lap = sector_data
                    if time > 0:
                        time_str = self._format_time(time)
                        self.sector_labels[idx].config(text=f"Sector {idx+1}: {time_str} (Lap {lap})")
                    else:
                        self.sector_labels[idx].config(text=f"Sector {idx+1}: No valid time")
                else:
                    self.sector_labels[idx].config(text=f"Sector {idx+1}: No valid time")
        
        # Clear and update comparison tree
        for item in self.comparison_tree.get_children():
            self.comparison_tree.delete(item)
        
        # Add lap times to comparison tree
        lap_times = session_summary.get('lap_times', {})
        sector_times = session_summary.get('sector_times', {})
        lap_valid = session_summary.get('lap_valid', {})
        
        best_time = session_summary.get('best_lap_time', 0)
        
        for lap_num_str in sorted(lap_times.keys(), key=int):
            lap_time = lap_times[lap_num_str]
            sectors = sector_times.get(lap_num_str, [0, 0, 0])
            is_valid = lap_valid.get(lap_num_str, False)
            
            # Calculate delta to best lap
            if best_time and best_time > 0 and lap_time > 0:
                delta = lap_time - best_time
                delta_str = f"{'+' if delta > 0 else ''}{delta/1000:.3f}"
            else:
                delta_str = "-"
            
            values = (
                lap_num_str,
                self._format_time(lap_time),
                delta_str,
                self._format_time(sectors[0]) if len(sectors) > 0 else "--:--:---",
                self._format_time(sectors[1]) if len(sectors) > 1 else "--:--:---",
                self._format_time(sectors[2]) if len(sectors) > 2 else "--:--:---"
            )
            
            item = self.comparison_tree.insert('', 'end', values=values)
            
            # Color coding
            if not is_valid:
                self.comparison_tree.tag_configure('invalid', foreground='red')
                self.comparison_tree.item(item, tags=('invalid',))
            elif best_time and lap_time == best_time:
                self.comparison_tree.tag_configure('best', foreground='green')
                self.comparison_tree.item(item, tags=('best',))

    def set_record_callback(self, callback):
        """Set the callback for the record button"""
        self.record_button.config(command=callback)

    def set_stop_callback(self, callback):
        """Set the callback for the stop button"""
        self.stop_button.config(command=callback)

    def toggle_recording_state(self, is_recording: bool):
        """Toggle the state of recording buttons"""
        if is_recording:
            self.record_button.config(state='disabled')
            self.stop_button.config(state='normal')
        else:
            self.record_button.config(state='normal')
            self.stop_button.config(state='disabled')

    def run(self):
        """Start the GUI main loop"""
        # Process Qt events in the main thread
        def process_qt_events():
            qt_app.processEvents()
            self.root.after(10, process_qt_events)
        
        # Start processing Qt events
        self.root.after(10, process_qt_events)
        
        # Start Tkinter main loop
        self.root.mainloop() 
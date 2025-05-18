import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import asdict

from gui import TelemetryData

class DataLogger:
    def __init__(self, base_path: str = "telemetry_logs"):
        """Initialize the data logger"""
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        
        self.current_session: Optional[Path] = None
        self.is_recording = False
        self.current_lap_data: List[Dict] = []
        self.completed_laps: List[List[Dict]] = []
        self.session_info = {
            "start_time": None,
            "track_name": None,
            "total_laps": 0,
            "best_lap_time": None,
            "best_lap_number": None,
            "best_sectors": [(0, 0), (0, 0), (0, 0)],  # (time, lap_number) for each sector
            "lap_times": {},
            "sector_times": {},
            "lap_valid": {}
        }

    def start_session(self, track_name: str = "Unknown"):
        """Start a new recording session"""
        if self.is_recording:
            return

        # Create new session directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.base_path / f"session_{timestamp}"
        session_dir.mkdir(exist_ok=True)
        
        self.current_session = session_dir
        self.is_recording = True
        self.current_lap_data = []
        self.completed_laps = []
        
        # Initialize session info
        self.session_info = {
            "start_time": timestamp,
            "track_name": track_name,
            "total_laps": 0,
            "best_lap_time": None,
            "best_lap_number": None,
            "best_sectors": [(0, 0), (0, 0), (0, 0)],  # (time, lap_number) for each sector
            "lap_times": {},
            "sector_times": {},
            "lap_valid": {}
        }
        
        # Save initial session info
        self._save_session_info()

    def stop_session(self):
        """Stop the current recording session"""
        if not self.is_recording:
            return

        # Save any remaining lap data
        if self.current_lap_data:
            self._save_lap_data(len(self.completed_laps) + 1)

        # Update and save final session info
        self._save_session_info()
        
        self.is_recording = False
        self.current_session = None
        self.current_lap_data = []
        self.completed_laps = []

    def record_telemetry(self, telemetry: TelemetryData, lap_data: Dict):
        """Record a telemetry data point"""
        if not self.is_recording:
            return

        current_lap_number = lap_data.get("lap_number", 0)
        
        # Create telemetry record
        record = {
            "timestamp": datetime.now().isoformat(),
            **asdict(telemetry),
            "sector": lap_data.get("sector", 0),
            "lap_distance": lap_data.get("lap_distance", 0),
            "current_lap_invalid": lap_data.get("current_lap_invalid", False),
            "lap_number": current_lap_number,
            "lap_time": telemetry.lap_time
        }
        
        # Check if this is a new lap
        if len(self.current_lap_data) > 0:
            last_record_lap = self.current_lap_data[-1]["lap_number"]
            if current_lap_number != last_record_lap:
                # Save the completed lap
                self._save_lap_data(last_record_lap)
                self.current_lap_data = []  # Start new lap data
        
        self.current_lap_data.append(record)
        
        # Check if lap is completed via last lap time
        if self._is_lap_completed(lap_data):
            last_lap_number = current_lap_number - 1 if current_lap_number > 0 else current_lap_number
            if last_lap_number > 0:
                self._save_lap_data(last_lap_number)
                self._update_session_stats(last_lap_number, lap_data)
                self.current_lap_data = [record]  # Keep only the current record for the new lap

    def _is_lap_completed(self, lap_data: Dict) -> bool:
        """Check if the current lap is completed"""
        # Check if we have a valid last lap time
        return lap_data.get("last_lap_time_ms", 0) > 0

    def _save_lap_data(self, lap_number: int):
        """Save the current lap data to a CSV file"""
        if not self.current_session or not self.current_lap_data:
            return

        # Save to CSV
        csv_path = self.current_session / f"lap_{lap_number:02d}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            if self.current_lap_data:
                writer = csv.DictWriter(f, fieldnames=self.current_lap_data[0].keys())
                writer.writeheader()
                writer.writerows(self.current_lap_data)

        # Only append to completed laps if it's not already there
        if len(self.completed_laps) < lap_number:
            self.completed_laps.append(self.current_lap_data)

    def _update_session_stats(self, lap_number: int, lap_data: Dict):
        """Update session statistics with completed lap data"""
        lap_time = lap_data.get("last_lap_time_ms", 0)
        
        # Update best lap time if this is faster
        if (not lap_data.get("current_lap_invalid", False) and 
            lap_time > 0 and  # Only consider positive lap times
            (self.session_info["best_lap_time"] is None or 
             lap_time < self.session_info["best_lap_time"])):
            self.session_info["best_lap_time"] = lap_time
            self.session_info["best_lap_number"] = lap_number

        # Update sector times
        for sector in range(3):
            sector_time = lap_data.get(f"sector{sector + 1}_time_ms", 0)
            if (sector_time > 0 and  # Only consider positive sector times
                not lap_data.get("current_lap_invalid", False)):  # Only update if lap is valid
                current_best = self.session_info["best_sectors"][sector][0]
                if current_best == 0 or sector_time < current_best:
                    self.session_info["best_sectors"][sector] = (sector_time, lap_number)

        self.session_info["total_laps"] = lap_number
        self._save_session_info()

    def _save_session_info(self):
        """Save session information to a JSON file"""
        if not self.current_session:
            return

        with open(self.current_session / "session_info.json", 'w') as f:
            json.dump(self.session_info, f, indent=2)

    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        return self.session_info.copy()

    def get_lap_times(self) -> List[int]:
        """Get list of lap times for completed laps"""
        return [lap[-1].get("lap_time", 0) for lap in self.completed_laps]

    def update_session_info(self, updates: Dict):
        """Update session information with nested key support"""
        if not self.is_recording:
            return

        def update_nested(data: Dict, key: str, value):
            """Update nested dictionary using dot notation keys"""
            parts = key.split('.')
            d = data
            for part in parts[:-1]:
                if part not in d:
                    d[part] = {}
                d = d[part]
            d[parts[-1]] = value
            
            # Update best lap time if applicable
            if 'lap_times' in data and data['lap_times']:
                valid_times = {lap: time for lap, time in data['lap_times'].items() 
                             if data.get('lap_valid', {}).get(str(lap), True)}
                if valid_times:
                    best_time = min(valid_times.values())
                    best_lap = min([lap for lap, time in valid_times.items() 
                                  if time == best_time])
                    data['best_lap_time'] = best_time
                    data['best_lap_number'] = int(best_lap)

            # Update best sectors if applicable
            if 'sector_times' in data:
                best_sectors = [(0, 0), (0, 0), (0, 0)]
                for lap, sectors in data['sector_times'].items():
                    if not data.get('lap_valid', {}).get(str(lap), True):
                        continue
                    for i, sector_time in enumerate(sectors):
                        if sector_time > 0:  # Only consider valid sector times
                            if best_sectors[i] == (0, 0) or sector_time < best_sectors[i][0]:
                                best_sectors[i] = (sector_time, int(lap))
                data['best_sectors'] = best_sectors

        for key, value in updates.items():
            update_nested(self.session_info, key, value)
        
        self._save_session_info()
        print(f"Updated session info: {self.session_info}") 
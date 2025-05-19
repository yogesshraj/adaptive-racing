import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class LapAnalysis:
    lap_number: int
    lap_time: int  # in milliseconds
    sector_times: List[int]
    is_valid: bool
    avg_speed: float
    max_speed: float
    min_speed: float
    throttle_percentage: float  # average throttle application
    brake_percentage: float    # average brake application

class SessionAnalyzer:
    def __init__(self, session_path: Path):
        """Initialize the session analyzer with a path to a session directory"""
        self.session_path = Path(session_path)
        self.session_info = self._load_session_info()
        self.lap_analyses: List[LapAnalysis] = []
        self._analyze_session()

    def _load_session_info(self) -> Dict:
        """Load session information from session_info.json"""
        try:
            session_info_path = self.session_path / "session_info.json"
            if not session_info_path.exists():
                return {
                    "lap_times": {},
                    "sector_times": {},
                    "lap_valid": {},
                    "best_sectors": [(0, 0), (0, 0), (0, 0)],
                    "total_laps": 0
                }
            
            with open(session_info_path, 'r') as f:
                data = json.load(f)
                # Ensure all required fields exist
                if "lap_times" not in data:
                    data["lap_times"] = {}
                if "sector_times" not in data:
                    data["sector_times"] = {}
                if "lap_valid" not in data:
                    data["lap_valid"] = {}
                if "best_sectors" not in data:
                    data["best_sectors"] = [(0, 0), (0, 0), (0, 0)]
                return data
                
        except json.JSONDecodeError as e:
            return {
                "lap_times": {},
                "sector_times": {},
                "lap_valid": {},
                "best_sectors": [(0, 0), (0, 0), (0, 0)],
                "total_laps": 0
            }

    def _analyze_session(self):
        """Analyze all laps in the session"""
        # Find all lap CSV files
        lap_files = sorted(self.session_path.glob("lap_*.csv"))
        
        for lap_file in lap_files:
            try:
                lap_number = int(lap_file.stem.split('_')[1])
                analysis = self._analyze_lap(lap_file, lap_number)
                self.lap_analyses.append(analysis)
            except Exception as e:
                print(f"Error analyzing lap {lap_file}: {e}")

    def _analyze_lap(self, lap_file: Path, lap_number: int) -> LapAnalysis:
        """Analyze a single lap's data"""
        speeds = []
        throttle_values = []
        brake_values = []
        sector_times = [0, 0, 0]
        is_valid = True
        lap_time = 0
        
        # Get lap info from session_info if available
        lap_times = self.session_info.get('lap_times', {})
        sector_times_dict = self.session_info.get('sector_times', {})
        lap_valid_dict = self.session_info.get('lap_valid', {})
        
        # Get lap-specific data if available
        str_lap_num = str(lap_number)
        if str_lap_num in lap_times:
            lap_time = lap_times[str_lap_num]
            is_valid = lap_valid_dict.get(str_lap_num, True)
            if str_lap_num in sector_times_dict:
                sector_times = sector_times_dict[str_lap_num]
        
        with open(lap_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert string values to appropriate types
                speed = float(row['speed'])
                speeds.append(speed)
                throttle_values.append(float(row['throttle']))
                brake_values.append(float(row['brake']))

        # Calculate lap statistics
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0
        min_speed = min(speeds) if speeds else 0
        avg_throttle = sum(throttle_values) / len(throttle_values) if throttle_values else 0
        avg_brake = sum(brake_values) / len(brake_values) if brake_values else 0

        return LapAnalysis(
            lap_number=lap_number,
            lap_time=lap_time,
            sector_times=sector_times,
            is_valid=is_valid,
            avg_speed=avg_speed,
            max_speed=max_speed,
            min_speed=min_speed,
            throttle_percentage=avg_throttle * 100,
            brake_percentage=avg_brake * 100
        )

    def get_best_lap(self) -> Optional[LapAnalysis]:
        """Get the analysis of the fastest valid lap"""
        valid_laps = [lap for lap in self.lap_analyses if lap.is_valid and lap.lap_time > 0]
        return min(valid_laps, key=lambda x: x.lap_time) if valid_laps else None

    def get_best_sector_times(self) -> List[Tuple[int, int]]:
        """Get the best time for each sector and the lap number it was achieved on"""
        best_sectors = [(0, 0)] * 3  # (time, lap_number) for each sector
        
        for lap in self.lap_analyses:
            if not lap.is_valid:
                continue
            
            for sector_idx, sector_time in enumerate(lap.sector_times):
                if sector_time <= 0:
                    continue
                    
                if best_sectors[sector_idx][0] == 0 or sector_time < best_sectors[sector_idx][0]:
                    best_sectors[sector_idx] = (sector_time, lap.lap_number)
        
        return best_sectors

    def get_lap_time_consistency(self) -> float:
        """Calculate lap time consistency (standard deviation of valid lap times)"""
        import statistics
        
        valid_lap_times = [lap.lap_time for lap in self.lap_analyses 
                          if lap.is_valid and lap.lap_time > 0]
        
        try:
            return statistics.stdev(valid_lap_times)
        except statistics.StatisticsError:
            return 0.0

    def get_session_summary(self) -> Dict:
        """Get a summary of the session analysis"""
        print("\nGenerating session summary...")
        
        # Initialize summary with basic session info
        summary = {
            "total_laps": self.session_info.get("total_laps", 0),
            "valid_laps": 0,
            "best_lap_time": 0,
            "best_lap_number": None,
            "best_sectors": self.session_info.get("best_sectors", [(0, 0), (0, 0), (0, 0)]),
            "session_date": self.session_info.get("start_time"),
            "track_name": self.session_info.get("track_name", "Unknown"),
            "lap_times": {},
            "sector_times": {},
            "lap_valid": {}
        }
        
        # Get lap times and validity
        lap_times = self.session_info.get("lap_times", {})
        lap_valid = self.session_info.get("lap_valid", {})
        sector_times = self.session_info.get("sector_times", {})
        
        # Process each lap
        for lap_num_str, lap_time in lap_times.items():
            if not isinstance(lap_time, (int, float)) or lap_time <= 0:
                continue
                
            lap_num = int(lap_num_str)
            is_valid = lap_valid.get(lap_num_str, False)
            
            # Store lap data
            summary["lap_times"][lap_num_str] = lap_time
            summary["lap_valid"][lap_num_str] = is_valid
            
            # Count valid laps
            if is_valid:
                summary["valid_laps"] += 1
                
                # Update best lap time
                if summary["best_lap_time"] == 0 or lap_time < summary["best_lap_time"]:
                    summary["best_lap_time"] = lap_time
                    summary["best_lap_number"] = lap_num
            
            # Process sector times
            if lap_num_str in sector_times:
                sectors = sector_times[lap_num_str]
                if isinstance(sectors, list) and len(sectors) == 3:
                    summary["sector_times"][lap_num_str] = sectors
                    
                    # Update best sectors if lap is valid
                    if is_valid:
                        for i, sector_time in enumerate(sectors):
                            if isinstance(sector_time, (int, float)) and sector_time > 0:
                                current_best = summary["best_sectors"][i][0]
                                if current_best == 0 or sector_time < current_best:
                                    summary["best_sectors"][i] = (sector_time, lap_num)
        
        # Calculate lap time consistency
        valid_times = [time for lap, time in lap_times.items() 
                      if lap_valid.get(lap, False) and isinstance(time, (int, float)) and time > 0]
        if len(valid_times) > 1:
            try:
                from statistics import stdev
                summary["lap_time_consistency"] = stdev(valid_times)
            except:
                summary["lap_time_consistency"] = 0.0
        else:
            summary["lap_time_consistency"] = 0.0
        
        print(f"Summary generated: {summary}")
        return summary 
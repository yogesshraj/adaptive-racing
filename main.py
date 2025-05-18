import signal
import sys
from typing import Optional
from pathlib import Path
from data_models import PACKET_IDS, PacketCarTelemetryData, PacketLapData, PacketSessionData, TRACK_IDS
from telemetry_listener import TelemetryListener
from gui import TelemetryGUI, TelemetryData
from data_logger import DataLogger
from lap_analyzer import SessionAnalyzer
from config import GUI_UPDATE_INTERVAL

class F1TelemetryApp:
    def __init__(self):
        self.gui = TelemetryGUI()
        self.listener = TelemetryListener()
        self.data_logger = DataLogger()
        self.current_telemetry = TelemetryData()
        self.player_car_index: Optional[int] = None
        self.current_lap_number = 0
        self.last_lap_time = 0
        self.current_lap_invalid = False  # Track current lap validity
        self.last_sector_time = 0  # Track the last sector's end time
        self.current_sector_start_time = 0  # Track when the current sector started
        self.track_name = "Unknown"  # Track name from session data
        
        # Register packet handlers
        self.listener.register_callback(
            PACKET_IDS['CAR_TELEMETRY'],
            self._handle_car_telemetry
        )
        self.listener.register_callback(
            PACKET_IDS['LAP_DATA'],
            self._handle_lap_data
        )
        self.listener.register_callback(
            PACKET_IDS['SESSION'],
            self._handle_session
        )
        
        # Setup signal handler for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Setup GUI callbacks
        self.gui.set_record_callback(self._start_recording)
        self.gui.set_stop_callback(self._stop_recording)

    def _handle_session(self, packet: PacketSessionData):
        """Handle session packet to get track and session information"""
        track_id = packet.m_trackId
        if track_id >= 0 and track_id in TRACK_IDS:
            self.track_name = TRACK_IDS[track_id]
            print(f"Track identified as: {self.track_name}")
            
            # Update track name in data logger if recording
            if self.data_logger and self.data_logger.is_recording:
                self.data_logger.update_session_info({
                    "track_name": self.track_name
                })
            
            # Update track info in visualizer
            track_length = packet.m_trackLength
            # For now, we'll use simple sector divisions at 1/3 and 2/3 of track length
            sector_distances = [track_length / 3, 2 * track_length / 3]
            self.gui.visualizer.set_track_info(track_length, sector_distances)

    def _handle_car_telemetry(self, packet: PacketCarTelemetryData):
        """Handle car telemetry packet"""
        if self.player_car_index is None:
            return
            
        car_data = packet.m_carTelemetryData[self.player_car_index]
        
        # Update current telemetry data
        self.current_telemetry.speed = car_data.m_speed
        self.current_telemetry.rpm = car_data.m_engineRPM
        self.current_telemetry.gear = car_data.m_gear
        self.current_telemetry.throttle = car_data.m_throttle
        self.current_telemetry.brake = car_data.m_brake
        self.current_telemetry.steer = car_data.m_steer
        self.current_telemetry.drs = car_data.m_drs
        
        # Add tire temperatures
        self.current_telemetry.tyresSurfaceTemperature = list(car_data.m_tyresSurfaceTemperature)
        
        # Update GUI
        self.gui.update_telemetry(self.current_telemetry)
        
        # Record telemetry if session is active
        if self.data_logger and self.data_logger.is_recording:
            self.data_logger.record_telemetry(
                self.current_telemetry,
                {
                    "lap_number": self.current_lap_number,
                    "lap_distance": 0,  # Will be updated from lap data
                    "current_lap_invalid": False  # Will be updated from lap data
                }
            )

    def _handle_lap_data(self, packet: PacketLapData):
        """Handle lap data packet"""
        if self.player_car_index is None:
            # In F1 22, the player car index is typically 0 for single player
            self.player_car_index = 0
            
        lap_data = packet.m_lapData[self.player_car_index]
        
        # Update current lap validity
        if lap_data.m_currentLapInvalid:
            self.current_lap_invalid = True
        
        # Track sector changes
        current_sector = lap_data.m_sector
        current_lap_time = lap_data.m_currentLapTimeInMS
        
        # Update current telemetry with sector information
        self.current_telemetry.current_sector = current_sector
        self.current_telemetry.lap_distance = lap_data.m_lapDistance  # Add lap distance for visualization
        
        # If we've moved to a new sector, update our sector tracking
        if current_sector > 0 and self.last_sector_time == 0:  # Just finished sector 1
            self.last_sector_time = current_lap_time
            self.current_sector_start_time = current_lap_time
            # Update sector 1 time in telemetry
            self.current_telemetry.sector1_time = current_lap_time
        elif current_sector > 1 and self.current_telemetry.sector2_time == 0:  # Just finished sector 2
            sector2_time = current_lap_time - self.last_sector_time
            self.current_telemetry.sector2_time = sector2_time
            # Update last sector time for sector 3 calculation
            self.last_sector_time = current_lap_time
        elif current_sector == 0:  # Just finished sector 3 or completed a lap
            # Calculate sector 3 time as the remainder of total lap time
            total_lap_time = lap_data.m_lastLapTimeInMS if lap_data.m_lastLapTimeInMS > 0 else current_lap_time
            if total_lap_time > 0 and self.current_telemetry.sector1_time > 0 and self.current_telemetry.sector2_time > 0:
                sector3_time = total_lap_time - (self.current_telemetry.sector1_time + self.current_telemetry.sector2_time)
                if sector3_time > 0:  # Only set if we got a valid positive time
                    self.current_telemetry.sector3_time = sector3_time
        
        # Update lap information
        new_lap_number = lap_data.m_currentLapNum
        if new_lap_number != self.current_lap_number:
            # Completed a lap
            if self.current_lap_number > 0:
                self.last_lap_time = lap_data.m_lastLapTimeInMS
                
                # Log all lap data fields for debugging
                print("\nComplete lap data for debugging:")
                for field in dir(lap_data):
                    if not field.startswith('_'):  # Only print non-private fields
                        try:
                            value = getattr(lap_data, field)
                            print(f"{field}: {value}")
                        except:
                            pass
                print("\n")
                
                # Calculate sector times based on both stored and packet data
                sector1_time = self.current_telemetry.sector1_time
                sector2_time = self.current_telemetry.sector2_time
                sector3_time = self.current_telemetry.sector3_time
                
                print(f"Completed lap {self.current_lap_number}: {'Invalid' if self.current_lap_invalid else 'Valid'}")
                print(f"Lap time: {self.last_lap_time}ms")
                print(f"Sector times (including tracked times):")
                print(f"  Sector 1: {sector1_time}ms ({sector1_time/1000:.3f}s)")
                print(f"  Sector 2: {sector2_time}ms ({sector2_time/1000:.3f}s)")
                print(f"  Sector 3: {sector3_time}ms ({sector3_time/1000:.3f}s)")
                print(f"  Total: {self.last_lap_time}ms ({self.last_lap_time/1000:.3f}s)")
                
                # Update session info with lap and sector times
                if self.data_logger and self.data_logger.is_recording:
                    self.data_logger.update_session_info({
                        f"lap_times.{self.current_lap_number}": self.last_lap_time,
                        f"sector_times.{self.current_lap_number}": [
                            sector1_time,
                            sector2_time,
                            sector3_time
                        ],
                        f"lap_valid.{self.current_lap_number}": not self.current_lap_invalid,
                        "total_laps": self.current_lap_number
                    })
                
                self.gui.add_lap_time(
                    self.current_lap_number,
                    self.last_lap_time,
                    not self.current_lap_invalid
                )
                
                # Reset sector tracking for new lap
                self.last_sector_time = 0
                self.current_sector_start_time = 0
                self.current_telemetry.sector1_time = 0
                self.current_telemetry.sector2_time = 0
                self.current_telemetry.sector3_time = 0
            
            # Reset for new lap
            self.current_lap_number = new_lap_number
            self.current_lap_invalid = False  # Reset validity for new lap
        
        # Update session information in GUI
        self.gui.update_session_info(
            self.current_lap_number,
            self.last_lap_time,
            self.data_logger.is_recording if self.data_logger else False,
            not self.current_lap_invalid
        )
        
        # Update current telemetry lap data
        if self.data_logger and self.data_logger.is_recording:
            self.current_telemetry.lap_time = lap_data.m_currentLapTimeInMS
            
            # Update lap data for recording
            lap_info = {
                "lap_number": self.current_lap_number,
                "lap_distance": lap_data.m_lapDistance,
                "current_lap_invalid": self.current_lap_invalid,
                "sector": current_sector,
                "current_lap_time_ms": lap_data.m_currentLapTimeInMS,
                "last_lap_time_ms": lap_data.m_lastLapTimeInMS,
                "sector1_time_ms": self.current_telemetry.sector1_time,
                "sector2_time_ms": self.current_telemetry.sector2_time,
                "sector3_time_ms": self.current_telemetry.sector3_time,
                # Add raw data for debugging
                "raw_current_sector": lap_data.m_sector,
                "raw_lap_distance": lap_data.m_lapDistance
            }
            
            self.data_logger.record_telemetry(self.current_telemetry, lap_info)

    def _start_recording(self):
        """Start recording telemetry data"""
        if not self.data_logger.is_recording:
            print(f"\nStarting new recording session on track: {self.track_name}")
            self.data_logger.start_session(track_name=self.track_name)
            self.gui.toggle_recording_state(True)

    def _stop_recording(self):
        """Stop recording telemetry data"""
        if self.data_logger.is_recording:
            print("\nStopping recording session...")
            # Get final session info before stopping
            final_session_info = self.data_logger.get_session_stats()
            self.data_logger.stop_session()
            self.gui.toggle_recording_state(False)
            
            try:
                # Find and analyze the latest session
                sessions = list(Path("telemetry_logs").glob("session_*"))
                if not sessions:
                    print("No session directories found!")
                    return
                    
                latest_session = max(sessions, key=lambda p: p.stat().st_mtime)
                print(f"Analyzing session: {latest_session}")
                
                # Create analyzer with the final session info
                analyzer = SessionAnalyzer(latest_session)
                summary = analyzer.get_session_summary()
                
                # Ensure we have the complete session data
                if not summary.get("lap_times"):
                    summary.update(final_session_info)
                
                print(f"Session summary: {summary}")
                
                # Update GUI with analysis
                self.gui.update_analysis(summary)
                print("Analysis updated in GUI")
                
            except Exception as e:
                print(f"Error analyzing session: {e}")
                import traceback
                traceback.print_exc()

    def _signal_handler(self, sig, frame):
        """Handle shutdown signal"""
        print("\nShutting down...")
        if self.data_logger and self.data_logger.is_recording:
            self._stop_recording()
        self.listener.stop()
        sys.exit(0)

    def run(self):
        """Start the application"""
        try:
            # Start the telemetry listener
            self.listener.start()
            
            # Start the GUI
            self.gui.run()
            
        except KeyboardInterrupt:
            self._signal_handler(None, None)
        finally:
            if self.data_logger and self.data_logger.is_recording:
                self._stop_recording()
            self.listener.stop()

if __name__ == "__main__":
    app = F1TelemetryApp()
    app.run() 
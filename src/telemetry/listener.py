import socket
import struct
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import threading
import time
import binascii

# F1 23 Packet IDs (assuming latest, adjust if needed for F1 22)
MOTION_PACKET_ID = 0
SESSION_PACKET_ID = 1
LAP_DATA_PACKET_ID = 2
EVENT_PACKET_ID = 3
PARTICIPANTS_PACKET_ID = 4
CAR_SETUPS_PACKET_ID = 5
CAR_TELEMETRY_PACKET_ID = 6
CAR_STATUS_PACKET_ID = 7
FINAL_CLASSIFICATION_PACKET_ID = 8
LOBBY_INFO_PACKET_ID = 9
CAR_DAMAGE_PACKET_ID = 10
SESSION_HISTORY_PACKET_ID = 11
TYRE_SETS_PACKET_ID = 12       # New in F1 23
MOTION_EX_PACKET_ID = 13       # New in F1 23


# Mappings (expand as needed from F1 documentation)
# For F1 22/23, refer to official documentation for complete lists
TRACK_IDS = {
    0: "Melbourne", 1: "Paul Ricard", 2: "Shanghai", 3: "Sakhir (Bahrain)", 4: "Catalunya", 5: "Monaco",
    6: "Montreal", 7: "Silverstone", 8: "Hockenheim", 9: "Hungaroring", 10: "Spa", 11: "Monza",
    12: "Singapore", 13: "Suzuka", 14: "Abu Dhabi", 15: "Texas", 16: "Brazil", 17: "Austria",
    18: "Sochi", 19: "Mexico", 20: "Baku (Azerbaijan)", 21: "Sakhir Short", 22: "Silverstone Short",
    23: "Texas Short", 24: "Suzuka Short", 25: "Hanoi", 26: "Zandvoort", 27: "Imola",
    28: "Portimao", 29: "Jeddah", 30: "Miami", 31: "Las Vegas", 32: "Qatar"
    # Add more as per F1 22/23 spec
}

SESSION_TYPES = {
    0: "Unknown", 1: "P1", 2: "P2", 3: "P3", 4: "Short P", 5: "Q1", 6: "Q2", 7: "Q3",
    8: "Short Q", 9: "OSQ", 10: "Race", 11: "Race 2", 12: "Race 3", 13: "Time Trial"
}

WEATHER_IDS = {
    0: "Clear", 1: "Light Cloud", 2: "Overcast", 3: "Light Rain", 4: "Heavy Rain", 5: "Storm"
}

CAR_IDS = { # F1 22 Example, update for current game if needed
    0: "Mercedes", 1: "Ferrari", 2: "Red Bull Racing", 3: "Williams", 4: "Aston Martin",
    5: "Alpine", 6: "AlphaTauri", 7: "Haas", 8: "McLaren", 9: "Alfa Romeo",
    # Add F2 cars, classic cars etc. if needed
    85: "Mercedes 2020", # Example from F1 2021
}


@dataclass
class CompletedLap:
    lap_number: int = 0
    lap_time_ms: int = 0
    sector1_time_ms: int = 0
    sector2_time_ms: int = 0
    sector3_time_ms: int = 0
    is_valid: bool = True
    is_event_lap: bool = False # Flag to denote if this is from a live EVENT_PACKET cross-the-line, not history yet

@dataclass
class TelemetryData:
    # Core Telemetry
    speed: float = 0.0
    engine_rpm: float = 0.0
    throttle: float = 0.0
    brake: float = 0.0
    steering: float = 0.0
    gear: int = 0
    
    # Session Info
    session_active: bool = False
    session_type_id: int = 0
    session_type_str: str = "N/A"
    track_id: int = -1
    track_name: str = "N/A"
    weather_id: int = 0
    weather_str: str = "N/A"
    player_car_index: int = -1
    car_name: str = "N/A"
    session_time_elapsed: float = 0.0 # Total session time

    # Live Lap Info
    current_lap_num: int = 0
    current_lap_time_sec: float = 0.0 # From CAR_TELEMETRY_PACKET_ID or LAP_DATA_PACKET_ID
    current_lap_invalid: bool = False
    current_sector: int = 0
    current_sector1_time_ms: int = 0
    current_sector2_time_ms: int = 0
    
    # Completed Laps Data
    completed_laps_history: List[CompletedLap] = field(default_factory=list) # Store laps from SessionHistoryPacket
    newly_completed_lap_event: Optional[CompletedLap] = None # To signal GUI about a new lap from EVENT (lap finished)

class F1TelemetryListener:
    def __init__(self, host: str = '127.0.0.1', port: int = 20777):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.latest_data = TelemetryData()
        self._lock = threading.Lock()
        self.last_debug_time = time.time()
        self.last_session_packet_time = 0 # To detect session end by timeout
        self.last_known_player_lap_num_from_lap_data = 0 # To help with history packet logic

    def start(self):
        """Start listening for telemetry data."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(0.1) # Increased timeout slightly
            self.socket.bind((self.host, self.port))
            print(f"F1 Telemetry (F1 2022 Profile): Listening on {self.host}:{self.port}")
            self.running = True
            self.listener_thread = threading.Thread(target=self._listen)
            self.listener_thread.daemon = True
            self.listener_thread.start()
        except Exception as e:
            print(f"Error starting listener: {e}")
            self.running = False
            if self.socket:
                self.socket.close()
            raise

    def stop(self):
        """Stop listening for telemetry data."""
        self.running = False
        # Signal potential session end if it was active
        if self.latest_data.session_active:
            with self._lock:
                self.latest_data.session_active = False
                print("Listener stopping, session marked as inactive.")
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.socket = None
        print("Listener thread stopped.")

    def _listen(self):
        """Main listener loop for telemetry data."""
        PACKET_HEADER_SIZE_F122 = 24 # Standard for F1 2022
        while self.running and self.socket:
            try:
                data, addr = self.socket.recvfrom(2048)
                if not data or len(data) < PACKET_HEADER_SIZE_F122:
                    if data: print(f"DEBUG: Runt packet (len: {len(data)})")
                    continue

                packet_id = data[5]
                session_time = struct.unpack('<f', data[14:18])[0]
                player_car_index_hdr = data[22] 

                with self._lock:
                    self.latest_data.player_car_index = player_car_index_hdr
                    self.latest_data.session_time_elapsed = session_time
                    self.latest_data.newly_completed_lap_event = None # Reset flag

                self._process_packet(data, packet_id, player_car_index_hdr, PACKET_HEADER_SIZE_F122)
                
                if self.latest_data.session_active and (time.time() - self.last_session_packet_time > 10.0):
                    with self._lock:
                        if self.latest_data.session_active: 
                             print("Session timeout detected. Marking session as inactive.")
                             self.latest_data.session_active = False
            except socket.timeout:
                continue
            except socket.error as e:
                if not self.running: break
                print(f"Socket error: {e}")
            except Exception as e:
                packet_id_str = str(packet_id) if 'packet_id' in locals() else 'N/A'
                print(f"Error in _listen loop (Packet ID {packet_id_str}): {e}")
                import traceback
                traceback.print_exc()
        print("Listener thread successfully shutdown.")

    def _extract_string(self, data, offset, length):
        try:
            return data[offset:offset+length].split(b'\0', 1)[0].decode('utf-8', 'ignore')
        except Exception: return "N/A"

    def _process_packet(self, data, packet_id, player_car_idx, header_size):
        payload = data[header_size:] # Actual packet data starts after the header

        if packet_id == SESSION_PACKET_ID: # Packet ID 1
            with self._lock:
                self.last_session_packet_time = time.time()
                if not self.latest_data.session_active:
                     print("Session Packet Received - Session active.")
                     self.latest_data.session_active = True
                     self.latest_data.completed_laps_history.clear() 
                     self.last_known_player_lap_num_from_lap_data = 0 # Reset for new session

                self.latest_data.weather_id = payload[0]  # m_weather (offset 0 in payload)
                # m_trackId is int8 at offset 2 in payload for F1 2022
                self.latest_data.track_id = struct.unpack('<b', payload[2:3])[0] 
                self.latest_data.session_type_id = payload[11] # m_sessionType (offset 11 in payload)
                
                self.latest_data.weather_str = WEATHER_IDS.get(self.latest_data.weather_id, f"Unknown ({self.latest_data.weather_id})")
                self.latest_data.track_name = TRACK_IDS.get(self.latest_data.track_id, f"Unknown Track ({self.latest_data.track_id})")
                self.latest_data.session_type_str = SESSION_TYPES.get(self.latest_data.session_type_id, f"Unknown ({self.latest_data.session_type_id})")
            return True

        elif packet_id == PARTICIPANTS_PACKET_ID: # Packet ID 4
            PARTICIPANT_DATA_SIZE_F122 = 56 
            num_active_cars = payload[0] # m_numActiveCars
            if player_car_idx < num_active_cars:
                # offset within m_participants array, which starts at payload[1]
                participant_offset = 1 + (player_car_idx * PARTICIPANT_DATA_SIZE_F122)
                if participant_offset + 48 < len(payload): # Check for name field
                    car_id_raw = payload[participant_offset + 2] # m_teamId for F1 2022
                    # name = self._extract_string(payload, participant_offset + 4, 48) # m_name
                    with self._lock:
                        self.latest_data.car_name = CAR_IDS.get(car_id_raw, f"Unknown Car ({car_id_raw})")
            return True

        elif packet_id == LAP_DATA_PACKET_ID: # Packet ID 2
            LAP_INFO_SIZE_F122 = 43
            lap_data_offset = player_car_idx * LAP_INFO_SIZE_F122
            
            if lap_data_offset + 23 <= len(payload): # Check up to m_lapInvalidated
                with self._lock:
                    # m_currentLapTimeInMS (uint32) at offset 0 of this player's LapData structure
                    self.latest_data.current_lap_time_sec = struct.unpack('<I', payload[lap_data_offset+0 : lap_data_offset+4])[0] / 1000.0
                    self.latest_data.current_sector = payload[lap_data_offset + 10] + 1 # m_sector (0-2 -> 1-3)
                    self.latest_data.current_sector1_time_ms = struct.unpack('<H', payload[lap_data_offset+12 : lap_data_offset+14])[0]
                    self.latest_data.current_sector2_time_ms = struct.unpack('<H', payload[lap_data_offset+14 : lap_data_offset+16])[0]
                    self.latest_data.current_lap_num = payload[lap_data_offset + 18] # m_currentLapNum (uint8)
                    self.last_known_player_lap_num_from_lap_data = self.latest_data.current_lap_num
                    self.latest_data.current_lap_invalid = (payload[lap_data_offset + 23] == 1) # m_lapInvalidated (uint8)
            return True

        elif packet_id == CAR_TELEMETRY_PACKET_ID: # Packet ID 6
            CAR_TELEMETRY_DATA_SIZE_F122 = 58
            telemetry_offset = player_car_idx * CAR_TELEMETRY_DATA_SIZE_F122
            if telemetry_offset + 17 <= len(payload):
                with self._lock:
                    self.latest_data.speed = float(struct.unpack('<H', payload[telemetry_offset + 0 : telemetry_offset + 2])[0])
                    self.latest_data.throttle = struct.unpack('<f', payload[telemetry_offset + 2 : telemetry_offset + 6])[0]
                    self.latest_data.steering = struct.unpack('<f', payload[telemetry_offset + 6 : telemetry_offset + 10])[0]
                    self.latest_data.brake = struct.unpack('<f', payload[telemetry_offset + 10 : telemetry_offset + 14])[0]
                    self.latest_data.gear = struct.unpack('<b', payload[telemetry_offset + 14 : telemetry_offset + 15])[0]
                    self.latest_data.engine_rpm = float(struct.unpack('<H', payload[telemetry_offset + 15 : telemetry_offset + 17])[0])
            return True
        
        elif packet_id == EVENT_PACKET_ID: # Packet ID 3
            event_string_code = payload[0:4].decode('utf-8', 'ignore')
            if event_string_code == "FTLP" or event_string_code == "SSTA": # FTLP = Fastest Lap, SSTA = Session Started
                 pass # Could use SSTA to also trigger session active, but SESSION_PACKET is primary

            if event_string_code == "LPNF": # Lap Not Finished (Outlap or Inlap - not a timed lap completion)
                pass # Could use this to know when a lap doesn't count towards history perhaps

            if event_string_code == "LAFN": # Lap Finished
                # This event packet provides lap data for the lap *just completed*
                # Vehicle index is at payload[4], laptime at payload[5:9] etc.
                event_vehicle_idx = payload[4]
                if event_vehicle_idx == self.latest_data.player_car_index:
                    lap_time_ms = struct.unpack('<I', payload[5:9])[0]
                    s1_ms = struct.unpack('<H', payload[9:11])[0]
                    s2_ms = struct.unpack('<H', payload[11:13])[0]
                    # F1 22 Event Packet for LAFN doesn't explicitly list S3 or overall validity.
                    # S3 must be calculated: LapTime - S1 - S2.
                    # Validity must be inferred or taken from LapData just before this event.
                    s3_ms = lap_time_ms - s1_ms - s2_ms if (s1_ms > 0 and s2_ms > 0 and lap_time_ms > (s1_ms+s2_ms)) else 0
                    
                    # Determine lap number for this event. It should be self.latest_data.current_lap_num (from LapData before this event)
                    completed_lap_number = self.latest_data.current_lap_num 
                    
                    # Check if this lap number is already in SessionHistory data to avoid double logging
                    already_in_history = any(l.lap_number == completed_lap_number for l in self.latest_data.completed_laps_history)

                    if not already_in_history and lap_time_ms > 0:
                        new_lap_event_data = CompletedLap(
                            lap_number=completed_lap_number,
                            lap_time_ms=lap_time_ms,
                            sector1_time_ms=s1_ms,
                            sector2_time_ms=s2_ms,
                            sector3_time_ms=s3_ms,
                            is_valid=not self.latest_data.current_lap_invalid, # Use validity from LapData of this lap
                            is_event_lap=True
                        )
                        with self._lock:
                            self.latest_data.newly_completed_lap_event = new_lap_event_data
                            # Optionally add to a temporary list if SessionHistory is slow, but SessionHistory is preferred source of truth.
                        print(f"Listener: Lap {completed_lap_number} finished (EVENT). Time: {lap_time_ms/1000.0:.3f}s, Valid: {not self.latest_data.current_lap_invalid}")
            return True

        elif packet_id == SESSION_HISTORY_PACKET_ID: # Packet ID 11
            history_car_idx = payload[0] # m_carIdx for which this history belongs
            
            if history_car_idx == self.latest_data.player_car_index: 
                num_laps_in_history = payload[1] # m_numLaps (total laps for this car in array)
                LAP_HISTORY_ENTRY_SIZE_F122 = 23 
                lap_history_array_offset = 2 # Offset from start of payload to m_lapHistoryData[0]
                                            # (m_carIdx, m_numLaps, m_numTyreStints = 3 bytes, then best lap/sector numbers)
                                            # F1 2022 spec: m_lapHistoryData is at index 2 within this packet's payload if no best lap num etc.
                                            # More precise: header(24) + carIdx(1) + numLaps(1) + numTyreStints(1) + bestLapTimeLapNum(1) + bestSector1LapNum(1) + bestSector2LapNum(1) + bestSector3LapNum(1) = 31. 
                                            # So payload offset to array is 7 from start of payload.
                lap_history_array_payload_offset = 7 # carIdx(1) + numLaps(1) + numTyreStints(1) + bests(4) = 7

                new_laps_from_history = []
                for i in range(num_laps_in_history):
                    entry_offset = lap_history_array_payload_offset + (i * LAP_HISTORY_ENTRY_SIZE_F122)
                    if entry_offset + LAP_HISTORY_ENTRY_SIZE_F122 > len(payload): break # Out of bounds

                    lap_time_ms = struct.unpack('<I', payload[entry_offset+0 : entry_offset+4])[0]
                    if lap_time_ms == 0: continue # Skip laps with no time (e.g. out lap)

                    s1_ms = struct.unpack('<H', payload[entry_offset+4 : entry_offset+6])[0]
                    s2_ms = struct.unpack('<H', payload[entry_offset+6 : entry_offset+8])[0]
                    s3_ms = struct.unpack('<H', payload[entry_offset+8 : entry_offset+10])[0]
                    lap_valid_byte = payload[entry_offset+10] # lapValidBitFlags
                    is_lap_overall_valid = (lap_valid_byte & 0x01) != 0
                    
                    # Lap number for history entries is simply i + 1
                    lap_num_in_history_entry = i + 1

                    # Check if we've already recorded this lap from history
                    already_recorded = any(l.lap_number == lap_num_in_history_entry for l in self.latest_data.completed_laps_history)
                    if not already_recorded:
                        new_lap = CompletedLap(
                            lap_number=lap_num_in_history_entry,
                            lap_time_ms=lap_time_ms,
                            sector1_time_ms=s1_ms,
                            sector2_time_ms=s2_ms,
                            sector3_time_ms=s3_ms,
                            is_valid=is_lap_overall_valid
                        )
                        new_laps_from_history.append(new_lap)
                
                if new_laps_from_history:
                    with self._lock:
                        for lap in new_laps_from_history:
                            # Avoid adding if a similar lap (by number) was just added via LAFN event & not yet superseded by history
                            event_lap_match = next((el for el in [self.latest_data.newly_completed_lap_event] if el and el.lap_number == lap.lap_number and el.is_event_lap), None)
                            if event_lap_match:
                                # History packet is source of truth, replace event lap if it existed
                                self.latest_data.completed_laps_history = [l for l in self.latest_data.completed_laps_history if l.lap_number != lap.lap_number]
                            
                            self.latest_data.completed_laps_history.append(lap)
                            # Sort by lap number to be sure, though they should come in order
                            self.latest_data.completed_laps_history.sort(key=lambda x: x.lap_number)
                            # The GUI will use completed_laps_history for its table.
                            # The newly_completed_lap_event is for more immediate GUI update from LAFN.
                            # If history provides a lap, it's the definitive one.
                            print(f"Listener: Lap {lap.lap_number} processed from SessionHistory. Time: {lap.lap_time_ms/1000.0:.3f}s")
            return True
        return False # Packet not fully processed for critical data updates by this function

    def _extract_float(self, data, offset):
        """Safely extract a float value from the data at the given offset."""
        try:
            if offset + 4 <= len(data):
                return struct.unpack('<f', data[offset:offset+4])[0]
            return None
        except Exception:
            return None
            
    def _extract_ushort(self, data, offset):
        """Safely extract an unsigned short value from the data at the given offset."""
        try:
            if offset + 2 <= len(data):
                return struct.unpack('<H', data[offset:offset+2])[0]
            return None
        except Exception:
            return None
            
    def _extract_sbyte(self, data, offset): # For signed byte (like gear)
        """Safely extract a signed byte value from the data at the given offset."""
        try:
            if offset < len(data):
                return struct.unpack('<b', data[offset:offset+1])[0]
            return None
        except Exception:
            return None
            
    def _extract_uint(self, data, offset):
        """Safely extract an unsigned int (4 bytes) value from the data at the given offset."""
        try:
            if offset + 4 <= len(data):
                return struct.unpack('<I', data[offset:offset+4])[0]
            return None
        except Exception:
            return None

    def get_current_telemetry(self) -> TelemetryData:
        """Get the latest telemetry data."""
        with self._lock:
            # Return a copy to prevent modification outside listener if GUI is complex
            # For now, direct object is fine if GUI is careful or copies itself.
            return self.latest_data 
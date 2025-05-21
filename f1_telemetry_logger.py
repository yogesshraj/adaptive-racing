import socket
import struct
import csv
import uuid
import os

# Constants
UDP_IP = "0.0.0.0"  # Listen on all available interfaces
UDP_PORT = 20777       # Default F1 22 port
CSV_FILENAME = "f1_telemetry_data.csv"
CSV_HEADER = [
    "Session ID", "Session Type", "Track Name", "Race Car", "Track Weather",
    "Lap Number", "Sector 1 Time", "Sector 2 Time", "Sector 3 Time",
    "Total Lap Time", "Valid Lap"
]

# --- Mappings ---
# These will be populated based on the F1 22 UDP specification
TRACK_IDS = {
    0: "Melbourne", 1: "Paul Ricard", 2: "Shanghai", 3: "Sakhir (Bahrain)",
    4: "Catalunya", 5: "Monaco", 6: "Montreal", 7: "Silverstone",
    8: "Hockenheim", 9: "Hungaroring", 10: "Spa", 11: "Monza",
    12: "Singapore", 13: "Suzuka", 14: "Abu Dhabi", 15: "Texas",
    16: "Brazil", 17: "Austria", 18: "Sochi", 19: "Mexico",
    20: "Baku (Azerbaijan)", 21: "Sakhir Short", 22: "Silverstone Short",
    23: "Texas Short", 24: "Suzuka Short", 25: "Hanoi", 26: "Zandvoort",
    27: "Imola", 28: "Portimão", 29: "Jeddah", 30: "Miami",
    -1: "Unknown"
}

SESSION_TYPES = {
    0: "Unknown", 1: "P1", 2: "P2", 3: "P3", 4: "Short P", 5: "Q1",
    6: "Q2", 7: "Q3", 8: "Short Q", 9: "OSQ", 10: "R", 11: "R2",
    12: "R3", 13: "Time Trial"
}

WEATHER_TYPES = {
    0: "Clear", 1: "Light Cloud", 2: "Overcast", 3: "Light Rain",
    4: "Heavy Rain", 5: "Storm"
}

TEAM_IDS = {
    0: "Mercedes", 1: "Ferrari", 2: "Red Bull Racing", 3: "Williams",
    4: "Aston Martin", 5: "Alpine", 6: "Alpha Tauri", 7: "Haas",
    8: "McLaren", 9: "Alfa Romeo", 85: "Mercedes 2020", 86: "Ferrari 2020",
    87: "Red Bull 2020", 88: "Williams 2020", 89: "Racing Point 2020",
    90: "Renault 2020", 91: "Alpha Tauri 2020", 92: "Haas 2020",
    93: "McLaren 2020", 94: "Alfa Romeo 2020", 95: "Aston Martin DB11 V12",
    96: "Aston Martin Vantage F1 Edition", 97: "Aston Martin Vantage Safety Car",
    98: "Ferrari F8 Tributo", 99: "Ferrari Roma", 100: "McLaren 720S",
    101: "McLaren Artura", 102: "Mercedes AMG GT Black Series Safety Car",
    103: "Mercedes AMG GTR Pro", 104: "F1 Custom Team", 106: "Prema '21",
    107: "Uni-Virtuosi '21", 108: "Carlin '21", 109: "Hitech '21",
    110: "Art GP '21", 111: "MP Motorsport '21", 112: "Charouz '21",
    113: "Dams '21", 114: "Campos '21", 115: "BWT '21", 116: "Trident '21",
    117: "Mercedes AMG GT Black Series", 118: "Prema '22", 119: "Virtuosi '22",
    120: "Carlin '22", 121: "Hitech '22", 122: "Art GP '22",
    123: "MP Motorsport '22", 124: "Charouz '22", 125: "Dams '22",
    126: "Campos '22", 127: "Van Amersfoort Racing '22", 128: "Trident '22"
}
# --- End Mappings ---

# Global state variables
current_session_id = None
last_session_uid = None
# last_session_type = -1 # Stores the raw m_sessionType
# The above line is commented out because it's not used for session change detection, session_uid is sufficient with m_sessionType from the current packet.
# For more robust session change detection, we should use a combination of m_sessionUID and m_sessionType.
# Let's refine this: A new session is primarily defined by a change in m_sessionUID.
# If m_sessionUID changes, it's definitely a new session.
# If m_sessionUID is the same, but m_sessionType changes, it's also considered a new race session context.
_internal_last_processed_session_uid_for_id_generation = None
_internal_last_processed_session_type_for_id_generation = -1

player_car_index = None
current_track_name = "Unknown"
current_race_car = "Unknown"
current_session_type_str = "Unknown"
current_weather_str = "Unknown"

# --- Packet Header Structure ---
# struct PacketHeader {
#     uint16    m_packetFormat;            // 2022
#     uint8     m_gameMajorVersion;        // Game major version - "X.00"
#     uint8     m_gameMinorVersion;        // Game minor version - "1.XX"
#     uint8     m_packetVersion;           // Version of this packet type, all start from 1
#     uint8     m_packetId;                // Identifier for the packet type, see below
#     uint64    m_sessionUID;              // Unique identifier for the session
#     float     m_sessionTime;             // Session timestamp
#     uint32    m_frameIdentifier;         // Identifier for the frame the data was retrieved on
#     uint8     m_playerCarIndex;          // Index of player's car in the array
#     uint8     m_secondaryPlayerCarIndex; // Index of secondary player's car in the array (splitscreen)
#                                          // 255 if no second player
# };
PACKET_HEADER_FORMAT = '<HBBBBQfIBB'
# print(f"DEBUG: PACKET_HEADER_FORMAT = {PACKET_HEADER_FORMAT}") # Debug
PACKET_HEADER_SIZE = struct.calcsize(PACKET_HEADER_FORMAT)


# --- LapData Structure (for a single car) ---
# Based on F1 22 UDP Specification for LapData within PacketLapData.m_lapData[22]
# uint32   m_lastLapTimeInMS;
# uint32   m_currentLapTimeInMS;
# uint16   m_sector1TimeInMS;
# uint16   m_sector2TimeInMS;
# float    m_lapDistance;
# float    m_totalDistance;
# float    m_safetyCarDelta;
# uint8    m_carPosition;
# uint8    m_currentLapNum;
# uint8    m_pitStatus;
# uint8    m_numPitStops;
# uint8    m_sector;
# uint8    m_currentLapInvalid;
# uint8    m_penalties;
# uint8    m_warnings;
# uint8    m_numUnservedDriveThroughPens;
# uint8    m_numUnservedStopGoPens;
# uint8    m_gridPosition;
# uint8    m_driverStatus;
# uint8    m_resultStatus;
# uint8    m_pitLaneTimerActive;
# uint16   m_pitLaneTimeInLaneInMS;
# uint16   m_pitStopTimerInMS;
# uint8    m_pitStopShouldServePen;
# Total expected size: 43 bytes
LAP_DATA_SINGLE_CAR_FORMAT = '<IIHHfffBBBBBBBBBBBBBHHB' # 2I, 2H, 3f, 13B, 2H, 1B
LAP_DATA_SINGLE_CAR_SIZE = struct.calcsize(LAP_DATA_SINGLE_CAR_FORMAT)
# print(f"DEBUG: LAP_DATA_SINGLE_CAR_FORMAT size: {LAP_DATA_SINGLE_CAR_SIZE}") # Should be 43


# --- New structures for Session History ---
# struct LapHistoryData {
#     uint32    m_lapTimeInMS;
#     uint16    m_sector1TimeInMS;
#     uint16    m_sector2TimeInMS;
#     uint16    m_sector3TimeInMS;
#     uint8     m_lapValidBitFlags; // 0x01 bit set-lap valid, 0x02 bit set-sector 1 valid, etc.
# };
LAP_HISTORY_ENTRY_FORMAT = '<IHHHB' # Size: 4 (I) + 2(H) + 2(H) + 2(H) + 1(B) = 11 bytes
LAP_HISTORY_ENTRY_SIZE = struct.calcsize(LAP_HISTORY_ENTRY_FORMAT)

# For PacketSessionHistoryData, we need carIdx, numLaps, and then the array.
# uint8 m_carIdx;
# uint8 m_numLaps;
# uint8 m_numTyreStints;
# uint8 m_bestLapTimeLapNum;
# uint8 m_bestSector1LapNum;
# uint8 m_bestSector2LapNum;
# uint8 m_bestSector3LapNum;
# These are 7 bytes after the header.
SESSION_HISTORY_LEAD_DATA_FORMAT = '<BBBBBBB'
SESSION_HISTORY_LEAD_DATA_SIZE = struct.calcsize(SESSION_HISTORY_LEAD_DATA_FORMAT)
# --- End new structures ---


# Global state for pending laps waiting for history data
pending_lap_details = {} # Key: (session_id, completed_lap_num), Value: (current_session_type_str, current_track_name_str, current_race_car_str, current_weather_str)
logged_laps_in_session = set()


def parse_packet_header(data):
    """Parses the header of a UDP packet."""
    # print(f"DEBUG: parse_packet_header called with data length: {len(data)}") # Debug
    # print(f"DEBUG: Using PACKET_HEADER_FORMAT: {PACKET_HEADER_FORMAT} for unpack") # Debug
    header_data = data[:PACKET_HEADER_SIZE]
    return struct.unpack(PACKET_HEADER_FORMAT, header_data)

def get_session_type_str(session_type_id):
    return SESSION_TYPES.get(session_type_id, "Unknown")

def get_track_name_str(track_id):
    return TRACK_IDS.get(track_id, "Unknown Track")

def get_weather_str(weather_id):
    return WEATHER_TYPES.get(weather_id, "Unknown Weather")

def get_team_name_str(team_id):
    return TEAM_IDS.get(team_id, "Unknown Car")


def write_csv_header_if_needed():
    """Writes the CSV header if the file doesn't exist or is empty."""
    file_exists = os.path.isfile(CSV_FILENAME)
    if not file_exists or os.path.getsize(CSV_FILENAME) == 0:
        with open(CSV_FILENAME, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(CSV_HEADER)
        print(f"CSV header written to {CSV_FILENAME}")


def log_lap_data_to_csv(lap_data_tuple):
    """Appends a lap's data to the CSV file."""
    with open(CSV_FILENAME, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(lap_data_tuple)
    # print(f"Lap data logged: {lap_data_tuple}") # For debugging


def process_session_packet(data):
    """Processes PacketSessionData (Packet ID 1)."""
    global current_session_id, last_session_uid, _internal_last_processed_session_uid_for_id_generation, _internal_last_processed_session_type_for_id_generation
    global current_track_name, current_session_type_str, current_weather_str, player_car_index

    # struct PacketSessionData {
    #     PacketHeader    m_header;
    #     uint8           m_weather;
    #     int8            m_trackTemperature;
    #     int8            m_airTemperature;
    #     uint8           m_totalLaps;
    #     uint16          m_trackLength;
    #     uint8           m_sessionType;
    #     int8            m_trackId;
    #     ... (other fields not directly needed for now)
    # };
    # We need m_sessionUID and m_playerCarIndex from header first
    header = parse_packet_header(data)
    packet_format, _, _, _, _packet_id, session_uid, _, _, p_car_index, _ = header # _packet_id is unused here

    if packet_format != 2022: # Ensure we are processing F1 22 format
        # print(f"Ignoring packet with format {packet_format}")
        return

    # It's generally safer to update player_car_index from any packet's header if it's valid.
    # However, SessionPacket is a good primary source.
    if 0 <= p_car_index < 22: # Max 22 cars
        player_car_index = p_car_index

    # Unpack relevant fields from SessionData (after the header)
    # Fields: m_weather, m_trackTemperature, m_airTemperature, m_totalLaps, m_trackLength, m_sessionType, m_trackId
    session_data_format = '<BbbBHBb' # Corrected format based on F1 22 spec for these specific fields
    session_data_unpack_offset = PACKET_HEADER_SIZE
    # print(f"DEBUG: process_session_packet: session_data_format = {session_data_format}, offset = {session_data_unpack_offset}, data_len = {len(data)}") # Debug
    
    try:
        weather, _track_temp, _air_temp, _total_laps, _track_length, session_type, track_id = \
            struct.unpack_from(session_data_format, data, session_data_unpack_offset)
    except struct.error as e:
        print(f"Error unpacking session data: {e}. Data length: {len(data)}, file offset: {session_data_unpack_offset}, format: '{session_data_format}'")
        return


    # Session Management: Check for new session
    # A new session is identified by a change in m_sessionUID or m_sessionType.
    global _internal_last_processed_session_uid_for_id_generation, _internal_last_processed_session_type_for_id_generation
    if session_uid != _internal_last_processed_session_uid_for_id_generation or \
       session_type != _internal_last_processed_session_type_for_id_generation:
        current_session_id = str(uuid.uuid4())
        _internal_last_processed_session_uid_for_id_generation = session_uid
        _internal_last_processed_session_type_for_id_generation = session_type
        # Reset logged laps for the new session is handled in main loop
        print(f"New session detected or session type changed. New Session ID: {current_session_id}, Game SessionUID: {session_uid}, Game SessionType: {session_type}")
    
    current_track_name = get_track_name_str(track_id)
    current_session_type_str = get_session_type_str(session_type)
    current_weather_str = get_weather_str(weather)

    # print(f"Session Data: Track: {current_track_name}, Session: {current_session_type_str}, Weather: {current_weather_str}, PlayerCarIdx: {player_car_index}")


def process_participants_packet(data):
    """Processes PacketParticipantsData (Packet ID 4)."""
    global player_car_index, current_race_car

    if player_car_index is None:
        # print("Player car index not yet known, skipping participants data processing.")
        return

    header = parse_packet_header(data)
    packet_format, _, _, _, _packet_id, _, _, _, p_car_index_participants, _ = header # _packet_id unused
    
    if packet_format != 2022:
        return

    # Update player_car_index if it differs (e.g. if first packet wasn't session/lap)
    # and is valid.
    if 0 <= p_car_index_participants < 22:
        if player_car_index != p_car_index_participants :
            # print(f"Player car index updated from ParticipantsData header: {p_car_index_participants}")
            player_car_index = p_car_index_participants


    # struct ParticipantData {
    #     uint8      m_aiControlled;
    #     uint8      m_driverId;
    #     uint8      m_networkId;
    #     uint8      m_teamId;
    #     uint8      m_myTeam;
    #     uint8      m_raceNumber;
    #     uint8      m_nationality;
    #     char       m_name[48]; // UTF-8
    #     uint8      m_yourTelemetry;
    # };
    PARTICIPANT_DATA_ENTRY_FORMAT = '<BBBBBBB48sB' # Corrected: removed space, 7 B's total for leading uint8s
    # print(f"DEBUG: PARTICIPANT_DATA_ENTRY_FORMAT = {PARTICIPANT_DATA_ENTRY_FORMAT}") # Debug
    PARTICIPANT_DATA_ENTRY_SIZE = struct.calcsize(PARTICIPANT_DATA_ENTRY_FORMAT)

    # Participants packet specific data: m_numActiveCars (uint8)
    num_active_cars_offset = PACKET_HEADER_SIZE
    # print(f"DEBUG: process_participants_packet: num_active_cars_offset = {num_active_cars_offset}, data_len = {len(data)}, format for num_active_cars: <B") # Debug
    num_active_cars = struct.unpack_from('<B', data, num_active_cars_offset)[0]

    # Offset to the player's car participant data
    # m_participants[22] starts after m_numActiveCars
    participants_array_start_offset = num_active_cars_offset + struct.calcsize('<B')
    offset = participants_array_start_offset + (player_car_index * PARTICIPANT_DATA_ENTRY_SIZE)

    if offset + PARTICIPANT_DATA_ENTRY_SIZE > len(data):
        # print(f"Not enough data for player's participant data. Index: {player_car_index}, Offset: {offset}, Data len: {len(data)}")
        return
    
    # print(f"DEBUG: process_participants_packet: Unpacking participant with format = {PARTICIPANT_DATA_ENTRY_FORMAT}, offset = {offset}, data_len = {len(data)}") # Debug
    try:
        participant_data_tuple = struct.unpack_from(PARTICIPANT_DATA_ENTRY_FORMAT, data, offset)
    except struct.error as e:
        print(f"Error unpacking participant data for player car {player_car_index}: {e}")
        return

    _ai_controlled, _driver_id, _network_id, team_id, _my_team, _race_num, _nationality, _name_bytes, _your_telemetry = participant_data_tuple
    
    current_race_car = get_team_name_str(team_id)
    # Player name can also be extracted if needed: name = name_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
    # print(f"Participant Data: Player Car: {current_race_car} (Team ID: {team_id})")


# Store the last session ID that triggered a lap cache reset
_last_session_id_for_lap_reset_cache = None

def process_session_history_packet(data):
    """Processes PacketSessionHistoryData (Packet ID 11)."""
    global player_car_index, pending_lap_details, logged_laps_in_session, current_session_id

    if player_car_index is None or current_session_id is None:
        # print("Player car index or session ID not known for history processing.")
        return

    header = parse_packet_header(data)
    packet_format, _, _, _, packet_id, _session_uid_hist, _, _, history_car_idx, _ = header

    if packet_format != 2022 or packet_id != 11:
        return

    if history_car_idx != player_car_index:
        # This history packet is not for the player's car
        return

    try:
        _car_idx_payload, num_laps_in_history, _num_tyre_stints, _best_lap_num, _best_s1_lap, _best_s2_lap, _best_s3_lap = \
            struct.unpack_from(SESSION_HISTORY_LEAD_DATA_FORMAT, data, PACKET_HEADER_SIZE)
    except struct.error as e:
        print(f"Error unpacking session history lead data: {e}")
        return

    # print(f"DEBUG History: CarIdx_Payload: {_car_idx_payload}, PlayerCarIdx: {player_car_index}, NumLapsInHistoryPacket: {num_laps_in_history}")

    lap_history_array_start_offset = PACKET_HEADER_SIZE + SESSION_HISTORY_LEAD_DATA_SIZE
    
    keys_to_remove_from_pending = []

    for pending_key in list(pending_lap_details.keys()): # Iterate over a copy of keys
        pending_session_id, pending_completed_lap_num = pending_key
        
        if pending_session_id == current_session_id:
            history_lap_index = pending_completed_lap_num - 1 # Lap N is at index N-1

            # print(f"DEBUG History Check: PendingLap={pending_completed_lap_num}, HistIndex={history_lap_index}, NumLapsInHistoryPacket={num_laps_in_history}")

            if 0 <= history_lap_index < num_laps_in_history:
                offset_for_this_lap_history = lap_history_array_start_offset + (history_lap_index * LAP_HISTORY_ENTRY_SIZE)
                
                try:
                    lap_time_ms, s1_time_ms, s2_time_ms, s3_time_ms_direct, lap_valid_bit_flags = \
                        struct.unpack_from(LAP_HISTORY_ENTRY_FORMAT, data, offset_for_this_lap_history)
                    
                    # print(f"DEBUG History Packet - Matched Lap {pending_completed_lap_num} for car {history_car_idx}: ")
                    # print(f"  Raw Times MS: Total={lap_time_ms}, S1={s1_time_ms}, S2={s2_time_ms}, S3_direct={s3_time_ms_direct}, ValidFlags={lap_valid_bit_flags:#04x}")

                except struct.error as e:
                    print(f"Error unpacking lap history entry for lap {pending_completed_lap_num} (idx {history_lap_index}): {e}. Offset: {offset_for_this_lap_history}, Data len: {len(data)}")
                    continue 

                lap_details_base = pending_lap_details[pending_key]
                total_lap_time_sec = round(lap_time_ms / 1000.0, 3)
                s1_time_sec = round(s1_time_ms / 1000.0, 3)
                s2_time_sec = round(s2_time_ms / 1000.0, 3)
                
                s3_calculated_ms = lap_time_ms - (s1_time_ms + s2_time_ms)
                s3_final_time_sec = round(s3_calculated_ms / 1000.0, 3)

                if s3_final_time_sec < 0:
                    # print(f"Warning: Calculated S3 for lap {pending_completed_lap_num} is negative ({s3_final_time_sec}s).")
                    s3_direct_is_valid_sector = (lap_valid_bit_flags & 0x08) != 0 # Check bit 3 for S3 validity
                    if s3_direct_is_valid_sector and s3_time_ms_direct > 0:
                        s3_final_time_sec = round(s3_time_ms_direct / 1000.0, 3)
                        # print(f"  Using direct S3 from history: {s3_final_time_sec}s (raw: {s3_time_ms_direct}ms)")
                    else:
                        s3_final_time_sec = 0.000 
                        # print(f"  Fell back to S3 = 0.000s. Direct S3 ms: {s3_time_ms_direct}, S3 valid flag: {s3_direct_is_valid_sector}")
                
                is_valid_lap = (lap_valid_bit_flags & 0x01) != 0 # Bit 0 for overall lap validity

                # print(f"  Final Processed History for Lap {pending_completed_lap_num}: S1={s1_time_sec}, S2={s2_time_sec}, S3={s3_final_time_sec}, Total={total_lap_time_sec}, Valid={is_valid_lap}")

                log_entry = (
                    pending_session_id,
                    lap_details_base["session_type"],
                    lap_details_base["track_name"],
                    lap_details_base["race_car"],
                    lap_details_base["weather"],
                    pending_completed_lap_num,
                    s1_time_sec,
                    s2_time_sec,
                    s3_final_time_sec,
                    total_lap_time_sec,
                    is_valid_lap
                )

                log_lap_data_to_csv(log_entry)
                print(f"Logged completed lap {pending_completed_lap_num} for session {pending_session_id[:8]} from history.")
                
                keys_to_remove_from_pending.append(pending_key)
                logged_laps_in_session.add(pending_key) 
            # else:
                # print(f"DEBUG History: Lap {pending_completed_lap_num} (index {history_lap_index}) not found or out of range in this history packet (num_laps_in_history_packet: {num_laps_in_history}).")
        # else:
            # print(f"DEBUG History: Skipping pending key {pending_key} for session {pending_session_id} as it does not match current session {current_session_id}")

    for key_to_remove in keys_to_remove_from_pending:
        if key_to_remove in pending_lap_details:
            del pending_lap_details[key_to_remove]
            # print(f"DEBUG: Removed {key_to_remove} from pending_lap_details.")


def process_lap_data_packet(data):
    """Processes PacketLapData (Packet ID 2)."""
    global player_car_index, pending_lap_details, current_session_id
    global current_session_type_str, current_track_name_str, current_race_car, current_weather_str

    if player_car_index is None or current_session_id is None:
        # print("Player car index or session ID not yet known, skipping lap data processing.")
        return

    header = parse_packet_header(data)
    packet_format, _, _, _, packet_id, session_uid_lap, _, _, p_car_index_lap, _ = header

    if packet_format != 2022 or packet_id != 2:
        return
    
    # Update player_car_index if it was not set by session packet or differs, and is valid
    if 0 <= p_car_index_lap < 22:
        if player_car_index is None or player_car_index != p_car_index_lap:
            # print(f"Player car index updated from LapData header: {p_car_index_lap}")
            player_car_index = p_car_index_lap
    else: # Invalid player car index from this packet
        return

    # struct LapData (for one car) - simplified for what we need
    # uint32   m_lastLapTimeInMS;
    # uint32   m_currentLapTimeInMS;
    # ... (other fields)
    # uint8    m_currentLapNum;
    # ... (other fields)
    # uint8    m_currentLapInvalid; 
    # LAP_DATA_ENTRY_FORMAT refers to a single car's lap data structure
    # The full PacketLapData contains an array of these for 22 cars.

    # Corrected format for LapData for one car (simplified for necessary fields)
    # Based on F1 22 spec: lastLapTimeInMS (I), currentLapTimeInMS (I), sector1TimeInMS (H), sector2TimeInMS (H),
    # lapDistance (f), totalDistance (f), safetyCarDelta (f), carPosition (B), currentLapNum (B),
    # pitStatus (B), numPitStops (B), sector (B), currentLapInvalid (B), penalties (B), warnings (B), ...
    # We only need a few fields to trigger pending lap details.
    # Size of one LapData entry in PacketLapData.m_lapData[22] is 39 bytes for F1 2022 (based on my previous calc for the full struct)
    # For now, let's use a more robust offset calculation to get to player_car_index data.
    
    LAP_DATA_SINGLE_CAR_FORMAT = '<IIHHfffBBBBBBBBBBBBBHHB' # 2I, 2H, 3f, 13B, 2H, 1B
    LAP_DATA_SINGLE_CAR_SIZE = struct.calcsize(LAP_DATA_SINGLE_CAR_FORMAT)
    # print(f"DEBUG: LAP_DATA_SINGLE_CAR_FORMAT = '{LAP_DATA_SINGLE_CAR_FORMAT}', Calculated size: {LAP_DATA_SINGLE_CAR_SIZE}") # Expected 43

    # Format for the parts of LapData we care about for triggering: LastLapTime, CurrentLapNum
    # LastLapTime (uint32), CurrentLapTime (uint32), S1 (uint16), S2 (uint16), lapDistance (f), totalDistance(f), safetyCarDelta(f), carPosition(B), currentLapNum(B)
    # Offset of m_lastLapTimeInMS is 0 within the LapData struct.
    # Offset of m_currentLapNum is 25 within the LapData struct: I I H H f f f B B ... -> 4+4+2+2+4+4+4+1 = 25th byte (index 24)
    # So struct format to read up to currentLapNum is '<IIHHfffBB'
    # And we need lastLapTimeInMS and currentLapNum from that. 

    offset_to_player_lap_data = PACKET_HEADER_SIZE + (player_car_index * LAP_DATA_SINGLE_CAR_SIZE)
    
    try:
        # Fetch m_lastLapTimeInMS (at start of LapData) and m_currentLapNum (offset 25 within LapData)
        player_last_lap_time_ms, = struct.unpack_from('<I', data, offset_to_player_lap_data)
        player_current_lap_num, = struct.unpack_from('<B', data, offset_to_player_lap_data + 25) # Offset of m_currentLapNum within LapData struct
    except struct.error as e:
        print(f"Error unpacking specific lap data fields: {e}. Data length: {len(data)}, offset: {offset_to_player_lap_data}")
        return

    # print(f"DEBUG LapData: Car: {player_car_index}, LastLapTimeMS: {player_last_lap_time_ms}, CurrentLapNum: {player_current_lap_num}")

    if player_last_lap_time_ms > 0 and player_current_lap_num > 1: # Lap completed and it's not the very first lap starting
        completed_lap_number = player_current_lap_num - 1
        pending_key = (current_session_id, completed_lap_number)

        if pending_key not in pending_lap_details and pending_key not in logged_laps_in_session:
            # Store basic info needed for logging later, to be enriched by history packet
            pending_lap_details[pending_key] = {
                "session_type": current_session_type_str,
                "track_name": current_track_name,
                "race_car": current_race_car,
                "weather": current_weather_str
                # Lap number is part of the key
            }
            print(f"Lap {completed_lap_number} completed for session {current_session_id}. Stored in pending_lap_details. Waiting for history data.")
        # else: print(f"Lap {completed_lap_number} already pending or logged.")


def main():
    """Main function to listen for UDP packets and process them."""
    global current_session_id, player_car_index, logged_laps_in_session # Ensure logged_laps_in_session is recognized as global here too
    global _internal_last_processed_session_uid_for_id_generation, _internal_last_processed_session_type_for_id_generation # For session reset logic
    global _last_session_id_for_lap_reset_cache # Added missing global declaration

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except OSError as e:
        print(f"Error binding to UDP port {UDP_PORT}: {e}")
        print("Please ensure no other application is using this port and you have network permissions.")
        return

    print(f"Listening for F1 22 telemetry on UDP port {UDP_PORT}...")

    write_csv_header_if_needed()
    
    # State to prevent duplicate lap logging for the same lap number in the same session
    # This is a simple approach; a more robust one might involve checking the CSV itself
    # or handling game state transitions more carefully.
    # logged_laps_in_session = set() # MOVED to global scope

    # global current_session_id # This was redundant, current_session_id is already in the global list at the top of main

    try:
        while True:
            data, addr = sock.recvfrom(2048) # Buffer size, F1 packets are < 1500 bytes

            if not data or len(data) < PACKET_HEADER_SIZE:
                # print("Received an empty or too small packet.")
                continue

            header_data = parse_packet_header(data)
            packet_format = header_data[0]
            packet_id = header_data[4]
            # session_uid_from_header = header_data[5] # For session tracking
            p_car_idx_from_header = header_data[8]

            if packet_format != 2022: # F1 22 uses format 2022
                # print(f"Received packet with unsupported format: {packet_format}")
                continue
            
            # Always update player_car_index from any packet's header if it's valid (0-21)
            # This helps if the first packet isn't a session packet or if player index changes mid-session (e.g. spectator mode change)
            if 0 <= p_car_idx_from_header < 22:
                if player_car_index is None or player_car_index != p_car_idx_from_header:
                    # print(f"Player car index updated from general header: {p_car_idx_from_header} (was {player_car_index})")
                    player_car_index = p_car_idx_from_header


            if packet_id == 1: # Session Packet
                process_session_packet(data)
                # When a new session_id is generated by process_session_packet,
                # clear the logged_laps_in_session set.
                if current_session_id != _last_session_id_for_lap_reset_cache:
                    logged_laps_in_session.clear()
                    pending_lap_details.clear() # Clear pending laps for new session
                    _last_session_id_for_lap_reset_cache = current_session_id
                    # print(f"New session ID ({current_session_id[:8]}) detected in main loop, lap log cache and pending laps cleared.")


            elif packet_id == 2: # Lap Data Packet
                process_lap_data_packet(data)
            
            elif packet_id == 4: # Participants Packet
                process_participants_packet(data)
            
            elif packet_id == 11: # Session History Packet
                process_session_history_packet(data)

    except KeyboardInterrupt:
        print("\nLogger stopped by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        sock.close()
        print("Socket closed. Exiting.")

if __name__ == "__main__":
    main() 
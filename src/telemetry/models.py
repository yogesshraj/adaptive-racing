from ctypes import (
    Structure,
    c_uint8, c_int8,
    c_uint16, c_int16,
    c_uint32,
    c_uint64,
    c_float,
    Array,
)

class PacketHeader(Structure):
    """Header for all F1 22 UDP packets"""
    _pack_ = 1
    _fields_ = [
        ("m_packetFormat", c_uint16),          # 2022
        ("m_gameMajorVersion", c_uint8),       # Game major version - "X.00"
        ("m_gameMinorVersion", c_uint8),       # Game minor version - "1.XX"
        ("m_packetVersion", c_uint8),          # Version of this packet type
        ("m_packetId", c_uint8),               # Identifier for the packet type
        ("m_sessionUID", c_uint64),            # Unique identifier for the session
        ("m_sessionTime", c_float),            # Session timestamp
        ("m_frameIdentifier", c_uint32),       # Identifier for the frame the data was retrieved on
        ("m_playerCarIndex", c_uint8),         # Index of player's car in the array
        ("m_secondaryPlayerCarIndex", c_uint8) # Index of secondary player's car (split screen)
    ]

class CarTelemetryData(Structure):
    """Contains all telemetry data for a single car"""
    _pack_ = 1
    _fields_ = [
        ("m_speed", c_uint16),                    # Speed of car in kilometers per hour
        ("m_throttle", c_float),                  # Amount of throttle applied (0.0 to 1.0)
        ("m_steer", c_float),                     # Steering (-1.0 (full lock left) to 1.0 (full lock right))
        ("m_brake", c_float),                     # Amount of brake applied (0.0 to 1.0)
        ("m_clutch", c_uint8),                    # Amount of clutch applied (0 to 100)
        ("m_gear", c_int8),                       # Gear selected (1-8, N=0, R=-1)
        ("m_engineRPM", c_uint16),                # Engine RPM
        ("m_drs", c_uint8),                       # 0 = off, 1 = on
        ("m_revLightsPercent", c_uint8),          # Rev lights indicator (percentage)
        ("m_revLightsBitValue", c_uint16),        # Rev lights (bit 0 = leftmost LED, bit 14 = rightmost LED)
        ("m_brakesTemperature", c_uint16 * 4),    # Brakes temperature (celsius)
        ("m_tyresSurfaceTemperature", c_uint8 * 4), # Tyres surface temperature (celsius)
        ("m_tyresInnerTemperature", c_uint8 * 4), # Tyres inner temperature (celsius)
        ("m_engineTemperature", c_uint16),        # Engine temperature (celsius)
        ("m_tyresPressure", c_float * 4),         # Tyres pressure (PSI)
        ("m_surfaceType", c_uint8 * 4),           # Driving surface, see appendices
    ]

class PacketCarTelemetryData(Structure):
    """Contains telemetry data for all cars on track"""
    _pack_ = 1
    _fields_ = [
        ("m_header", PacketHeader),               # Header
        ("m_carTelemetryData", CarTelemetryData * 22),  # Telemetry data for all cars
        ("m_mfdPanelIndex", c_uint8),            # Index of MFD panel open
        ("m_mfdPanelIndexSecondaryPlayer", c_uint8),  # Index of MFD panel for secondary player
        ("m_suggestedGear", c_int8),             # Suggested gear for the player (1-8, 0 if no gear suggested)
    ]

class LapData(Structure):
    """Contains lap data for a single car"""
    _pack_ = 1
    _fields_ = [
        ("m_lastLapTimeInMS", c_uint32),      # Last lap time in milliseconds
        ("m_currentLapTimeInMS", c_uint32),   # Current time around the lap in milliseconds
        ("m_sector1TimeInMS", c_uint16),      # Sector 1 time in milliseconds
        ("m_sector2TimeInMS", c_uint16),      # Sector 2 time in milliseconds
        ("m_lapDistance", c_float),           # Distance vehicle is around current lap in metres
        ("m_totalDistance", c_float),         # Total distance travelled in session in metres
        ("m_safetyCarDelta", c_float),        # Delta in seconds for safety car
        ("m_carPosition", c_uint8),           # Car race position
        ("m_currentLapNum", c_uint8),         # Current lap number
        ("m_pitStatus", c_uint8),             # 0 = none, 1 = pitting, 2 = in pit area
        ("m_numPitStops", c_uint8),           # Number of pit stops taken in this race
        ("m_sector", c_uint8),                # 0 = sector1, 1 = sector2, 2 = sector3
        ("m_currentLapInvalid", c_uint8),     # Current lap invalid - 0 = valid, 1 = invalid
        ("m_penalties", c_uint8),             # Accumulated time penalties in seconds
        ("m_warnings", c_uint8),              # Accumulated number of warnings issued
        ("m_numUnservedDriveThroughPens", c_uint8),  # Number of unserved drive through penalties
        ("m_numUnservedStopGoPens", c_uint8),     # Number of unserved stop go penalties
        ("m_gridPosition", c_uint8),          # Grid position the vehicle started the race in
        ("m_driverStatus", c_uint8),          # Status of driver - 0 = in garage, 1 = flying lap
                                             # 2 = in lap, 3 = out lap, 4 = on track
        ("m_resultStatus", c_uint8),          # Result status - 0 = invalid, 1 = inactive, 2 = active
                                             # 3 = finished, 4 = didnotfinish, 5 = disqualified
                                             # 6 = not classified, 7 = retired
        ("m_pitLaneTimerActive", c_uint8),    # Pit lane timing, 0 = inactive, 1 = active
        ("m_pitLaneTimeInLaneInMS", c_uint16), # If active, the current time spent in the pit lane in ms
        ("m_pitStopTimerInMS", c_uint16),     # Time of the actual pit stop in ms
        ("m_pitStopShouldServePen", c_uint8), # Whether the car should serve a penalty at this stop
    ]

class PacketLapData(Structure):
    """Contains lap data for all cars on track"""
    _pack_ = 1
    _fields_ = [
        ("m_header", PacketHeader),           # Header
        ("m_lapData", LapData * 22),          # Lap data for all cars on track
        ("m_timeTrialPBCarIdx", c_uint8),     # Index of Personal Best car in time trial
        ("m_timeTrialRivalCarIdx", c_uint8),  # Index of Rival car in time trial
    ]

class PacketSessionData(Structure):
    """Contains details about the current session"""
    _pack_ = 1
    _fields_ = [
        ("m_header", PacketHeader),               # Header
        ("m_weather", c_uint8),                   # Weather - 0 = clear, 1 = light cloud, 2 = overcast
                                                 # 3 = light rain, 4 = heavy rain, 5 = storm
        ("m_trackTemperature", c_int8),          # Track temp. in degrees celsius
        ("m_airTemperature", c_int8),            # Air temp. in degrees celsius
        ("m_totalLaps", c_uint8),                # Total number of laps in this race
        ("m_trackLength", c_uint16),             # Track length in metres
        ("m_sessionType", c_uint8),              # 0 = unknown, 1 = P1, 2 = P2, 3 = P3, 4 = Short P
                                                # 5 = Q1, 6 = Q2, 7 = Q3, 8 = Short Q, 9 = OSQ
                                                # 10 = R, 11 = R2, 12 = Time Trial
        ("m_trackId", c_int8),                   # -1 for unknown, see appendix
        ("m_formula", c_uint8),                  # Formula, 0 = F1 Modern, 1 = F1 Classic, 2 = F2,
                                                # 3 = F1 Generic
        ("m_sessionTimeLeft", c_uint16),         # Time left in session in seconds
        ("m_sessionDuration", c_uint16),         # Session duration in seconds
        ("m_pitSpeedLimit", c_uint8),           # Pit speed limit in kilometres per hour
        ("m_gamePaused", c_uint8),              # Whether the game is paused
        ("m_isSpectating", c_uint8),            # Whether the player is spectating
        ("m_spectatorCarIndex", c_uint8),       # Index of the car being spectated
        ("m_sliProNativeSupport", c_uint8),     # SLI Pro support, 0 = inactive, 1 = active
        ("m_numMarshalZones", c_uint8),         # Number of marshal zones to follow
        ("m_marshalZones", c_uint8 * 21 * 4),   # List of marshal zones
        ("m_safetyCarStatus", c_uint8),         # 0 = no safety car, 1 = full safety car
                                               # 2 = virtual safety car
        ("m_networkGame", c_uint8),             # 0 = offline, 1 = online
        ("m_numWeatherForecastSamples", c_uint8), # Number of weather samples to follow
        ("m_weatherForecastSamples", c_uint8 * 56), # Array of weather forecast samples
        ("m_forecastAccuracy", c_uint8),        # 0 = Perfect, 1 = Approximate
        ("m_aiDifficulty", c_uint8),            # AI Difficulty rating – 0-110
        ("m_seasonLinkIdentifier", c_uint32),   # Identifier for season - persists across saves
        ("m_weekendLinkIdentifier", c_uint32),  # Identifier for weekend - persists across saves
        ("m_sessionLinkIdentifier", c_uint32),  # Identifier for session - persists across saves
        ("m_pitStopWindowIdealLap", c_uint8),   # Ideal lap to pit on for current strategy
        ("m_pitStopWindowLatestLap", c_uint8),  # Latest lap to pit on for current strategy
        ("m_pitStopRejoinPosition", c_uint8),   # Predicted position to rejoin at
        ("m_steeringAssist", c_uint8),          # 0 = off, 1 = on
        ("m_brakingAssist", c_uint8),           # 0 = off, 1 = low, 2 = medium, 3 = high
        ("m_gearboxAssist", c_uint8),           # 1 = manual, 2 = manual & suggested gear, 3 = auto
        ("m_pitAssist", c_uint8),               # 0 = off, 1 = on
        ("m_pitReleaseAssist", c_uint8),        # 0 = off, 1 = on
        ("m_ERSAssist", c_uint8),               # 0 = off, 1 = on
        ("m_DRSAssist", c_uint8),               # 0 = off, 1 = on
        ("m_dynamicRacingLine", c_uint8),       # 0 = off, 1 = corners only, 2 = full
        ("m_dynamicRacingLineType", c_uint8),   # 0 = 2D, 1 = 3D
    ]

# Track IDs
TRACK_IDS = {
    0: "Melbourne",
    1: "Paul Ricard",
    2: "Shanghai",
    3: "Sakhir",
    4: "Catalunya",
    5: "Monaco",
    6: "Montreal",
    7: "Silverstone",
    8: "Hockenheim",
    9: "Hungaroring",
    10: "Spa",
    11: "Monza",
    12: "Singapore",
    13: "Suzuka",
    14: "Abu Dhabi",
    15: "Texas",
    16: "Brazil",
    17: "Austria",
    18: "Sochi",
    19: "Mexico",
    20: "Baku",
    21: "Sakhir Short",
    22: "Silverstone Short",
    23: "Texas Short",
    24: "Suzuka Short",
    25: "Hanoi",
    26: "Zandvoort",
    27: "Imola",
    28: "Portimão",
    29: "Jeddah",
    30: "Miami",
}

# Packet IDs
PACKET_IDS = {
    'MOTION': 0,
    'SESSION': 1,
    'LAP_DATA': 2,
    'EVENT': 3,
    'PARTICIPANTS': 4,
    'CAR_SETUPS': 5,
    'CAR_TELEMETRY': 6,
    'CAR_STATUS': 7,
    'FINAL_CLASSIFICATION': 8,
    'LOBBY_INFO': 9,
    'CAR_DAMAGE': 10,
    'SESSION_HISTORY': 11,
}

# Mapping of packet IDs to their corresponding structure
PACKET_STRUCTURES = {
    PACKET_IDS['CAR_TELEMETRY']: PacketCarTelemetryData,
    PACKET_IDS['LAP_DATA']: PacketLapData,
    PACKET_IDS['SESSION']: PacketSessionData,
} 
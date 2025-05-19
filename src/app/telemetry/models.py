from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from ctypes import Structure, c_uint16, c_float, c_uint8, c_int8

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

@dataclass
class TelemetryData:
    """Class for storing F1 22 telemetry data"""
    speed: int = 0  # Speed in km/h
    rpm: int = 0    # Engine RPM
    gear: int = 0   # Current gear (-1 = reverse, 0 = neutral, 1-8 = gears)
    throttle: float = 0.0  # Throttle input (0.0 to 1.0)
    brake: float = 0.0     # Brake input (0.0 to 1.0)
    steer: float = 0.0     # Steering input (-1.0 to 1.0)
    drs: int = 0    # DRS status (0 = off, 1 = on)
    lap_time: int = 0  # in milliseconds
    sector1_time: int = 0  # in milliseconds
    sector2_time: int = 0  # in milliseconds
    sector3_time: int = 0  # in milliseconds
    current_sector: int = 0  # 0-based sector number (0, 1, 2)
    lap_distance: float = 0.0  # Distance around current lap in meters
    tyresSurfaceTemperature: List[int] = None  # Surface temperature of each tire [FL, FR, RL, RR]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.tyresSurfaceTemperature is None:
            self.tyresSurfaceTemperature = [0, 0, 0, 0]
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @classmethod
    def from_car_telemetry(cls, car_telemetry: CarTelemetryData) -> 'TelemetryData':
        """Create TelemetryData from CarTelemetryData structure"""
        return cls(
            speed=car_telemetry.m_speed,
            rpm=car_telemetry.m_engineRPM,
            gear=car_telemetry.m_gear,
            throttle=car_telemetry.m_throttle,
            brake=car_telemetry.m_brake,
            steer=car_telemetry.m_steer,
            drs=car_telemetry.m_drs
        )

    def to_dict(self) -> dict:
        """Convert telemetry data to dictionary"""
        return {
            'speed': self.speed,
            'rpm': self.rpm,
            'gear': self.gear,
            'throttle': self.throttle,
            'brake': self.brake,
            'steer': self.steer,
            'drs': self.drs
        } 
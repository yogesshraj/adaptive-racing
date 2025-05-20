import socket
import struct
from dataclasses import dataclass
from typing import Dict, Any, Optional
import threading
import time
import binascii

# F1 22 Packet IDs
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

@dataclass
class TelemetryData:
    speed: float = 0.0          # Speed in km/h
    engine_rpm: float = 0.0     # Engine RPM
    throttle: float = 0.0       # Throttle application (0.0 to 1.0)
    brake: float = 0.0          # Brake application (0.0 to 1.0)
    steering: float = 0.0       # Steering (-1.0 (full lock left) to 1.0 (full lock right))
    gear: int = 0               # Gear (0=N, 1-8=Forward, -1=R)
    current_lap_time: float = 0.0  # Current lap time in seconds

class PacketHeader:
    SIZE = 24  # Try smaller header size
    
    def __init__(self, data: bytes):
        try:
            # Print first 32 bytes of data for analysis
            hex_data = binascii.hexlify(data[:32]).decode()
            print(f"\nFirst 32 bytes in hex:")
            # Print in groups of 4 bytes for better readability
            for i in range(0, len(hex_data), 8):
                print(f"{hex_data[i:i+8]}", end=" ")
            print("\n")
            
            # Try different header formats
            # Format 1: Simple header
            self.packet_format = struct.unpack('<H', data[0:2])[0]
            self.packet_id = data[2]
            print(f"Format: {self.packet_format}, ID: {self.packet_id}")
            
            # Try to find float values that make sense
            for i in range(0, len(data)-4, 4):
                try:
                    val = struct.unpack('<f', data[i:i+4])[0]
                    if 0 <= val <= 400:  # Possible speed
                        print(f"Possible speed at offset {i}: {val:.1f} km/h")
                    elif 0 <= val <= 15000:  # Possible RPM
                        print(f"Possible RPM at offset {i}: {val:.0f}")
                    elif 0 <= val <= 1.0:  # Possible throttle/brake
                        print(f"Possible throttle/brake at offset {i}: {val:.2f}")
                except:
                    pass
                
                # Also try as unsigned short (for speed)
                try:
                    val = struct.unpack('<H', data[i:i+2])[0]
                    if 0 <= val <= 400:  # Possible speed
                        print(f"Possible speed (short) at offset {i}: {val} km/h")
                except:
                    pass
            
            self.player_car_index = 0  # Default to first car
            
        except Exception as e:
            print(f"Error parsing header: {e}")
            print(f"Raw data length: {len(data)}")
            raise

class F1TelemetryListener:
    def __init__(self, host: str = '127.0.0.1', port: int = 20777):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False
        self.latest_data = TelemetryData()
        self._lock = threading.Lock()
        self._packet_counts = {}  # Track packet types we receive

    def start(self):
        """Start listening for telemetry data."""
        try:
            self.socket.bind((self.host, self.port))
            print(f"Successfully bound to {self.host}:{self.port}")
            print("Waiting for F1 22 telemetry data...")
            self.running = True
            self.listener_thread = threading.Thread(target=self._listen)
            self.listener_thread.daemon = True
            self.listener_thread.start()
        except Exception as e:
            print(f"Error starting listener: {e}")
            raise

    def stop(self):
        """Stop listening for telemetry data."""
        self.running = False
        self.socket.close()

    def _listen(self):
        """Main listener loop for telemetry data."""
        last_stats_time = time.time()
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
                packet_id = data[2] if len(data) > 2 else None
                
                # Update packet statistics
                if packet_id is not None:
                    self._packet_counts[packet_id] = self._packet_counts.get(packet_id, 0) + 1
                
                # Print statistics every 5 seconds
                current_time = time.time()
                if current_time - last_stats_time >= 5:
                    print("\nPacket Statistics:")
                    for pid, count in self._packet_counts.items():
                        print(f"Packet ID {pid}: {count} packets")
                    print("")
                    last_stats_time = current_time
                
                self._process_telemetry(data)
            except Exception as e:
                print(f"Error receiving data: {e}")
                time.sleep(0.1)

    def _process_telemetry(self, data: bytes):
        """Process the raw telemetry data from F1 22."""
        try:
            if len(data) < 16:  # Minimum size we expect
                return

            header = PacketHeader(data)
            
            # For now, we're just analyzing the data format
            # Once we understand the format, we'll implement proper parsing

        except Exception as e:
            print(f"Error processing telemetry data: {e}")

    def get_current_telemetry(self) -> TelemetryData:
        """Get the latest telemetry data."""
        with self._lock:
            return self.latest_data 
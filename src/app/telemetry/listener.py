import socket
import threading
import struct
from typing import Callable
from ctypes import sizeof, create_string_buffer, memmove, addressof
from .models import TelemetryData, CarTelemetryData

class TelemetryListener:
    def __init__(self, host='127.0.0.1', port=20777):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.callback = None
        self.thread = None
        self.packet_count = 0

    def start(self, callback: Callable[[TelemetryData], None]):
        """Start listening for telemetry data"""
        if self.running:
            return

        self.callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._listen)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop listening for telemetry data"""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.thread:
            self.thread.join()
            self.thread = None

    def _listen(self):
        """Listen for telemetry data in a loop"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))

        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
                if data:
                    self.packet_count += 1
                    telemetry = self._parse_telemetry(data)
                    if telemetry and self.callback:
                        self.callback(telemetry)
            except Exception as e:
                print(f"Error receiving telemetry: {e}")
                continue

    def _parse_telemetry(self, data: bytes) -> TelemetryData:
        """Parse raw telemetry data into TelemetryData object"""
        try:
            # Check packet type
            if len(data) < 24:
                return None
            packet_id = struct.unpack_from('<B', data, 5)[0]
            if packet_id != 6:
                # Not a Car Telemetry packet
                return None

            min_packet_size = 24 + (22 * 60)
            if len(data) < min_packet_size:
                return None

            player_car_index = struct.unpack_from('<B', data, 21)[0]
            car_data_offset = 24 + player_car_index * 60

            car_buffer = create_string_buffer(60)
            memmove(addressof(car_buffer), data[car_data_offset:], 60)
            car_telemetry = CarTelemetryData.from_buffer(car_buffer)
            telemetry = TelemetryData.from_car_telemetry(car_telemetry)

            return telemetry
        except Exception as e:
            print(f"Error parsing telemetry: {e}")
            return None 
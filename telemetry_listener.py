import socket
import struct
import threading
from typing import Callable, Dict, Optional
from ctypes import sizeof, create_string_buffer, memmove, addressof, Structure

from data_models import PacketHeader, PACKET_STRUCTURES
from config import UDP_IP, UDP_PORT

class TelemetryListener:
    def __init__(self, ip: str = UDP_IP, port: int = UDP_PORT):
        """Initialize the telemetry listener with the given IP and port"""
        self.ip = ip
        self.port = port
        self.socket = None
        self.running = False
        self.thread = None
        self.callbacks: Dict[int, Callable] = {}  # Packet ID -> callback function
        self._setup_socket()

    def _setup_socket(self):
        """Set up the UDP socket for receiving telemetry data"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.ip, self.port))
        self.socket.settimeout(1.0)  # 1 second timeout for clean shutdown

    def register_callback(self, packet_id: int, callback: Callable):
        """Register a callback function for a specific packet type"""
        self.callbacks[packet_id] = callback

    def start(self):
        """Start listening for telemetry data in a separate thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop)
        self.thread.daemon = True  # Thread will be killed when main program exits
        self.thread.start()

    def stop(self):
        """Stop listening for telemetry data"""
        self.running = False
        if self.thread:
            self.thread.join()
        if self.socket:
            self.socket.close()

    def _listen_loop(self):
        """Main loop for receiving and processing telemetry packets"""
        header_buffer = create_string_buffer(sizeof(PacketHeader))
        
        while self.running:
            try:
                # First, peek at the header to determine packet type
                data, addr = self.socket.recvfrom(2048)  # Buffer size should be larger than largest packet
                if not data:
                    continue

                # Copy header data into our header buffer
                memmove(addressof(header_buffer), data, sizeof(PacketHeader))
                header = PacketHeader.from_buffer(header_buffer)

                # Get the appropriate structure for this packet type
                packet_structure = PACKET_STRUCTURES.get(header.m_packetId)
                if not packet_structure:
                    continue  # Skip unknown packet types

                # Create a buffer for the full packet and copy data into it
                packet_buffer = create_string_buffer(sizeof(packet_structure))
                memmove(addressof(packet_buffer), data, min(len(data), sizeof(packet_structure)))
                
                # Create the full packet structure
                packet = packet_structure.from_buffer(packet_buffer)

                # Call the registered callback for this packet type
                callback = self.callbacks.get(header.m_packetId)
                if callback:
                    callback(packet)

            except socket.timeout:
                continue  # Just continue on timeout
            except Exception as e:
                print(f"Error processing telemetry packet: {e}")
                continue  # Continue on other errors to maintain the connection

    def __del__(self):
        """Cleanup when the object is destroyed"""
        self.stop() 
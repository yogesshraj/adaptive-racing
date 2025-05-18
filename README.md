# Advanced Adaptive AI Race Engineer and Training Suite

## Phase 1: Real-time Telemetry Data Acquisition and Basic Visualization for F1 22

This application connects to F1 22, captures real-time telemetry data, and displays key metrics in a simple interface.

## Setup

### 1. F1 22 Game Configuration
   - Launch F1 22.
   - Navigate to **Game Options -> Settings -> Telemetry Settings**.
   - Set **UDP Telemetry** to **On**.
   - Set **UDP Broadcast Mode** to **Off** (unless sending to multiple devices on your network, for initial setup, Off is simpler).
   - Set **UDP IP Address** to `127.0.0.1` (if running this application on the same PC as the game). If running on a different device, set it to the IP address of that device.
   - Set **Port** to `20777` (or your preferred port, ensure it matches `config.py`).
   - Set **UDP Send Rate** to `20Hz` or `60Hz` (higher rates provide smoother data but increase network/CPU load).
   - Set **UDP Format** to `2022`.

### 2. Python Environment
   - Ensure you have Python 3.8+ installed.
   - It is recommended to use a virtual environment:
     ```bash
     python -m venv venv
     source venv/bin/activate  # On Windows: venv\Scripts\activate
     ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

### 3. Running the Application
   ```bash
   python main.py
   ```

## Project Structure
```
/adaptive_racing_telemetry
|-- /data_models.py         # Defines ctypes structures for F1 22 UDP packets
|-- /telemetry_listener.py  # Handles UDP socket communication and packet reception
|-- /packet_parser.py       # Parses raw UDP data into structured Python objects
|-- /gui.py                 # Tkinter based GUI for displaying telemetry
|-- /main.py                # Main application script
|-- /config.py              # Configuration settings (port, IP)
|-- /utils.py               # Utility functions (e.g., data normalization)
|-- README.md               # This file
|-- requirements.txt        # Python package dependencies
```
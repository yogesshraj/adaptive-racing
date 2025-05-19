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
     pip install -r requirements/base.txt  # For basic usage
     pip install -r requirements/dev.txt   # For development
     pip install -r requirements/test.txt  # For running tests
     ```

### 3. Running the Application
   ```bash
   python main.py
   ```

## Project Structure
```
adaptive-racing/
├── src/                           # Source code
│   ├── telemetry/                 # Telemetry related modules
│   │   ├── __init__.py
│   │   ├── listener.py           # UDP listener
│   │   └── models.py             # Data models
│   ├── analysis/                  # Analysis modules
│   │   ├── __init__.py
│   │   ├── lap_analyzer.py       # Lap timing and analysis
│   │   └── data_logger.py        # Data logging and processing
│   ├── visualization/             # Visualization components
│   │   ├── __init__.py
│   │   ├── gui.py               # Main GUI interface
│   │   └── plots.py             # Data visualization
│   └── utils/                     # Utility functions
│       └── __init__.py
├── tests/                         # Test files
│   ├── test_telemetry/
│   ├── test_analysis/
│   └── test_visualization/
├── data/                          # Data storage
│   ├── raw/                      # Raw telemetry logs
│   └── processed/                # Processed data
├── docs/                          # Documentation
│   ├── api/
│   └── user_guide/
├── config/                        # Configuration files
│   └── default_config.py         # Default configuration
├── scripts/                       # Utility scripts
├── requirements/                  # Dependencies
│   ├── base.txt                  # Basic requirements
│   ├── dev.txt                   # Development requirements
│   └── test.txt                  # Testing requirements
├── main.py                        # Application entry point
└── README.md                      # This file
```
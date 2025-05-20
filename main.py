import sys
import os

# Add the project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from src.visualization.gui import TelemetryDisplay

def main():
    """Main entry point for the F1 22 Telemetry Application."""
    app = QApplication(sys.argv)
    window = TelemetryDisplay()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 
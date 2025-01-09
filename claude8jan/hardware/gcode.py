import serial
import serial.tools.list_ports
import threading
import time

class GCode:
    def __init__(self, baudrate=250000, feedrate=2000, acceleration=5, jerk=1):
        self.baud_rate = baudrate
        self.serial_port = None
        self.printer_on_serial = None
        self.listener_thread = None
        self.connected = False
        self.current_position = {'X': 0, 'Y': 0, 'Z': 0}
        self.feedrate = feedrate
        self.acceleration = acceleration
        self.jerk = jerk
        self.waiting_for_response = False
        self.last_response = None
        self.connect_to_printer()

    def find_serial_port(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'USB' in port.description:
                try:
                    ser = serial.Serial(port.device, self.baud_rate, timeout=1)
                    ser.close()
                    return port.device
                except serial.SerialException:
                    print(f"Failed to connect on {port.device}")
        return None

    # ... [Rest of the GCode class methods]
    # Note: For brevity, the remaining methods are not shown here but would be included
    # in the actual file, including all the methods from the original GCode class.
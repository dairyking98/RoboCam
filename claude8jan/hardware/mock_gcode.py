"""
Simplified GCode implementation using mock hardware for testing
"""
import threading
import time
from .mock_hardware import MockSerial, MockPrinter

class MockGCode:
    def __init__(self, baudrate=250000, feedrate=2000, acceleration=5, jerk=1):
        """Initialize the Mock GCode class with simulated hardware"""
        self.baud_rate = baudrate
        self.printer_on_serial = None
        self.listener_thread = None
        self.connected = False
        self.current_position = {'X': 0, 'Y': 0, 'Z': 0}
        self.feedrate = feedrate
        self.acceleration = acceleration
        self.jerk = jerk
        self.waiting_for_response = False
        self.last_response = None
        self.mock_printer = MockPrinter()
        self.connect_to_printer()

    def find_serial_port(self):
        """Simulate finding a serial port"""
        return "COM_MOCK"

    def connect_to_printer(self):
        """Establish connection to the mock printer"""
        try:
            self.printer_on_serial = MockSerial("COM_MOCK", self.baud_rate, timeout=1)
            self.connected = True
            print(f"Connected to mock printer on COM_MOCK at {self.baud_rate} baud")
            
            self.listener_thread = threading.Thread(target=self.listen_to_printer_output)
            self.listener_thread.daemon = True
            self.listener_thread.start()
            
            # Wait for initialization
            time.sleep(0.5)
            
            # Initial commands
            self.set_jerk(self.jerk)
            self.set_acceleration(self.acceleration)
            
        except Exception as e:
            print(f"Failed to establish mock connection: {e}")
            self.connected = False

    def listen_to_printer_output(self):
        """Listen for data from the mock printer"""
        while self.connected:
            if self.printer_on_serial and self.printer_on_serial.in_waiting > 0:
                response = self.printer_on_serial.readline().decode('utf-8').strip()
                if self.waiting_for_response:
                    self.last_response = response
                else:
                    print(f"Printer: {response}")
            time.sleep(0.01)

    def send_gcode(self, command):
        """Send a G-code command to the mock printer"""
        if not self.printer_on_serial:
            print("No printer connected")
            return False

        try:
            self.printer_on_serial.reset_input_buffer()
            self.last_response = None
            self.waiting_for_response = True
            
            print(f"Sending: {command}")
            self.printer_on_serial.write(command.encode('utf-8') + b'\n')
            
            # Process command in mock printer
            response = self.mock_printer.process_command(command)
            self.last_response = response
            
            # Update current position from mock printer
            self.current_position = self.mock_printer.position.copy()
            
            self.waiting_for_response = False
            return True
            
        except Exception as e:
            self.waiting_for_response = False
            print(f"Error sending command {command}: {e}")
            return False

    def move_xyz(self, x, y, z):
        """Move the XYZ axes to the provided coordinates"""
        x = max(0, x)  # Prevent negative X
        y = max(0, y)  # Prevent negative Y
        z = max(0, z)  # Prevent negative Z
        command = f"G1 X{x} Y{y} Z{z} F{self.feedrate}"
        self.send_gcode(command)

    def home_all_axes(self):
        """Home all axes"""
        if self.send_gcode("G28"):
            print("Homing completed, positions reset to 0")
            self.current_position = {'X': 0, 'Y': 0, 'Z': 0}
            self.send_gcode(f"G1 X0 Y0 Z0 F{self.feedrate}")
        else:
            print("Homing failed or timed out")

    def set_feedrate(self, feedrate):
        """Set the feedrate"""
        self.feedrate = feedrate

    def set_acceleration(self, acceleration):
        """Set the acceleration"""
        self.acceleration = acceleration
        self.send_gcode(f"M201 X{acceleration} Y{acceleration} Z{acceleration}")

    def set_jerk(self, jerk):
        """Set the jerk"""
        self.jerk = jerk
        self.send_gcode(f"M205 X{jerk} Y{jerk} Z{jerk}")

    def enable_steppers(self):
        """Enable steppers"""
        self.send_gcode("M17")

    def disable_steppers(self):
        """Disable steppers"""
        self.send_gcode("M84")

    def close_connection(self):
        """Close the mock connection"""
        if self.printer_on_serial:
            print("Closing mock serial connection...")
            self.connected = False
            self.printer_on_serial.close()
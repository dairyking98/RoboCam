import serial
import serial.tools.list_ports
import threading
import time
from typing import Dict, Optional, Union, List
from ..config import GCODE_SETTINGS
import logging

class GCode:
    def __init__(self, baudrate=250000, feedrate=2000, acceleration=5, jerk=1):
        """Initialize the GCode class with default baudrate and G-code settings."""
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        self.baud_rate = baudrate
        self.serial_port = None
        self.printer_on_serial = None
        self.listener_thread = None
        self.connected = False
        self.current_position = {'X': 0, 'Y': 0, 'Z': 0}
        self.target_position = {'X': 0, 'Y': 0, 'Z': 0}
        self.feedrate = feedrate
        self.acceleration = acceleration
        self.jerk = jerk
        self.waiting_for_response = False
        self.last_response = None
        self._is_moving = False
        self.debug = False
        self.connect_to_printer()

    def set_debug(self, debug: bool):
        """Set the debug flag."""
        self.debug = debug
        if self.debug:
            print("DEBUG: Debug mode enabled for GCode class")

    def find_serial_port(self) -> Optional[str]:
        """Find available serial ports and select the correct one."""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'USB' in port.description:
                try:
                    ser = serial.Serial(port.device, self.baud_rate, timeout=1)
                    ser.close()
                    return port.device
                except serial.SerialException:
                    if self.debug:
                        print(f"DEBUG: Failed to connect on {port.device}")
        return None

    def connect_to_printer(self) -> bool:
        """Establish connection to the 3D printer."""
        serial_port = self.find_serial_port()
        if serial_port:
            try:
                self.printer_on_serial = serial.Serial(serial_port, self.baud_rate, timeout=1)
                self.connected = True
                if self.debug:
                    print(f"DEBUG: Connected to printer on {serial_port} at {self.baud_rate} baud.")
                
                self.listener_thread = threading.Thread(target=self.listen_to_printer_output)
                self.listener_thread.daemon = True
                self.listener_thread.start()
                
                time.sleep(2)  # Wait for printer initialization
                
                # Initial settings
                self.set_jerk(self.jerk)
                self.set_acceleration(self.acceleration)
                return True
                
            except serial.SerialException as e:
                if self.debug:
                    print(f"DEBUG: Failed to establish connection: {e}")
                self.connected = False
                return False
        else:
            if self.debug:
                print("DEBUG: No valid serial port found.")
            self.connected = False
            return False

    def listen_to_printer_output(self):
        """Listen for data coming from the printer."""
        while self.connected:
            if self.printer_on_serial and self.printer_on_serial.in_waiting > 0:
                try:
                    response = self.printer_on_serial.readline().decode('utf-8', errors='ignore').strip()
                    if self.waiting_for_response:
                        self.last_response = response
                    elif self.debug:
                        print(f"DEBUG: Printer: {response}")
                except UnicodeDecodeError as e:
                    if self.debug:
                        print(f"DEBUG: UnicodeDecodeError: Failed to decode data from printer: {e}")
            time.sleep(0.01)

    def send_gcode(self, command: str) -> bool:
        """Send a G-code command and wait for acknowledgment."""
        if not self.printer_on_serial:
            if self.debug:
                print("DEBUG: No printer connected")
            return False

        try:
            # Clear buffers
            self.printer_on_serial.reset_input_buffer()
            self.last_response = None
            self.waiting_for_response = True
            
            # Send command
            if self.debug:
                print(f"DEBUG: Sending: {command}")
            self.printer_on_serial.write(f"{command}\n".encode('utf-8'))
            
            # Set timeout based on command type
            if command.startswith('G28'):
                timeout = GCODE_SETTINGS['TIMEOUT']['HOMING']
            else:
                timeout = GCODE_SETTINGS['TIMEOUT']['GENERAL']
            
            # Wait for response
            start_time = time.time()
            while (time.time() - start_time) < timeout:
                if self.last_response is not None:
                    response = self.last_response
                    self.last_response = None
                    
                    if 'ok' in response.lower():
                        self.waiting_for_response = False
                        return True
                    elif 'error' in response.lower():
                        if self.debug:
                            print(f"DEBUG: Error from printer: {response}")
                        self.waiting_for_response = False
                        return False
                time.sleep(0.01)
            
            if self.debug:
                print("DEBUG: Command timed out")
            self.waiting_for_response = False
            return False
            
        except Exception as e:
            if self.debug:
                print(f"DEBUG: Error sending command {command}: {e}")
            self.waiting_for_response = False
            return False

    def move_xyz(self, x: float, y: float, z: float) -> bool:
        """Move to absolute XYZ coordinates."""
        x = max(0, x)
        y = max(0, y)
        z = max(0, z)
        command = f"G1 X{x} Y{y} Z{z} F{self.feedrate}"
        self.target_position = {'X': x, 'Y': y, 'Z': z}
        if self.debug:
            print(f"DEBUG: Moving to X:{x} Y:{y} Z:{z}")
        if self.send_gcode(command):
            # Wait for movement to complete
            while self.is_moving():
                time.sleep(0.1)
            self.current_position = {'X': x, 'Y': y, 'Z': z}
            return True
        return False
        
    def wait_for_movement_completion(self):
        if self.debug:
            print("DEBUG: Waiting for movement completion")
        self.send_gcode("M400")  # Wait for all moves to finish
        response = self._get_printer_response()
        if response and 'ok' in response.lower():
            if self.debug:
                print("DEBUG: Movement completed")
            return True
        return False

    def home_all_axes(self) -> bool:
        """Home all axes and reset positions to 0."""
        if self.debug:
            print("DEBUG: Homing all axes")
        if self.send_gcode("G28"):
            if self.debug:
                print("DEBUG: Homing completed, positions reset to 0.")
            self.current_position = {'X': 0, 'Y': 0, 'Z': 0}
            self.send_gcode(f"G1 X0 Y0 Z0 F{self.feedrate}")
            return True
        return False

    def set_feedrate(self, feedrate: int):
        """Set the feedrate (speed)."""
        self.feedrate = feedrate
        if self.debug:
            print(f"DEBUG: Feedrate set to {feedrate}")

    def set_acceleration(self, acceleration: int) -> bool:
        """Set the maximum acceleration."""
        self.acceleration = acceleration
        command = f"M201 X{acceleration} Y{acceleration} Z{acceleration} E{acceleration}"
        if self.debug:
            print(f"DEBUG: Setting acceleration to {acceleration}")
        return self.send_gcode(command)

    def set_jerk(self, jerk: int) -> bool:
        """Set the jerk (speed change rate)."""
        self.jerk = jerk
        command = f"M205 X{jerk} Y{jerk} Z{jerk}"
        if self.debug:
            print(f"DEBUG: Setting jerk to {jerk}")
        return self.send_gcode(command)

    def enable_steppers(self) -> bool:
        """Enable stepper motors."""
        if self.debug:
            print("DEBUG: Enabling steppers")
        return self.send_gcode("M17")

    def disable_steppers(self) -> bool:
        """Disable stepper motors."""
        if self.debug:
            print("DEBUG: Disabling steppers")
        return self.send_gcode("M84")

    def close_connection(self):
        """Close the serial connection and stop the listener thread."""
        if self.printer_on_serial:
            if self.debug:
                print("DEBUG: Closing serial connection...")
            self.connected = False
            time.sleep(0.1)  # Give listener thread time to exit
            self.printer_on_serial.close()
            self.printer_on_serial = None
            
    def get_position(self) -> Dict[str, float]:
        """Retrieve the current position of the printer."""
        return self.current_position

    def __del__(self):
        """Destructor to ensure proper cleanup."""
        self.close_connection()
        
    def is_connected(self) -> bool:
        """Check if the printer is connected."""
        return self.connected

    def is_moving(self) -> bool:
        """Check if the printer is currently moving."""
        if not self._is_moving:
            return False

        if self.debug:
            print("DEBUG: Checking if printer is moving")

        # Send M400 to wait for all moves to finish
        self.send_gcode("M400")

        # Request current position
        current_pos = self.get_current_position()
        
        # Compare current position with target position
        if current_pos is None:
            if self.debug:
                print("DEBUG: Couldn't get current position, assuming still moving")
            return True  # Assume still moving if we couldn't get the position
        
        tolerance = 0.1  # Set a small tolerance for float comparison
        for axis in ['X', 'Y', 'Z']:
            if abs(current_pos[axis] - self.target_position[axis]) > tolerance:
                if self.debug:
                    print(f"DEBUG: Still moving - {axis} axis not at target")
                return True

        if self.debug:
            print("DEBUG: Movement completed")
        self._is_moving = False
        return False

    def get_current_position(self) -> Optional[Dict[str, float]]:
        """Get the current position of the printer using M114."""
        if self.debug:
            print("DEBUG: Getting current position")
        if self.send_gcode("M114"):
            response = self._get_printer_response()
            if response:
                try:
                    # Parse the M114 response
                    parts = response.split()
                    pos = {}
                    for part in parts:
                        if ':' in part:
                            axis, value = part.split(':')
                            if axis in ['X', 'Y', 'Z']:
                                pos[axis] = float(value)
                    if len(pos) == 3:
                        self.current_position = pos
                        if self.debug:
                            print(f"DEBUG: Current position: {pos}")
                        return pos
                except ValueError:
                    if self.debug:
                        print(f"DEBUG: Failed to parse position from response: {response}")
        return None

    def _get_printer_response(self) -> Optional[str]:
        """Get a response from the printer."""
        if self.printer_on_serial and self.printer_on_serial.in_waiting > 0:
            try:
                response = self.printer_on_serial.readline().decode('utf-8', errors='ignore').strip()
                if self.debug:
                    print(f"DEBUG: Received response: {response}")
                return response
            except UnicodeDecodeError as e:
                if self.debug:
                    print(f"DEBUG: UnicodeDecodeError: Failed to decode data from printer: {e}")
        return None

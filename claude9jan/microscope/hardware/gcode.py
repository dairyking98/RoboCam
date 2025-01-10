# microscope_control/hardware/gcode.py
"""
GCode controller module for microscope control system.
Handles communication with the 3D printer via serial connection.
"""

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
        self.feedrate = feedrate
        self.acceleration = acceleration
        self.jerk = jerk
        self.waiting_for_response = False
        self.last_response = None
        self.connect_to_printer()

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
                    print(f"Failed to connect on {port.device}")
        return None

    def connect_to_printer(self) -> bool:
        """Establish connection to the 3D printer."""
        serial_port = self.find_serial_port()
        if serial_port:
            try:
                self.printer_on_serial = serial.Serial(serial_port, self.baud_rate, timeout=1)
                self.connected = True
                print(f"Connected to printer on {serial_port} at {self.baud_rate} baud.")
                
                self.listener_thread = threading.Thread(target=self.listen_to_printer_output)
                self.listener_thread.daemon = True
                self.listener_thread.start()
                
                time.sleep(2)  # Wait for printer initialization
                
                # Initial settings
                self.set_jerk(self.jerk)
                self.set_acceleration(self.acceleration)
                return True
                
            except serial.SerialException as e:
                print(f"Failed to establish connection: {e}")
                self.connected = False
                return False
        else:
            print("No valid serial port found.")
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
                    else:
                        print(f"Printer: {response}")
                except UnicodeDecodeError as e:
                    print(f"UnicodeDecodeError: Failed to decode data from printer: {e}")
            time.sleep(0.01)

    def send_gcode(self, command: str) -> bool:
        """Send a G-code command and wait for acknowledgment."""
        if not self.printer_on_serial:
            self.logger.error("No printer connected")
            return False

        try:
            # Clear buffers
            self.printer_on_serial.reset_input_buffer()
            self.last_response = None
            self.waiting_for_response = True
            
            # Send command
            self.logger.debug(f"Sending: {command}")
            self.printer_on_serial.write(f"{command}\n".encode('utf-8'))
            
            # Set timeout based on command type
            if command.startswith('G28'):
                timeout = GCODE_SETTINGS['TIMEOUT']['HOMING']
            else:
                timeout = GCODE_SETTINGS['TIMEOUT']['GENERAL']
            
            # Wait for response
            start_time = time.time()
            while (time.time() - start_time) < timeout:  # Fixed comparison here
                if self.last_response is not None:
                    response = self.last_response
                    self.last_response = None
                    
                    if 'ok' in response.lower():
                        self.waiting_for_response = False
                        return True
                    elif 'error' in response.lower():
                        self.logger.error(f"Error from printer: {response}")
                        self.waiting_for_response = False
                        return False
                time.sleep(0.01)
            
            self.logger.error("Command timed out")
            self.waiting_for_response = False
            return False
            
        except Exception as e:
            self.logger.error(f"Error sending command {command}: {e}")
            self.waiting_for_response = False
            return False

    def move_xyz(self, x: float, y: float, z: float) -> bool:
        """Move to absolute XYZ coordinates."""
        x = max(0, x)
        y = max(0, y)
        z = max(0, z)
        command = f"G1 X{x} Y{y} Z{z} F{self.feedrate}"
        if self.send_gcode(command):
            self.current_position = {'X': x, 'Y': y, 'Z': z}
            return True
        return False

    def home_all_axes(self) -> bool:
        """Home all axes and reset positions to 0."""
        if self.send_gcode("G28"):
            print("Homing completed, positions reset to 0.")
            self.current_position = {'X': 0, 'Y': 0, 'Z': 0}
            self.send_gcode(f"G1 X0 Y0 Z0 F{self.feedrate}")
            return True
        return False

    def set_feedrate(self, feedrate: int):
        """Set the feedrate (speed)."""
        self.feedrate = feedrate

    def set_acceleration(self, acceleration: int) -> bool:
        """Set the maximum acceleration."""
        self.acceleration = acceleration
        command = f"M201 X{acceleration} Y{acceleration} Z{acceleration} E{acceleration}"
        return self.send_gcode(command)

    def set_jerk(self, jerk: int) -> bool:
        """Set the jerk (speed change rate)."""
        self.jerk = jerk
        command = f"M205 X{jerk} Y{jerk} Z{jerk}"
        return self.send_gcode(command)

    def enable_steppers(self) -> bool:
        """Enable stepper motors."""
        return self.send_gcode("M17")

    def disable_steppers(self) -> bool:
        """Disable stepper motors."""
        return self.send_gcode("M84")

    def close_connection(self):
        """Close the serial connection and stop the listener thread."""
        if self.printer_on_serial:
            print("Closing serial connection...")
            self.connected = False
            time.sleep(0.1)  # Give listener thread time to exit
            self.printer_on_serial.close()
            self.printer_on_serial = None

    def __del__(self):
        """Destructor to ensure proper cleanup."""
        self.close_connection()

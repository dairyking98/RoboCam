import serial
import serial.tools.list_ports
import threading
import time

class GCode:
    def __init__(self, baudrate=250000, feedrate=2000, acceleration=5, jerk=1):
        """Initialize the GCode class with default baudrate and G-code settings."""
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
        self.connect_to_printer()  # Connect on initialization

    def find_serial_port(self):
        """Find available serial ports and select the correct one."""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'USB' in port.description:  # Check if it's a USB serial port
                try:
                    # Try opening the port to verify it works
                    ser = serial.Serial(port.device, self.baud_rate, timeout=1)
                    ser.close()  # Close the port if it connects successfully
                    return port.device
                except serial.SerialException:
                    print(f"Failed to connect on {port.device}")
        return None

    def connect_to_printer(self):
        """Establish connection to the 3D printer via serial."""
        serial_port = self.find_serial_port()
        if serial_port:
            try:
                self.printer_on_serial = serial.Serial(serial_port, self.baud_rate, timeout=1)
                self.connected = True
                print(f"Connected to printer on {serial_port} at {self.baud_rate} baud.")
                
                # Start the listener thread immediately
                print("Starting listener thread")
                self.listener_thread = threading.Thread(target=self.listen_to_printer_output)
                self.listener_thread.daemon = True
                self.listener_thread.start()
                print("Listener thread started")
                
                # Wait for the printer to initialize
                time.sleep(2)
                
                # Initial commands
                self.set_jerk(self.jerk)
                self.set_acceleration(self.acceleration)
                
            except serial.SerialException:
                print("Failed to establish connection.")
                self.connected = False
        else:
            print("No valid serial port found.")
            self.connected = False

    def listen_to_printer_output(self):
        """Listen for data coming from the printer."""
        print("Listener thread started running")
        while self.connected:
            if self.printer_on_serial and self.printer_on_serial.in_waiting > 0:
                try:
                    response = self.printer_on_serial.readline().decode('utf-8', errors='ignore').strip()
                    print(f"Raw response: '{response}'")
                    if self.waiting_for_response:
                        print(f"Storing response: '{response}'")
                        self.last_response = response
                    else:
                        print(f"Printing response: '{response}'")
                        print(f"Printer: {response}")
                except UnicodeDecodeError as e:
                    print(f"UnicodeDecodeError: Failed to decode data from printer: {e}")
            time.sleep(0.01)
        print("Listener thread exiting")

    def send_gcode(self, command):
        """Send a G-code command and wait for acknowledgment."""
        if not self.printer_on_serial:
            print("No printer connected.")
            return False

        try:
            # Clear any pending data
            self.printer_on_serial.reset_input_buffer()
            self.last_response = None
            
            # Set waiting flag before sending command
            self.waiting_for_response = True
            print(f"Set waiting_for_response to True")
            
            # Send the command
            print(f"Sending: {command}")
            self.printer_on_serial.write((command + '\n').encode('utf-8'))
            
            # Set timeout based on command
            timeout = 30 if command.startswith('G28') else 10  # 30 seconds for homing, 10 for others
            
            # Wait for acknowledgment with timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.last_response is not None:
                    response = self.last_response
                    print(f"Got response: '{response}'")
                    self.last_response = None  # Clear the response
                    
                    # Check for acknowledgment
                    if 'ok' in response.lower():
                        print("Found 'ok' in response")
                        self.waiting_for_response = False
                        return True
                    elif 'error' in response.lower():
                        print(f"Error response from printer: {response}")
                        self.waiting_for_response = False
                        return False
                time.sleep(0.01)
            
            print(f"{timeout}s timeout occurred")
            self.waiting_for_response = False
            print("Command timed out - no acknowledgment received")
            return False
            
        except Exception as e:
            self.waiting_for_response = False
            print(f"Error sending command {command}: {e}")
            return False

    def move_xyz(self, x, y, z):
        """Move the XYZ axes to the provided coordinates, ensuring no negative values."""
        x = max(0, x)  # Prevent negative X
        y = max(0, y)  # Prevent negative Y
        z = max(0, z)  # Prevent negative Z
        command = f"G1 X{x} Y{y} Z{z} F{self.feedrate}"  # Append feedrate to movement command
        self.send_gcode(command)

        # Update current position after movement
        self.current_position['X'] = x
        self.current_position['Y'] = y
        self.current_position['Z'] = z

    def home_all_axes(self):
        """Home all axes and reset current positions to 0."""
        if self.send_gcode("G28"):  # If homing is successful
            print("Homing completed, positions reset to 0.")
            self.current_position = {'X': 0, 'Y': 0, 'Z': 0}
            
            # Add move to 0,0,0 after successful homing
            self.send_gcode(f"G1 X0 Y0 Z0 F{self.feedrate}")
            print("Moved to home position (0,0,0).")
        else:
            print("Homing failed or timed out.")

    def set_feedrate(self, feedrate):
        """Set the feedrate (speed)."""
        self.feedrate = feedrate

    def set_acceleration(self, acceleration):
        """Set the maximum acceleration."""
        self.acceleration = acceleration
        command = f"M201 X{acceleration} Y{acceleration} Z{acceleration} E{acceleration}"
        self.send_gcode(command)

    def set_jerk(self, jerk):
        """Set the jerk (speed change rate)."""
        self.jerk = jerk
        command = f"M205 X{jerk} Y{jerk} Z{jerk}"
        self.send_gcode(command)

    def enable_steppers(self):
        """Enable steppers."""
        self.send_gcode("M17")

    def disable_steppers(self):
        """Disable steppers."""
        self.send_gcode("M84")

    def close_connection(self):
        """Close the serial connection and stop the listener thread."""
        if self.printer_on_serial:
            print("Closing serial connection...")
            self.connected = False
            # Give the listener thread time to exit
            time.sleep(0.5)
            self.printer_on_serial.close()
            self.printer_on_serial = None

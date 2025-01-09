import tkinter as tk
from tkinter import messagebox
from tkinter import Toplevel
from tkinter import filedialog
import threading
import time
import cv2
from picamera2 import Picamera2
import numpy as np
import serial
import serial.tools.list_ports
import os

# Creation Date         6 Jan 2025
# Last Updated          8 Jan 2025
# Author                Leonard Chau
"""TO DO
CameraGUI
        issues with turn off and on
CameraOverlayGUI
        size, rotation, zoom, quality
        circle, crosshair, size, thickness, color
SnakePathGUI
        locate 4 points
        Store point coordinatesS
        GeneratePath and store
        Cell readout (A1, A8, F8, F1)
ExperimentGUI
        traverse GeneratePath and capture and store images, file naming scheme
        cell readout
ZStackGUI
        height, interval, file naming scheme"""

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
        self.waiting_for_response = False  # Add flag for response handling
        self.last_response = None  # Add variable to store last response
        self.connect_to_printer()

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
                print("Debug - Starting listener thread")
                self.listener_thread = threading.Thread(target=self.listen_to_printer_output)
                self.listener_thread.daemon = True
                self.listener_thread.start()
                print("Debug - Listener thread started")
                
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
        print("Debug - Listener thread started running")  # Debug line
        while self.connected:
            if self.printer_on_serial and self.printer_on_serial.in_waiting > 0:
                try:
                    response = self.printer_on_serial.readline().decode('utf-8', errors='ignore').strip()
                    print(f"Debug - Listener got raw response: '{response}'")  # Debug line
                    if self.waiting_for_response:
                        print(f"Debug - Storing response: '{response}'")
                        self.last_response = response
                    else:
                        print(f"Debug - Printing response: '{response}'")
                        print(f"Printer: {response}")
                except UnicodeDecodeError as e:
                    print(f"UnicodeDecodeError: Failed to decode data from printer: {e}")
            time.sleep(0.01)
        print("Debug - Listener thread exiting")  # Debug line

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
            print("Debug - Set waiting_for_response to True")  # Debug output
            
            # Send the command
            print(f"Sending: {command}")
            self.printer_on_serial.write((command + '\n').encode('utf-8'))
            
            # Set timeout based on command
            timeout = 30 if command.startswith('G28') else 10  # 30 seconds for homing, 10 for others
            
            # Wait for acknowledgment with timeout
            start_time = time.time()
            while time.time() - start_time < timeout:  # Use variable timeout
                if self.last_response is not None:
                    response = self.last_response
                    print(f"Debug - Got response: '{response}'")  # Debug output
                    self.last_response = None  # Clear the response
                    
                    # Check for acknowledgment
                    if 'ok' in response.lower():
                        print("Debug - Found 'ok' in response")  # Debug output
                        self.waiting_for_response = False
                        return True
                    elif 'error' in response.lower():
                        print(f"Error response from printer: {response}")
                        self.waiting_for_response = False
                        return False
                time.sleep(0.01)
            
            print(f"Debug - {timeout}s timeout occurred")  # Debug output
            self.waiting_for_response = False
            print("Command timed out - no acknowledgment received")
            return False
            
        except Exception as e:
            self.waiting_for_response = False
            print(f"Error sending command {command}: {e}")
            return False

    def wait_for_initial_response(self):
        """Wait for initial response from printer."""
        print("Waiting for initial response from printer...")
        # Clear any existing data
        self.printer_on_serial.reset_input_buffer()
        
        start_time = time.time()
        while time.time() - start_time < 10:  # 10 second timeout
            if self.printer_on_serial.in_waiting:
                try:
                    response = self.printer_on_serial.readline().decode('utf-8', errors='ignore').strip()
                    print(f"Received from printer: {response}")
                    
                    # Keep reading even if we get SD init fail or other messages
                    if any(word in response.lower() for word in ['ok', 'start']):
                        print("Printer is ready, continuing...")
                        # Start the listener thread
                        self.listener_thread = threading.Thread(target=self.listen_to_printer_output)
                        self.listener_thread.daemon = True
                        self.listener_thread.start()
                        return True
                        
                except UnicodeDecodeError as e:
                    print(f"Error reading from printer: {e}")
                    continue
            time.sleep(0.1)
        return False
    
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
            
class Camera:
    def __init__(self):
        self.capture = cv2.VideoCapture(0)  # Initialize the camera (0 is usually the default camera)

        if not self.capture.isOpened():
            raise Exception("Could not open video device")

    def get_frame(self):
        """Get a frame from the camera."""
        ret, frame = self.capture.read()  # Capture frame from the camera
        if not ret:
            raise Exception("Failed to grab frame")
        return frame

    def release(self):
        """Release the camera when done."""
        self.capture.release()


class GCodeGUI:
    def __init__(self, root, gcode):
        """Initialize the GUI class."""
        self.root = root
        self.gcode = gcode
        
        self.root.title("GCode Control")

        # Create frame for controls
        self.frame = tk.Frame(self.root)
        self.frame.pack(padx=10, pady=10)

        # XYZ Coordinates Entry
        self.x_label = tk.Label(self.frame, text="X:")
        self.x_label.grid(row=0, column=0, padx=5, pady=5)

        self.x_entry = tk.Entry(self.frame)
        self.x_entry.grid(row=0, column=1, padx=5, pady=5)
        self.x_entry.insert(0, str(self.gcode.current_position['X']))  # Default value

        self.y_label = tk.Label(self.frame, text="Y:")
        self.y_label.grid(row=1, column=0, padx=5, pady=5)

        self.y_entry = tk.Entry(self.frame)
        self.y_entry.grid(row=1, column=1, padx=5, pady=5)
        self.y_entry.insert(0, str(self.gcode.current_position['Y']))  # Default value

        self.z_label = tk.Label(self.frame, text="Z:")
        self.z_label.grid(row=2, column=0, padx=5, pady=5)

        self.z_entry = tk.Entry(self.frame)
        self.z_entry.grid(row=2, column=1, padx=5, pady=5)
        self.z_entry.insert(0, str(self.gcode.current_position['Z']))  # Default value

        # Send Absolute Button
        self.send_button = tk.Button(self.frame, text="Send Absolute Coordinates", command=self.send_to_printer)
        self.send_button.grid(row=3, column=0, columnspan=2, pady=10)

        # Step Size Radio Buttons for XYZ Increment
        self.step_size = tk.DoubleVar(value=1.0)  # Default to 1.0 mm

        self.step_size_01 = tk.Radiobutton(self.frame, text="0.1 mm", variable=self.step_size, value=0.1)
        self.step_size_01.grid(row=4, column=0, padx=5, pady=5)

        self.step_size_1 = tk.Radiobutton(self.frame, text="1 mm", variable=self.step_size, value=1.0)
        self.step_size_1.grid(row=4, column=1, padx=5, pady=5)

        self.step_size_10 = tk.Radiobutton(self.frame, text="10 mm", variable=self.step_size, value=10.0)
        self.step_size_10.grid(row=4, column=2, padx=5, pady=5)

        # Move X, Y, Z Buttons (incremental)
        self.move_buttons_frame = tk.Frame(self.frame)
        self.move_buttons_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.move_x_plus = tk.Button(self.move_buttons_frame, text="X+", command=lambda: self.move_increment('X', 1))
        self.move_x_plus.grid(row=1, column=0, padx=5)

        self.move_x_minus = tk.Button(self.move_buttons_frame, text="X-", command=lambda: self.move_increment('X', -1))
        self.move_x_minus.grid(row=1, column=2, padx=5)

        self.move_y_plus = tk.Button(self.move_buttons_frame, text="Y+", command=lambda: self.move_increment('Y', 1))
        self.move_y_plus.grid(row=0, column=1, padx=5)

        self.move_y_minus = tk.Button(self.move_buttons_frame, text="Y-", command=lambda: self.move_increment('Y', -1))
        self.move_y_minus.grid(row=2, column=1, padx=5)

        self.move_z_plus = tk.Button(self.move_buttons_frame, text="Z+", command=lambda: self.move_increment('Z', 1))
        self.move_z_plus.grid(row=2, column=0, padx=5)

        self.move_z_minus = tk.Button(self.move_buttons_frame, text="Z-", command=lambda: self.move_increment('Z', -1))
        self.move_z_minus.grid(row=2, column=2, padx=5)

        # Home, Enable, Disable Steppers Buttons
        self.home_button = tk.Button(self.frame, text="Home All Axes", command=self.home_axes)
        self.home_button.grid(row=6, column=0, pady=10)

        self.enable_steppers_button = tk.Button(self.frame, text="Enable Steppers", command=self.enable_steppers)
        self.enable_steppers_button.grid(row=6, column=1, pady=10)

        self.disable_steppers_button = tk.Button(self.frame, text="Disable Steppers", command=self.disable_steppers)
        self.disable_steppers_button.grid(row=7, column=0, pady=10)

        # Feedrate, Acceleration, Jerk input fields
        self.feedrate_label = tk.Label(self.frame, text="Feedrate (mm/min):")
        self.feedrate_label.grid(row=9, column=0, padx=5, pady=5)

        self.feedrate_entry = tk.Entry(self.frame)
        self.feedrate_entry.grid(row=9, column=1, padx=5, pady=5)
        self.feedrate_entry.insert(0, str(self.gcode.feedrate))  # Default to 200

        self.acceleration_label = tk.Label(self.frame, text="Acceleration (mm/sÂ²):")
        self.acceleration_label.grid(row=10, column=0, padx=5, pady=5)

        self.acceleration_entry = tk.Entry(self.frame)
        self.acceleration_entry.grid(row=10, column=1, padx=5, pady=5)
        self.acceleration_entry.insert(0, str(self.gcode.acceleration))  # Default to 5

        self.jerk_label = tk.Label(self.frame, text="Jerk (mm/s):")
        self.jerk_label.grid(row=11, column=0, padx=5, pady=5)

        self.jerk_entry = tk.Entry(self.frame)
        self.jerk_entry.grid(row=11, column=1, padx=5, pady=5)
        self.jerk_entry.insert(0, str(self.gcode.jerk))  # Default to 5

        # Apply button for feedrate, acceleration, and jerk
        self.apply_button = tk.Button(self.frame, text="Apply Settings", command=self.apply_settings)
        self.apply_button.grid(row=12, column=0, columnspan=2, pady=10)

        # Handle the close window event (when the X button is pressed)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def move_increment(self, axis, direction):
        """Increment or decrement the specified axis by the given amount."""
        step_size = self.step_size.get()  # Get the currently selected step size from the radio buttons
        increment = step_size * direction  # Apply the direction (positive or negative)

        # Calculate the new position, ensuring it's non-negative
        new_position = self.gcode.current_position[axis] + increment
        new_position = max(0, new_position)  # Prevent negative positions

        # Move the axis
        if axis == 'X':
            self.gcode.move_xyz(new_position, self.gcode.current_position['Y'], self.gcode.current_position['Z'])
        elif axis == 'Y':
            self.gcode.move_xyz(self.gcode.current_position['X'], new_position, self.gcode.current_position['Z'])
        elif axis == 'Z':
            self.gcode.move_xyz(self.gcode.current_position['X'], self.gcode.current_position['Y'], new_position)

        # After movement, update the entry fields with the new position
        self.x_entry.delete(0, tk.END)
        self.x_entry.insert(0, str(self.gcode.current_position['X']))

        self.y_entry.delete(0, tk.END)
        self.y_entry.insert(0, str(self.gcode.current_position['Y']))

        self.z_entry.delete(0, tk.END)
        self.z_entry.insert(0, str(self.gcode.current_position['Z']))

    def home_axes(self):
        """Send home command to printer."""
        self.gcode.home_all_axes()
        # Reset the XYZ entries to 0 after homing
        self.x_entry.delete(0, tk.END)
        self.y_entry.delete(0, tk.END)
        self.z_entry.delete(0, tk.END)
        self.x_entry.insert(0, "0")
        self.y_entry.insert(0, "0")
        self.z_entry.insert(0, "0")

    def send_to_printer(self):
        """Send the absolute coordinates to the printer."""
        try:
            x = float(self.x_entry.get())
            y = float(self.y_entry.get())
            z = float(self.z_entry.get())
            self.gcode.move_xyz(x, y, z)
        except ValueError:
            print("Invalid coordinates!")

    def enable_steppers(self):
        """Enable the stepper motors."""
        self.gcode.enable_steppers()

    def disable_steppers(self):
        """Disable the stepper motors."""
        self.gcode.disable_steppers()

    def apply_settings(self):
        """Apply the feedrate, acceleration, and jerk settings."""
        try:
            feedrate = float(self.feedrate_entry.get())
            acceleration = float(self.acceleration_entry.get())
            jerk = float(self.jerk_entry.get())
            self.gcode.set_feedrate(feedrate)
            self.gcode.set_acceleration(acceleration)
            self.gcode.set_jerk(jerk)
        except ValueError:
            print("Invalid values for settings!")

    def on_close(self):
        """Handle the window close event (when the X button is pressed)."""
        print("Closing application...")
        self.gcode.disable_steppers()  # Disable steppers
        self.gcode.close_connection()  # Close serial connection
        #self.root.quit()  # Exit the Tkinter main loop

class CameraGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Camera Preview")
        
        # Set initial window size
        self.root.geometry("1000x600")  # Width x Height
        
        # Create main frames
        self.preview_frame = tk.Frame(self.root)
        self.preview_frame.pack(side=tk.LEFT, padx=10, pady=10, expand=True)
        
        self.controls_frame = tk.Frame(self.root)
        self.controls_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.Y)

        # Initialize camera settings
        self.rotation = tk.IntVar(value=0)
        self.zoom = tk.DoubleVar(value=1.0)
        self.overlay_type = tk.StringVar(value="none")
        self.overlay_color = tk.StringVar(value="red")
        self.overlay_size = tk.IntVar(value=100)
        self.overlay_thickness = tk.IntVar(value=2)
        
        # Create preview label with fixed size
        self.image_label = tk.Label(self.preview_frame, width=640, height=480)
        self.image_label.pack(expand=True)
        
        # Add control panels
        self.create_camera_controls()
        self.create_overlay_controls()
        
        # Initialize camera and start preview
        self.picam2 = None
        self.running = False
        self.start_camera_preview()
        
        # Bind window closing event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_camera_controls(self):
        """Create camera control panel"""
        camera_frame = tk.LabelFrame(self.controls_frame, text="Camera Settings")
        camera_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Rotation control
        tk.Label(camera_frame, text="Rotation:").pack(anchor=tk.W)
        rotations = [0, 90, 180, 270]
        for r in rotations:
            tk.Radiobutton(camera_frame, text=f"{r} deg", 
                          variable=self.rotation, value=r).pack(anchor=tk.W)
        
        # Zoom control
        tk.Label(camera_frame, text="Zoom:").pack(anchor=tk.W)
        zoom_scale = tk.Scale(camera_frame, from_=1.0, to=4.0, 
                            resolution=0.1, orient=tk.HORIZONTAL,
                            variable=self.zoom)
        zoom_scale.pack(fill=tk.X)

    def create_overlay_controls(self):
        """Create overlay control panel"""
        overlay_frame = tk.LabelFrame(self.controls_frame, text="Overlay Settings")
        overlay_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Overlay type selection
        tk.Label(overlay_frame, text="Overlays:").pack(anchor=tk.W)
        self.crosshair_enabled = tk.BooleanVar(value=False)
        self.circle_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(overlay_frame, text="Crosshair", 
                       variable=self.crosshair_enabled).pack(anchor=tk.W)
        tk.Checkbutton(overlay_frame, text="Circle", 
                       variable=self.circle_enabled).pack(anchor=tk.W)
        
        # Color selection
        tk.Label(overlay_frame, text="Color:").pack(anchor=tk.W)
        colors = ["red", "green", "blue", "yellow", "white"]
        color_menu = tk.OptionMenu(overlay_frame, self.overlay_color, *colors)
        color_menu.pack(fill=tk.X)
        
        # Circle size slider
        tk.Label(overlay_frame, text="Circle Size:").pack(anchor=tk.W)
        circle_size_slider = tk.Scale(overlay_frame, from_=100, to=500, 
                                      orient=tk.HORIZONTAL, 
                                      variable=self.overlay_size)
        circle_size_slider.pack(fill=tk.X)
        
        # Thickness control
        tk.Label(overlay_frame, text="Thickness:").pack(anchor=tk.W)
        thickness_scale = tk.Scale(overlay_frame, from_=1, to=5, 
                                    orient=tk.HORIZONTAL,
                                    variable=self.overlay_thickness)
        thickness_scale.pack(fill=tk.X)

        
    def draw_overlay(self, frame):
        """Draw overlay on the frame"""
        height, width = frame.shape[:2]
        center_x = width // 2
        center_y = height // 2

        # Validate circle size input
        try:
            size = int(self.overlay_size.get())
        except ValueError:
            size = 100  # Default size if invalid input

        thickness = self.overlay_thickness.get()
        
        # Convert color name to BGR
        color_map = {
            "blue": (0, 0, 255),
            "green": (0, 255, 0),
            "red": (255, 0, 0),
            "yellow": (255, 255, 0),
            "white": (255, 255, 255)
        }
        color = color_map[self.overlay_color.get()]
        
        if self.crosshair_enabled.get():
            # Draw crosshair to maximum size
            cv2.line(frame, (0, center_y), (width, center_y), color, thickness)  # Horizontal line
            cv2.line(frame, (center_x, 0), (center_x, height), color, thickness)  # Vertical line
                
        if self.circle_enabled.get():
            # Draw circle
            cv2.circle(frame, (center_x, center_y), size // 2, color, thickness)
            
        return frame




    def apply_transformations(self, frame):
        """Apply rotation and zoom to frame"""
        # Apply rotation
        if self.rotation.get() != 0:
            rows, cols = frame.shape[:2]
            matrix = cv2.getRotationMatrix2D((cols/2, rows/2), self.rotation.get(), 1)
            frame = cv2.warpAffine(frame, matrix, (cols, rows))
        
        # Apply zoom
        if self.zoom.get() != 1.0:
            rows, cols = frame.shape[:2]
            zoom = self.zoom.get()
            crop_size = (int(cols/zoom), int(rows/zoom))
            x = (cols - crop_size[0]) // 2
            y = (rows - crop_size[1]) // 2
            frame = frame[y:y+crop_size[1], x:x+crop_size[0]]
            frame = cv2.resize(frame, (cols, rows))
            
        return frame

    def start_camera_preview(self):
        """Initialize the camera and start the preview."""
        if self.picam2 is None:
            try:
                # Initialize Picamera2 and configure it
                self.picam2 = Picamera2()
                picam2_config = self.picam2.create_preview_configuration(main={"size": (640, 480)})
                self.picam2.configure(picam2_config)
                self.picam2.start()
                self.running = True
                print("Camera started.")
                self.update_frame()
            except Exception as e:
                print(f"Error starting camera: {e}")
                if self.picam2:
                    self.picam2.close()
                    self.picam2 = None
                self.running = False

    def update_frame(self):
        """Update the image on the label."""
        if self.running and self.picam2:
            try:
                # Capture frame
                frame = self.picam2.capture_array("main")
                
                # Apply transformations
                frame = self.apply_transformations(frame)
                
                # Draw overlay
                frame = self.draw_overlay(frame)
                
                # Convert to RGB for tkinter
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert to PhotoImage
                photo = tk.PhotoImage(data=cv2.imencode('.ppm', frame)[1].tobytes())
                
                # Update the preview label
                self.image_label.configure(image=photo)
                self.image_label.image = photo
                
                # Schedule next update
                self.root.after(10, self.update_frame)
            except Exception as e:
                print(f"Error updating frame: {e}")
                self.running = False

    def stop(self):
        """Stop the camera when closing the GUI."""
        self.running = False
        if self.picam2 is not None:
            try:
                self.picam2.stop()
                self.picam2.close()
                self.picam2 = None
                print("Camera stopped and closed.")
            except Exception as e:
                print(f"Error stopping camera: {e}")

    def on_closing(self):
        """Handle window closing event."""
        self.stop()
        self.root.destroy()


class MainGUI:
    def __init__(self, root, app):
        """Initialize the MainGUI class."""
        self.root = root
        self.app = app
        
        self.root.title("Main GUI")
        
        # Checkbox for enabling GCodeGUI
        self.gcode_checkbox_var = tk.BooleanVar()
        self.gcode_checkbox = tk.Checkbutton(self.root, text="Show GCode Control", variable=self.gcode_checkbox_var, command=self.toggle_gcode_gui)
        self.gcode_checkbox.pack(pady=10)
        
        # Checkbox for enabling CameraGUI
        self.camera_checkbox_var = tk.BooleanVar()
        self.camera_checkbox = tk.Checkbutton(self.root, text="Show Camera Preview", variable=self.camera_checkbox_var, command=self.toggle_camera_gui)
        self.camera_checkbox.pack(pady=10)

        # Checkbox for enabling ExperimentGUI
        self.experiment_checkbox_var = tk.BooleanVar()
        self.experiment_checkbox = tk.Checkbutton(self.root, text="Experiment", variable=self.experiment_checkbox_var, command=self.toggle_experiment)
        self.experiment_checkbox.pack(pady=10)
        
        # Checkbox for enabling PathfinderGUI
        self.pathfinder_checkbox_var = tk.BooleanVar()
        self.pathfinder_checkbox = tk.Checkbutton(self.root, text="Pathfinder", variable=self.pathfinder_checkbox_var, command=self.toggle_pathfinder_gui)
        self.pathfinder_checkbox.pack(pady=10)

        # Initialize ExperimentGUI
        self.experiment_gui = ExperimentGUI(root, self.experiment_checkbox_var)
        
    def toggle_gcode_gui(self):
        """Toggle the GCodeGUI window based on the checkbox."""
        if self.gcode_checkbox_var.get():  # If checked, open GCodeGUI
            self.app.open_gcode_gui()
        else:  # If unchecked, close GCodeGUI
            self.app.close_gcode_gui()
    
    def toggle_camera_gui(self):
        """Toggle the CameraGUI window based on the checkbox."""
        if self.camera_checkbox_var.get():  # If checked, open CameraGUI
            self.app.open_camera_gui()
        else:  # If unchecked, close CameraGUI
            self.app.close_camera_gui()
            
    def toggle_experiment(self):
        """Toggle the ExperimentGUI window based on the checkbox."""
        if self.experiment_checkbox_var.get():
            self.experiment_gui.start()
        else:
            self.experiment_gui.stop()
            
    def toggle_pathfinder_gui(self):
        """Toggle the PathfinderGUI window based on the checkbox."""
        if self.pathfinder_checkbox_var.get():
            self.app.open_pathfinder_gui()
        else:
            self.app.close_pathfinder_gui()

class ExperimentGUI:
    def __init__(self, root, checkbox_var):
        self.root = root
        self.window = None
        self.checkbox_var = checkbox_var
        self.save_folder = ""
        self.is_running = False
        self.file_prefix = "fileprefix"
        

    def init_gui(self):
        self.window = tk.Toplevel(self.root)
        self.window.title("Experiment GUI")
        self.window.protocol("WM_DELETE_WINDOW", self.stop)

        # Create main frame
        main_frame = tk.Frame(self.window, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Folder selection
        folder_frame = tk.LabelFrame(main_frame, text="Save Location", padx=5, pady=5)
        folder_frame.pack(fill=tk.X, pady=5)

        self.folder_path = tk.StringVar()
        folder_entry = tk.Entry(folder_frame, textvariable=self.folder_path, width=50)
        folder_entry.pack(side=tk.LEFT, padx=5)

        folder_button = tk.Button(folder_frame, text="Browse...", command=self.select_folder)
        folder_button.pack(side=tk.LEFT, padx=5)

        # File prefix name entry
        prefix_frame = tk.Frame(main_frame)
        prefix_frame.pack(fill=tk.X, pady=5)

        tk.Label(prefix_frame, text="File Prefix:").pack(side=tk.LEFT, padx=5)
        self.prefix_var = tk.StringVar()
        prefix_entry = tk.Entry(prefix_frame, textvariable=self.prefix_var, width=30)
        prefix_entry.pack(side=tk.LEFT, padx=5)
        
        # Duration settings
        time_frame = tk.LabelFrame(main_frame, text="Duration", padx=5, pady=5)
        time_frame.pack(fill=tk.X, pady=5)

        # Hours
        hours_frame = tk.Frame(time_frame)
        hours_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(hours_frame, text="Hours:").pack()
        self.hours_var = tk.StringVar(value="0")
        tk.Entry(hours_frame, textvariable=self.hours_var, width=5).pack()

        # Minutes
        minutes_frame = tk.Frame(time_frame)
        minutes_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(minutes_frame, text="Minutes:").pack()
        self.minutes_var = tk.StringVar(value="0")
        tk.Entry(minutes_frame, textvariable=self.minutes_var, width=5).pack()

        # Seconds
        seconds_frame = tk.Frame(time_frame)
        seconds_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(seconds_frame, text="Seconds:").pack()
        self.seconds_var = tk.StringVar(value="0")
        tk.Entry(seconds_frame, textvariable=self.seconds_var, width=5).pack()

        # Control buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.start_button = tk.Button(button_frame, text="Start Experiment", command=self.start_experiment)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(button_frame, text="Stop Experiment", command=self.stop_experiment, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Status display
        self.status_var = tk.StringVar(value="Ready")
        status_label = tk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(pady=5)

    def start(self):
        if self.window is None:
            self.init_gui()

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_folder = folder
            self.folder_path.set(folder)

    def start_experiment(self):
        if not self.save_folder:
            messagebox.showerror("Error", "Please select a save folder first")
            return

        self.file_prefix = self.prefix_var.get()
        if not self.file_prefix:
            messagebox.showerror("Error", "Please enter a file prefix")
            return
            
        try:
            hours = int(self.hours_var.get())
            minutes = int(self.minutes_var.get())
            seconds = int(self.seconds_var.get())
            
            if hours == 0 and minutes == 0 and seconds == 0:
                messagebox.showerror("Error", "Please set a duration greater than 0")
                return
                
            self.is_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set("Experiment running...")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for duration")
            return

    def stop_experiment(self):
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Experiment stopped")

    def stop(self):
        if self.is_running:
            self.stop_experiment()
        if self.window is not None:
            self.window.destroy()
            self.window = None
            self.checkbox_var.set(False)
            
class PathfinderGUI:
    def __init__(self, root, gcode):
        self.root = root
        self.gcode = gcode
        self.root.title("Pathfinder")
        
        # Set initial window size
        self.root.geometry("400x300")  # Width x Height
        
        # Initialize well coordinates
        self.A1 = None
        self.A8 = None
        self.F8 = None
        self.F1 = None
        
        # Create main frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Add widgets to the main frame
        self.create_widgets()
        
        # Bind window closing event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_widgets(self):
        # Capture A1 Well button
        self.A1_frame = tk.Frame(self.main_frame)
        self.A1_frame.pack(anchor=tk.W, padx=5, pady=5)
        self.A1_button = tk.Button(self.A1_frame, text="Capture A1 Well", command=self.capture_A1)
        self.A1_button.pack(side=tk.LEFT)
        self.A1_label = tk.Label(self.A1_frame, text="")
        self.A1_label.pack(side=tk.LEFT, padx=5)
        
        # Capture A8 Well button
        self.A8_frame = tk.Frame(self.main_frame)
        self.A8_frame.pack(anchor=tk.W, padx=5, pady=5)
        self.A8_button = tk.Button(self.A8_frame, text="Capture A8 Well", command=self.capture_A8)
        self.A8_button.pack(side=tk.LEFT)
        self.A8_label = tk.Label(self.A8_frame, text="")
        self.A8_label.pack(side=tk.LEFT, padx=5)
        
        # Capture F8 Well button
        self.F8_frame = tk.Frame(self.main_frame)
        self.F8_frame.pack(anchor=tk.W, padx=5, pady=5)
        self.F8_button = tk.Button(self.F8_frame, text="Capture F8 Well", command=self.capture_F8)
        self.F8_button.pack(side=tk.LEFT)
        self.F8_label = tk.Label(self.F8_frame, text="")
        self.F8_label.pack(side=tk.LEFT, padx=5)
        
        # Capture F1 Well button
        self.F1_frame = tk.Frame(self.main_frame)
        self.F1_frame.pack(anchor=tk.W, padx=5, pady=5)
        self.F1_button = tk.Button(self.F1_frame, text="Capture F1 Well", command=self.capture_F1)
        self.F1_button.pack(side=tk.LEFT)
        self.F1_label = tk.Label(self.F1_frame, text="")
        self.F1_label.pack(side=tk.LEFT, padx=5)
        
        # Generate Path button
        self.generate_button = tk.Button(self.main_frame, text="Generate Path", command=self.generate_path, state=tk.DISABLED)
        self.generate_button.pack(pady=10)
        
    def capture_A1(self):
        self.A1 = {'X': self.gcode.current_position['X'], 'Y': self.gcode.current_position['Y'], 'Z': self.gcode.current_position['Z']}
        self.A1_label.config(text=f"X: {self.A1['X']:.2f}, Y: {self.A1['Y']:.2f}, Z: {self.A1['Z']:.2f}")
        self.check_capture_status()

    def capture_A8(self):
        self.A8 = {'X': self.gcode.current_position['X'], 'Y': self.gcode.current_position['Y'], 'Z': self.gcode.current_position['Z']}
        self.A8_label.config(text=f"X: {self.A8['X']:.2f}, Y: {self.A8['Y']:.2f}, Z: {self.A8['Z']:.2f}")
        self.check_capture_status()

    def capture_F8(self):
        self.F8 = {'X': self.gcode.current_position['X'], 'Y': self.gcode.current_position['Y'], 'Z': self.gcode.current_position['Z']}
        self.F8_label.config(text=f"X: {self.F8['X']:.2f}, Y: {self.F8['Y']:.2f}, Z: {self.F8['Z']:.2f}")
        self.check_capture_status()

    def capture_F1(self):
        self.F1 = {'X': self.gcode.current_position['X'], 'Y': self.gcode.current_position['Y'], 'Z': self.gcode.current_position['Z']}
        self.F1_label.config(text=f"X: {self.F1['X']:.2f}, Y: {self.F1['Y']:.2f}, Z: {self.F1['Z']:.2f}")
        self.check_capture_status()
        self.check_capture_status()
        
    def check_capture_status(self):
        if self.A1 and self.A8 and self.F8 and self.F1:
            self.generate_button.config(state=tk.NORMAL)
        
    def generate_path(self):
        # Generate the list of points for A1, A2, A3, ... F6, F7, F8
        path = []

        # Check if all well coordinates are captured
        if not all([self.A1, self.A8, self.F8, self.F1]):
            print("Error: Not all well coordinates are captured.")
            print("Please capture all four well coordinates before generating the path.")
            return

        # Print the captured well coordinates for debugging
        print("Captured well coordinates:")
        print(f"A1: X: {self.A1['X']:.2f}, Y: {self.A1['Y']:.2f}, Z: {self.A1['Z']:.2f}")
        print(f"A8: X: {self.A8['X']:.2f}, Y: {self.A8['Y']:.2f}, Z: {self.A8['Z']:.2f}")
        print(f"F8: X: {self.F8['X']:.2f}, Y: {self.F8['Y']:.2f}, Z: {self.F8['Z']:.2f}")
        print(f"F1: X: {self.F1['X']:.2f}, Y: {self.F1['Y']:.2f}, Z: {self.F1['Z']:.2f}")

        # Calculate the number of rows and columns
        num_rows = 6  # A to F
        num_cols = 8  # 1 to 8

        # Calculate the step sizes for X and Y coordinates
        x_step = (self.A8['X'] - self.A1['X']) / (num_cols - 1)
        y_step = (self.F1['Y'] - self.A1['Y']) / (num_rows - 1)

        # Iterate over each row (A to F)
        for row in range(num_rows):
            # Calculate the Y coordinate for the current row
            y = self.A1['Y'] + row * y_step

            # Iterate over each column (1 to 8)
            for col in range(num_cols):
                # Calculate the X coordinate for the current column
                x = self.A1['X'] + col * x_step

                # Append the interpolated point to the path
                path.append({'X': x, 'Y': y, 'Z': self.A1['Z']})

        print("Generated path:")
        for point in path:
            print(f"X: {point['X']:.2f}, Y: {point['Y']:.2f}, Z: {point['Z']:.2f}")
            
    class Experiment:
        def __init__(self, camera, gcode, path, save_folder, file_prefix):
            self.camera = camera
            self.gcode = gcode
            self.path = path
            self.save_folder = save_folder
            self.file_prefix = file_prefix
            self.is_running = False
            self.current_iteration = 1

        def start(self):
            self.is_running = True
            self.run_experiment()

        def stop(self):
            self.is_running = False

        def run_experiment(self):
            while self.is_running:
                for point in self.path:
                    if not self.is_running:
                        break

                    # Move to the specified point
                    self.gcode.move_xyz(point['X'], point['Y'], point['Z'])

                    # Wait for the movement to complete
                    while self.gcode.is_moving():
                        time.sleep(0.1)

                    # Capture an image with the camera
                    image = self.camera.capture_image()

                    # Generate the file name
                    file_name = f"{self.file_prefix}_Well_{point['Well']}_{self.current_iteration}.jpg"
                    file_path = os.path.join(self.save_folder, file_name)

                    # Save the image
                    cv2.imwrite(file_path, image)

                self.current_iteration += 1

class App:
    def __init__(self, root):
        self.root = root
        self.gcode_gui_window = None
        self.camera_gui_window = None
        self.camera_gui = None  # Add reference to CameraGUI instance
        self.pathfinder_gui_window = None
        
        # Initialize the MainGUI
        self.main_gui = MainGUI(root, self)
        
        self.gcode = GCode()

    def open_gcode_gui(self):
        """Open the GCode GUI in a new window."""
        if self.gcode_gui_window is None:  # Only open if not already open
            self.gcode_gui_window = Toplevel(self.root)
            self.gcode_gui_window.title("GCode Control")
            GCodeGUI(self.gcode_gui_window, self.gcode)
            self.gcode_gui_window.protocol("WM_DELETE_WINDOW", self.close_gcode_gui)
        
    def close_gcode_gui(self):
        """Close the GCode GUI window."""
        if self.gcode_gui_window:
            self.gcode_gui_window.destroy()
            self.gcode_gui_window = None
            self.main_gui.gcode_checkbox_var.set(False)

    def open_camera_gui(self):
        """Open the Camera GUI in a new window."""
        if self.camera_gui_window is None:  # Only open if not already open
            self.camera_gui_window = Toplevel(self.root)
            self.camera_gui_window.title("Camera Preview")
            self.camera_gui_window.geometry("640x480")
            self.camera_gui = CameraGUI(self.camera_gui_window)  # Store reference
            self.camera_gui_window.protocol("WM_DELETE_WINDOW", self.close_camera_gui)
    
    def close_camera_gui(self):
        """Close the Camera GUI window."""
        if self.camera_gui_window:
            if self.camera_gui:
                self.camera_gui.stop()  # Stop the camera properly
                self.camera_gui = None
            self.camera_gui_window.destroy()
            self.camera_gui_window = None
            self.main_gui.camera_checkbox_var.set(False)
            
    def open_pathfinder_gui(self):
        """Open the Pathfinder GUI in a new window."""
        if self.pathfinder_gui_window is None:  # Only open if not already open
            self.pathfinder_gui_window = Toplevel(self.root)
            self.pathfinder_gui_window.title("Pathfinder")
            PathfinderGUI(self.pathfinder_gui_window, self.gcode)  # Pass the gcode instance
            self.pathfinder_gui_window.protocol("WM_DELETE_WINDOW", self.close_pathfinder_gui)
        
    def close_pathfinder_gui(self):
        """Close the Pathfinder GUI window."""
        if self.pathfinder_gui_window:
            self.pathfinder_gui_window.destroy()
            self.pathfinder_gui_window = None
            self.main_gui.pathfinder_checkbox_var.set(False)

    def start(self):
        """Start the Tkinter main loop."""
        self.root.mainloop()

# Main program
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)  # Initialize the App object
    app.start()  # Start the application

"""
GCode control interface for microscope movement.
Provides UI for manual control and movement settings.
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Dict, Any

from ..config import GUI_SETTINGS, GCODE_SETTINGS

class GCodeGUI:
    """GUI class for GCode control interface."""
    
    def __init__(self, root: tk.Toplevel, gcode: Any):
        """
        Initialize the GCode control interface.
        
        Args:
            root: Parent window
            gcode: GCode controller instance
        """
        self.logger = logging.getLogger(__name__)
        self.root = root
        self.gcode = gcode
        
        # Set window properties
        self.root.title("GCode Control")
        self.root.resizable(False, False)
        
        # Initialize variables
        self.step_size = tk.DoubleVar(value=GUI_SETTINGS['DEFAULT_STEP_SIZE'])
        self.create_gui()
        
    def create_gui(self):
        """Create the GUI elements."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Position control frame
        pos_frame = ttk.LabelFrame(main_frame, text="Position Control", padding="5")
        pos_frame.grid(row=0, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Coordinate entries
        self.coord_vars = {
            'X': tk.StringVar(value='0.0'),
            'Y': tk.StringVar(value='0.0'),
            'Z': tk.StringVar(value='0.0')
        }
        
        # Create coordinate entry fields
        for i, (axis, var) in enumerate(self.coord_vars.items()):
            ttk.Label(pos_frame, text=f"{axis}:").grid(row=i, column=0, padx=5, pady=2)
            ttk.Entry(pos_frame, textvariable=var, width=10).grid(row=i, column=1, padx=5, pady=2)
        
        # Send coordinates button
        ttk.Button(
            pos_frame,
            text="Move to Position",
            command=self.send_absolute_move
        ).grid(row=len(self.coord_vars), column=0, columnspan=2, pady=5)
        
        # Step size control frame
        step_frame = ttk.LabelFrame(main_frame, text="Step Size", padding="5")
        step_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Step size radio buttons
        for i, size in enumerate(GUI_SETTINGS['STEP_SIZES']):
            ttk.Radiobutton(
                step_frame,
                text=f"{size} mm",
                variable=self.step_size,
                value=size
            ).grid(row=0, column=i, padx=5)
        
        # Movement control frame
        move_frame = ttk.LabelFrame(main_frame, text="Movement Control", padding="5")
        move_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Movement buttons
        # Y+ button
        ttk.Button(
            move_frame,
            text="Y+",
            command=lambda: self.move_increment('Y', 1)
        ).grid(row=0, column=1)
        
        # X- button
        ttk.Button(
            move_frame,
            text="X-",
            command=lambda: self.move_increment('X', -1)
        ).grid(row=1, column=0)
        
        # X+ button
        ttk.Button(
            move_frame,
            text="X+",
            command=lambda: self.move_increment('X', 1)
        ).grid(row=1, column=2)
        
        # Y- button
        ttk.Button(
            move_frame,
            text="Y-",
            command=lambda: self.move_increment('Y', -1)
        ).grid(row=2, column=1)
        
        # Z controls
        ttk.Button(
            move_frame,
            text="Z+",
            command=lambda: self.move_increment('Z', 1)
        ).grid(row=1, column=3, padx=10)
        
        ttk.Button(
            move_frame,
            text="Z-",
            command=lambda: self.move_increment('Z', -1)
        ).grid(row=2, column=3, padx=10)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Motion Settings", padding="5")
        settings_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Settings entries
        self.settings_vars = {
            'Feedrate': tk.StringVar(value=str(GCODE_SETTINGS['FEEDRATE'])),
            'Acceleration': tk.StringVar(value=str(GCODE_SETTINGS['ACCELERATION'])),
            'Jerk': tk.StringVar(value=str(GCODE_SETTINGS['JERK']))
        }
        
        # Create settings entry fields
        for i, (setting, var) in enumerate(self.settings_vars.items()):
            ttk.Label(settings_frame, text=f"{setting}:").grid(row=i, column=0, padx=5, pady=2)
            ttk.Entry(settings_frame, textvariable=var, width=10).grid(row=i, column=1, padx=5, pady=2)
        
        # Apply settings button
        ttk.Button(
            settings_frame,
            text="Apply Settings",
            command=self.apply_settings
        ).grid(row=len(self.settings_vars), column=0, columnspan=2, pady=5)
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=4, column=0, columnspan=2, pady=5)
        
        # Home button
        ttk.Button(
            control_frame,
            text="Home All Axes",
            command=self.home_axes
        ).grid(row=0, column=0, padx=5)
        
        # Enable/Disable steppers
        ttk.Button(
            control_frame,
            text="Enable Steppers",
            command=self.enable_steppers
        ).grid(row=0, column=1, padx=5)
        
        ttk.Button(
            control_frame,
            text="Disable Steppers",
            command=self.disable_steppers
        ).grid(row=0, column=2, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var)
        status_bar.grid(row=5, column=0, columnspan=2, pady=5)
        
    def move_increment(self, axis: str, direction: int):
        """
        Move an axis by the current step size.
        
        Args:
            axis: Axis to move ('X', 'Y', or 'Z')
            direction: Direction to move (1 or -1)
        """
        try:
            step = self.step_size.get() * direction
            current_pos = self.gcode.get_position()
            new_pos = dict(current_pos)
            new_pos[axis] = current_pos[axis] + step
            
            if self.gcode.move_xyz(new_pos['X'], new_pos['Y'], new_pos['Z']):
                # Update position display
                self.update_position_display()
                self.status_var.set(f"Moved {axis} by {step:+.2f}mm")
            else:
                self.status_var.set(f"Movement failed")
                
        except Exception as e:
            self.logger.error(f"Error in incremental move: {e}")
            self.status_var.set("Movement error")
            
    def send_absolute_move(self):
        """Send absolute coordinates to the printer."""
        try:
            x = float(self.coord_vars['X'].get())
            y = float(self.coord_vars['Y'].get())
            z = float(self.coord_vars['Z'].get())
            
            if self.gcode.move_xyz(x, y, z):
                self.status_var.set("Movement completed")
            else:
                self.status_var.set("Movement failed")
                
        except ValueError:
            self.status_var.set("Invalid coordinates")
        except Exception as e:
            self.logger.error(f"Error in absolute move: {e}")
            self.status_var.set("Movement error")
            
    def update_position_display(self):
        """Update the position display with current coordinates."""
        pos = self.gcode.get_position()
        for axis, var in self.coord_vars.items():
            var.set(f"{pos[axis]:.2f}")
            
    def apply_settings(self):
        """Apply motion settings to the printer."""
        try:
            feedrate = float(self.settings_vars['Feedrate'].get())
            acceleration = float(self.settings_vars['Acceleration'].get())
            jerk = float(self.settings_vars['Jerk'].get())
            
            self.gcode.set_feedrate(feedrate)
            self.gcode.set_acceleration(acceleration)
            self.gcode.set_jerk(jerk)
            
            self.status_var.set("Settings applied")
            
        except ValueError:
            self.status_var.set("Invalid settings values")
        except Exception as e:
            self.logger.error(f"Error applying settings: {e}")
            self.status_var.set("Settings error")
            
    def home_axes(self):
        """Home all axes."""
        try:
            if self.gcode.home_all_axes():
                self.update_position_display()
                self.status_var.set("Homing completed")
            else:
                self.status_var.set("Homing failed")
        except Exception as e:
            self.logger.error(f"Error during homing: {e}")
            self.status_var.set("Homing error")
            
    def enable_steppers(self):
        """Enable the stepper motors."""
        try:
            if self.gcode.enable_steppers():
                self.status_var.set("Steppers enabled")
            else:
                self.status_var.set("Failed to enable steppers")
        except Exception as e:
            self.logger.error(f"Error enabling steppers: {e}")
            self.status_var.set("Stepper error")
            
    def disable_steppers(self):
        """Disable the stepper motors."""
        try:
            if self.gcode.disable_steppers():
                self.status_var.set("Steppers disabled")
            else:
                self.status_var.set("Failed to disable steppers")
        except Exception as e:
            self.logger.error(f"Error disabling steppers: {e}")
            self.status_var.set("Stepper error")

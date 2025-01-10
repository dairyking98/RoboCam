"""
Main GUI module for microscope control system.
Coordinates all GUI windows and components.
"""

import tkinter as tk
from tkinter import ttk, Toplevel
import logging
from typing import Optional, Dict

from ..config import GUI_SETTINGS
from ..hardware.gcode import GCode
from .gcode_gui import GCodeGUI
from .camera_gui import CameraGUI
from .experiment_gui import ExperimentGUI
from .pathfinder_gui import PathfinderGUI

class App:
    """Main application class that manages all GUI windows and components."""
    
    def __init__(self, root: tk.Tk):
        """
        Initialize the main application.
        
        Args:
            root: The root Tkinter window
        """
        self.logger = logging.getLogger(__name__)
        self.root = root
        
        # Set main window properties
        self.root.title("Microscope Control System")
        self.root.geometry(GUI_SETTINGS['MAIN_WINDOW_SIZE'])
        
        # Initialize hardware
        self.gcode = GCode()
        
        # Initialize window references
        self.windows: Dict[str, Optional[tk.Toplevel]] = {
            'gcode': None,
            'camera': None,
            'pathfinder': None
        }
        
        # Initialize GUI instances
        self.gui_instances: Dict[str, Optional[object]] = {
            'gcode': None,
            'camera': None,
            'pathfinder': None,
            'experiment': None
        }
        
        # Create main GUI elements
        self.create_main_gui()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_main_gui(self):
        """Create the main window GUI elements."""
        # Create main frame with padding
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create title label
        title_label = ttk.Label(
            self.main_frame, 
            text="Microscope Control System",
            font=('Helvetica', 16, 'bold')
        )
        title_label.grid(row=0, column=0, pady=10, columnspan=2)
        
        # Create checkboxes frame
        checkbox_frame = ttk.LabelFrame(self.main_frame, text="Controls", padding="5")
        checkbox_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Create checkbox variables
        self.checkbox_vars = {
            'gcode': tk.BooleanVar(),
            'camera': tk.BooleanVar(),
            'experiment': tk.BooleanVar(),
            'pathfinder': tk.BooleanVar()
        }
        
        # Create checkboxes
        ttk.Checkbutton(
            checkbox_frame,
            text="GCode Control",
            variable=self.checkbox_vars['gcode'],
            command=lambda: self.toggle_window('gcode')
        ).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(
            checkbox_frame,
            text="Camera Preview",
            variable=self.checkbox_vars['camera'],
            command=lambda: self.toggle_window('camera')
        ).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(
            checkbox_frame,
            text="Experiment Control",
            variable=self.checkbox_vars['experiment'],
            command=self.toggle_experiment
        ).grid(row=2, column=0, sticky=tk.W, pady=2)
        
        ttk.Checkbutton(
            checkbox_frame,
            text="Well Plate Pathfinder",
            variable=self.checkbox_vars['pathfinder'],
            command=lambda: self.toggle_window('pathfinder')
        ).grid(row=3, column=0, sticky=tk.W, pady=2)
        
        # Create status frame
        status_frame = ttk.LabelFrame(self.main_frame, text="Status", padding="5")
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Add status labels
        self.status_labels = {
            'gcode': ttk.Label(status_frame, text="GCode: Not Connected"),
            'camera': ttk.Label(status_frame, text="Camera: Not Running"),
            'experiment': ttk.Label(status_frame, text="Experiment: Idle")
        }
        
        for i, (key, label) in enumerate(self.status_labels.items()):
            label.grid(row=i, column=0, sticky=tk.W, pady=2)
    
    def toggle_window(self, window_type: str):
        """
        Toggle the visibility of a specific window.
        
        Args:
            window_type: Type of window to toggle ('gcode', 'camera', or 'pathfinder')
        """
        try:
            if self.checkbox_vars[window_type].get():
                self.open_window(window_type)
            else:
                self.close_window(window_type)
        except Exception as e:
            self.logger.error(f"Error toggling {window_type} window: {e}")
            self.checkbox_vars[window_type].set(False)
    
    def open_window(self, window_type: str):
        """
        Open a specific window.
        
        Args:
            window_type: Type of window to open
        """
        if self.windows[window_type] is None:
            try:
                self.windows[window_type] = tk.Toplevel(self.root)
                
                if window_type == 'gcode':
                    self.gui_instances['gcode'] = GCodeGUI(
                        self.windows[window_type],
                        self.gcode
                    )
                    self.update_status('gcode', 'Connected')
                    
                elif window_type == 'camera':
                    self.gui_instances['camera'] = CameraGUI(
                        self.windows[window_type]
                    )
                    self.update_status('camera', 'Running')
                    
                elif window_type == 'pathfinder':
                    self.gui_instances['pathfinder'] = PathfinderGUI(
                        self.windows[window_type],
                        self.gcode
                    )
                
                # Set window close protocol
                self.windows[window_type].protocol(
                    "WM_DELETE_WINDOW",
                    lambda w=window_type: self.close_window(w)
                )
            
            except Exception as e:
                self.logger.error(f"Error opening {window_type} window: {e}")
                if self.windows[window_type]:
                    self.windows[window_type].destroy()
                    self.windows[window_type] = None
                self.checkbox_vars[window_type].set(False)
    
    def close_window(self, window_type: str):
        """
        Close a specific window.
        
        Args:
            window_type: Type of window to close
        """
        if self.windows[window_type]:
            try:
                # Cleanup specific window types
                if window_type == 'camera' and self.gui_instances['camera']:
                    self.gui_instances['camera'].stop()
                    self.update_status('camera', 'Not Running')
                    
                elif window_type == 'gcode':
                    self.update_status('gcode', 'Not Connected')
                
                # Destroy window and clear references
                self.windows[window_type].destroy()
                self.windows[window_type] = None
                self.gui_instances[window_type] = None
                self.checkbox_vars[window_type].set(False)
            
            except Exception as e:
                self.logger.error(f"Error closing {window_type} window: {e}")
    
    def toggle_experiment(self):
        """Toggle the experiment control GUI."""
        try:
            if self.checkbox_vars['experiment'].get():
                if not self.gui_instances['experiment']:
                    self.gui_instances['experiment'] = ExperimentGUI(
                        self.root,
                        self.checkbox_vars['experiment']
                    )
                self.gui_instances['experiment'].start()
                self.update_status('experiment', 'Running')
            else:
                if self.gui_instances['experiment']:
                    self.gui_instances['experiment'].stop()
                    self.update_status('experiment', 'Idle')
        
        except Exception as e:
            self.logger.error(f"Error toggling experiment GUI: {e}")
            self.checkbox_vars['experiment'].set(False)
            self.update_status('experiment', 'Error')
    
    def update_status(self, component: str, status: str):
        """
        Update the status display for a component.
        
        Args:
            component: Component name
            status: Status message to display
        """
        if component in self.status_labels:
            self.status_labels[component].config(
                text=f"{component.title()}: {status}"
            )
    
    def on_closing(self):
        """Handle application shutdown."""
        try:
            self.logger.info("Shutting down application")
            
            # Close all windows
            for window_type in self.windows:
                if self.windows[window_type]:
                    self.close_window(window_type)
            
            # Cleanup hardware
            if self.gcode:
                self.gcode.disable_steppers()
                self.gcode.close_connection()
            
            # Destroy root window
            self.root.destroy()
        
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            self.root.destroy()
    
    def start(self):
        """Start the application main loop."""
        try:
            self.logger.info("Starting main application loop")
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            raise

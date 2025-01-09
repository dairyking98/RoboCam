"""
Main GUI module for the microscope control application.
"""
import tkinter as tk

class MainGUI:
    def __init__(self, root, app):
        """Initialize the MainGUI class."""
        self.root = root
        self.app = app
        
        self.root.title("Main GUI")
        
        # Checkbox for enabling GCodeGUI
        self.gcode_checkbox_var = tk.BooleanVar()
        self.gcode_checkbox = tk.Checkbutton(
            self.root, 
            text="Show GCode Control", 
            variable=self.gcode_checkbox_var, 
            command=self.toggle_gcode_gui
        )
        self.gcode_checkbox.pack(pady=10)
        
        # Checkbox for enabling CameraGUI
        self.camera_checkbox_var = tk.BooleanVar()
        self.camera_checkbox = tk.Checkbutton(
            self.root, 
            text="Show Camera Preview", 
            variable=self.camera_checkbox_var, 
            command=self.toggle_camera_gui
        )
        self.camera_checkbox.pack(pady=10)

        # Checkbox for enabling ExperimentGUI
        self.experiment_checkbox_var = tk.BooleanVar()
        self.experiment_checkbox = tk.Checkbutton(
            self.root, 
            text="Experiment", 
            variable=self.experiment_checkbox_var, 
            command=self.toggle_experiment_gui
        )
        self.experiment_checkbox.pack(pady=10)
        
        # Checkbox for enabling PathfinderGUI
        self.pathfinder_checkbox_var = tk.BooleanVar()
        self.pathfinder_checkbox = tk.Checkbutton(
            self.root, 
            text="Pathfinder", 
            variable=self.pathfinder_checkbox_var, 
            command=self.toggle_pathfinder_gui
        )
        self.pathfinder_checkbox.pack(pady=10)

    def toggle_gcode_gui(self):
        """Toggle the GCodeGUI window based on the checkbox."""
        if self.gcode_checkbox_var.get():
            self.app.open_gcode_gui()
        else:
            self.app.close_gcode_gui()
    
    def toggle_camera_gui(self):
        """Toggle the CameraGUI window based on the checkbox."""
        if self.camera_checkbox_var.get():
            self.app.open_camera_gui()
        else:
            self.app.close_camera_gui()
            
    def toggle_experiment_gui(self):
        """Toggle the ExperimentGUI window based on the checkbox."""
        if self.experiment_checkbox_var.get():
            self.app.open_experiment_gui()
        else:
            self.app.close_experiment_gui()
            
    def toggle_pathfinder_gui(self):
        """Toggle the PathfinderGUI window based on the checkbox."""
        if self.pathfinder_checkbox_var.get():
            self.app.open_pathfinder_gui()
        else:
            self.app.close_pathfinder_gui()
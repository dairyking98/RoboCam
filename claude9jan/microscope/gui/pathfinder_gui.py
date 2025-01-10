"""
Well plate navigation and path generation interface.
Handles coordinate capture and path generation for automated plate scanning.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Optional, Dict, List, Any
import numpy as np
import json

from microscope.config import WELL_PLATE

class PathfinderGUI:
    """GUI class for well plate navigation and path generation."""
    
    def __init__(self, root: tk.Toplevel, gcode: Any):
        """
        Initialize the well plate navigation interface.
        
        Args:
            root: Parent window
            gcode: GCode controller instance
        """
        self.logger = logging.getLogger(__name__)
        self.root = root
        self.gcode = gcode
        
        # Set window properties
        self.root.title("Well Plate Pathfinder")
        self.root.resizable(False, False)
        
        # Initialize corner coordinates
        self.corners = {
            'A1': None,
            'A8': None,
            'F8': None,
            'F1': None
        }
        
        # Initialize path data
        self.path_points: List[Dict[str, float]] = []
        
        # Create GUI
        self.create_gui()
        
    def create_gui(self):
        """Create the GUI elements."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Corner capture section
        self.create_corner_capture_section(main_frame)
        
        # Path controls section
        self.create_path_controls_section(main_frame)
        
        # Path display section
        self.create_path_display_section(main_frame)
        
        # Status section
        self.create_status_section(main_frame)
        
    def create_corner_capture_section(self, parent: ttk.Frame):
        """Create the corner capture control section."""
        corner_frame = ttk.LabelFrame(parent, text="Corner Positions", padding="5")
        corner_frame.grid(row=0, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Create capture buttons and position displays for each corner
        self.corner_labels = {}
        
        for i, (corner, _) in enumerate(self.corners.items()):
            # Button frame
            btn_frame = ttk.Frame(corner_frame)
            btn_frame.grid(row=i, column=0, pady=2, sticky=tk.W)
            
            # Capture button
            capture_btn = ttk.Button(
                btn_frame,
                text=f"Capture {corner}",
                command=lambda c=corner: self.capture_corner(c)
            )
            capture_btn.grid(row=0, column=0, padx=5)
            
            # Position label
            self.corner_labels[corner] = ttk.Label(btn_frame, text="Not set")
            self.corner_labels[corner].grid(row=0, column=1, padx=5)
            
    def create_path_controls_section(self, parent: ttk.Frame):
        """Create the path generation control section."""
        control_frame = ttk.LabelFrame(parent, text="Path Controls", padding="5")
        control_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Generate path button
        self.generate_btn = ttk.Button(
            control_frame,
            text="Generate Path",
            command=self.generate_path,
            state=tk.DISABLED
        )
        self.generate_btn.grid(row=0, column=0, padx=5, pady=5)
        
        # Clear path button
        self.clear_btn = ttk.Button(
            control_frame,
            text="Clear Path",
            command=self.clear_path,
            state=tk.DISABLED
        )
        self.clear_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # Save path button
        self.save_btn = ttk.Button(
            control_frame,
            text="Save Path",
            command=self.save_path,
            state=tk.DISABLED
        )
        self.save_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Add options for scanning pattern
        ttk.Label(control_frame, text="Scan Pattern:").grid(row=1, column=0, padx=5, pady=2)
        self.pattern_var = tk.StringVar(value="snake")
        pattern_menu = ttk.OptionMenu(
            control_frame,
            self.pattern_var,
            "snake",
            "snake",
            "raster"
        )
        pattern_menu.grid(row=1, column=1, padx=5, pady=2)
        
    def create_path_display_section(self, parent: ttk.Frame):
        """Create the path display section."""
        display_frame = ttk.LabelFrame(parent, text="Path Preview", padding="5")
        display_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        # Create text widget for path display
        self.path_text = tk.Text(display_frame, height=10, width=40)
        self.path_text.grid(row=0, column=0, padx=5, pady=5)
        self.path_text.config(state=tk.DISABLED)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(display_frame, orient=tk.VERTICAL, command=self.path_text.yview)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.path_text.configure(yscrollcommand=scrollbar.set)
        
    def create_status_section(self, parent: ttk.Frame):
        """Create the status display section."""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack()
        
    def capture_corner(self, corner: str):
        """
        Capture current position for specified corner.
        
        Args:
            corner: Corner identifier ('A1', 'A8', 'F8', or 'F1')
        """
        try:
            position = self.gcode.get_position()
            self.corners[corner] = position
            
            # Update position display
            self.corner_labels[corner].config(
                text=f"X: {position['X']:.2f}, Y: {position['Y']:.2f}, Z: {position['Z']:.2f}"
            )
            
            # Check if all corners are captured
            if all(pos is not None for pos in self.corners.values()):
                self.generate_btn.config(state=tk.NORMAL)
                self.status_var.set("Ready to generate path")
            
        except Exception as e:
            self.logger.error(f"Error capturing corner {corner}: {e}")
            messagebox.showerror("Error", f"Failed to capture corner {corner}")
            
    def generate_path(self):
        """Generate path between corners based on selected pattern."""
        try:
            if not all(pos is not None for pos in self.corners.values()):
                raise ValueError("Not all corners have been captured")
            
            # Calculate number of rows and columns
            num_rows = WELL_PLATE['ROWS']
            num_cols = WELL_PLATE['COLS']
            
            # Calculate step sizes
            x_step = (self.corners['A8']['X'] - self.corners['A1']['X']) / (num_cols - 1)
            y_step = (self.corners['F1']['Y'] - self.corners['A1']['Y']) / (num_rows - 1)
            
            # Clear existing path
            self.path_points = []
            
            # Generate points based on pattern
            if self.pattern_var.get() == "snake":
                self.generate_snake_path(num_rows, num_cols, x_step, y_step)
            else:
                self.generate_raster_path(num_rows, num_cols, x_step, y_step)
            
            # Update display
            self.update_path_display()
            self.clear_btn.config(state=tk.NORMAL)
            self.save_btn.config(state=tk.NORMAL)
            self.status_var.set("Path generated")
            
        except Exception as e:
            self.logger.error(f"Error generating path: {e}")
            messagebox.showerror("Error", "Failed to generate path")
            
    def clear_path(self):
        """Clear the generated path."""
        self.path_points = []
        self.path_text.config(state=tk.NORMAL)
        self.path_text.delete(1.0, tk.END)
        self.path_text.config(state=tk.DISABLED)
        self.clear_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.status_var.set("Path cleared")
        
    def save_path(self):
        """Save the generated path to a JSON file."""
        try:
            file_path = tk.filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if file_path:
                with open(file_path, 'w') as file:
                    json.dump(self.path_points, file, indent=4)
                self.status_var.set(f"Path saved to {file_path}")
        except Exception as e:
            self.logger.error(f"Error saving path: {e}")
            messagebox.showerror("Error", "Failed to save path")
            
    def generate_snake_path(self, rows: int, cols: int, x_step: float, y_step: float):
        """Generate snake pattern path."""
        for row in range(rows):
            for col in range(cols):
                # Reverse direction on odd rows
                col_idx = cols - 1 - col if row % 2 else col
                
                x = self.corners['A1']['X'] + (col_idx * x_step)
                y = self.corners['A1']['Y'] + (row * y_step)
                z = self.corners['A1']['Z']
                
                well_id = f"{WELL_PLATE['ROW_LABELS'][row]}{WELL_PLATE['COL_LABELS'][col_idx]}"
                
                self.path_points.append({
                    'X': x,
                    'Y': y,
                    'Z': z,
                    'well': well_id
                })

    def generate_raster_path(self, rows: int, cols: int, x_step: float, y_step: float):
        """Generate raster pattern path."""
        for row in range(rows):
            for col in range(cols):
                x = self.corners['A1']['X'] + (col * x_step)
                y = self.corners['A1']['Y'] + (row * y_step)
                z = self.corners['A1']['Z']
                
                well_id = f"{WELL_PLATE['ROW_LABELS'][row]}{WELL_PLATE['COL_LABELS'][col]}"
                
                self.path_points.append({
                    'X': x,
                    'Y': y,
                    'Z': z,
                    'well': well_id
                })

    def update_path_display(self):
        """Update the path display text widget."""
        self.path_text.config(state=tk.NORMAL)
        self.path_text.delete(1.0, tk.END)
        
        for i, point in enumerate(self.path_points, 1):
            self.path_text.insert(tk.END, 
                f"Point {i}: Well {point['well']} - "
                f"X: {point['X']:.2f}, Y: {point['Y']:.2f}, Z: {point['Z']:.2f}\n"
            )
            
        self.path_text.config(state=tk.DISABLED)

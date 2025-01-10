"""
Experiment control interface for automated microscope operations.
Handles experiment setup, execution, and data collection.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import os
import time
from typing import Optional, Dict, Any
from datetime import datetime

from ..config import FILE_SETTINGS

class ExperimentGUI:
    """GUI class for experiment control and automation."""
    
    def __init__(self, root: tk.Tk, checkbox_var: tk.BooleanVar):
        """
        Initialize the experiment control interface.
        
        Args:
            root: Parent window
            checkbox_var: Checkbox state variable from main GUI
        """
        self.logger = logging.getLogger(__name__)
        self.root = root
        self.checkbox_var = checkbox_var
        self.window: Optional[tk.Toplevel] = None
        
        # Initialize experiment variables
        self.save_folder = FILE_SETTINGS['DEFAULT_SAVE_FOLDER']
        self.file_prefix = FILE_SETTINGS['DEFAULT_FILE_PREFIX']
        self.is_running = False
        self.start_time: Optional[float] = None
        self.elapsed_time = 0
        
        # Initialize GUI state variables
        self.duration = {
            'hours': tk.StringVar(value="0"),
            'minutes': tk.StringVar(value="0"),
            'seconds': tk.StringVar(value="0")
        }
        self.status_var = tk.StringVar(value="Ready")
        self.folder_path = tk.StringVar(value=self.save_folder)
        self.prefix_var = tk.StringVar(value=self.file_prefix)
        self.interval_var = tk.StringVar(value="1.0")  # Time between captures in seconds

    def init_gui(self):
        """Initialize the experiment control window and its components."""
        # Create new window if not exists
        if self.window is None:
            self.window = tk.Toplevel(self.root)
            self.window.title("Experiment Control")
            self.window.protocol("WM_DELETE_WINDOW", self.stop)
            
            # Create main container
            main_frame = ttk.Frame(self.window, padding="10")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Folder selection section
            self.create_folder_section(main_frame)
            
            # File naming section
            self.create_file_section(main_frame)
            
            # Duration section
            self.create_duration_section(main_frame)
            
            # Interval section
            self.create_interval_section(main_frame)
            
            # Control buttons section
            self.create_control_section(main_frame)
            
            # Status section
            self.create_status_section(main_frame)

    def create_folder_section(self, parent: ttk.Frame):
        """Create the folder selection section."""
        folder_frame = ttk.LabelFrame(parent, text="Save Location", padding="5")
        folder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        folder_entry = ttk.Entry(
            folder_frame,
            textvariable=self.folder_path,
            width=50
        )
        folder_entry.grid(row=0, column=0, padx=5)
        
        browse_button = ttk.Button(
            folder_frame,
            text="Browse...",
            command=self.select_folder
        )
        browse_button.grid(row=0, column=1, padx=5)

    def create_file_section(self, parent: ttk.Frame):
        """Create the file naming section."""
        file_frame = ttk.LabelFrame(parent, text="File Naming", padding="5")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(file_frame, text="Prefix:").grid(row=0, column=0, padx=5)
        prefix_entry = ttk.Entry(
            file_frame,
            textvariable=self.prefix_var,
            width=30
        )
        prefix_entry.grid(row=0, column=1, padx=5)
        
        # Preview label
        ttk.Label(file_frame, text="Example:").grid(row=1, column=0, padx=5)
        self.preview_var = tk.StringVar()
        self.update_filename_preview()
        preview_label = ttk.Label(file_frame, textvariable=self.preview_var)
        preview_label.grid(row=1, column=1, padx=5)

    def create_duration_section(self, parent: ttk.Frame):
        """Create the duration control section."""
        time_frame = ttk.LabelFrame(parent, text="Duration", padding="5")
        time_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # Hours
        hours_frame = ttk.Frame(time_frame)
        hours_frame.grid(row=0, column=0, padx=5)
        ttk.Label(hours_frame, text="Hours:").pack()
        ttk.Entry(
            hours_frame,
            textvariable=self.duration['hours'],
            width=5
        ).pack()
        
        # Minutes
        minutes_frame = ttk.Frame(time_frame)
        minutes_frame.grid(row=0, column=1, padx=5)
        ttk.Label(minutes_frame, text="Minutes:").pack()
        ttk.Entry(
            minutes_frame,
            textvariable=self.duration['minutes'],
            width=5
        ).pack()
        
        # Seconds
        seconds_frame = ttk.Frame(time_frame)
        seconds_frame.grid(row=0, column=2, padx=5)
        ttk.Label(seconds_frame, text="Seconds:").pack()
        ttk.Entry(
            seconds_frame,
            textvariable=self.duration['seconds'],
            width=5
        ).pack()

    def create_interval_section(self, parent: ttk.Frame):
        """Create the interval control section."""
        interval_frame = ttk.LabelFrame(parent, text="Capture Interval", padding="5")
        interval_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(interval_frame, text="Interval (seconds):").pack(side=tk.LEFT, padx=5)
        ttk.Entry(
            interval_frame,
            textvariable=self.interval_var,
            width=10
        ).pack(side=tk.LEFT, padx=5)

    def create_control_section(self, parent: ttk.Frame):
        """Create the control buttons section."""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=4, column=0, pady=10)
        
        self.start_button = ttk.Button(
            control_frame,
            text="Start Experiment",
            command=self.start_experiment
        )
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(
            control_frame,
            text="Stop Experiment",
            command=self.stop_experiment,
            state=tk.DISABLED
        )
        self.stop_button.grid(row=0, column=1, padx=5)

    def create_status_section(self, parent: ttk.Frame):
        """Create the status display section."""
        status_frame = ttk.LabelFrame(parent, text="Status", padding="5")
        status_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.time_var = tk.StringVar(value="Elapsed: 0:00:00")
        time_label = ttk.Label(status_frame, textvariable=self.time_var)
        time_label.pack()
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack()

    def select_folder(self):
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(initialdir=self.save_folder)
        if folder:
            self.save_folder = folder
            self.folder_path.set(folder)
            self.update_filename_preview()

    def update_filename_preview(self):
        """Update the filename preview."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        preview = f"{self.prefix_var.get()}_{timestamp}{FILE_SETTINGS['IMAGE_FORMAT']}"
        self.preview_var.set(preview)

    def validate_settings(self) -> bool:
        """
        Validate experiment settings.
        
        Returns:
            bool: True if settings are valid, False otherwise
        """
        try:
            # Check save folder
            if not self.folder_path.get():
                raise ValueError("Please select a save folder")
            
            # Check file prefix
            if not self.prefix_var.get():
                raise ValueError("Please enter a file prefix")
            
            # Check duration
            hours = int(self.duration['hours'].get())
            minutes = int(self.duration['minutes'].get())
            seconds = int(self.duration['seconds'].get())
            
            if hours == 0 and minutes == 0 and seconds == 0:
                raise ValueError("Please set a duration greater than 0")
            
            # Check interval
            interval = float(self.interval_var.get())
            if interval <= 0:
                raise ValueError("Interval must be greater than 0")
            
            return True
            
        except ValueError as e:
            messagebox.showerror("Invalid Settings", str(e))
            return False
        
        except Exception as e:
            self.logger.error(f"Error validating settings: {e}")
            messagebox.showerror("Error", "Invalid settings")
            return False

    def start_experiment(self):
        """Start the experiment."""
        if not self.validate_settings():
            return
            
        try:
            self.is_running = True
            self.start_time = time.time()
            self.elapsed_time = 0
            
            # Update UI
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set("Experiment running...")
            
            # Start time update
            self.update_time()
            
        except Exception as e:
            self.logger.error(f"Error starting experiment: {e}")
            self.stop_experiment()
            messagebox.showerror("Error", "Failed to start experiment")

    def stop_experiment(self):
        """Stop the experiment."""
        self.is_running = False
        self.start_time = None
        
        # Update UI
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Experiment stopped")

    def update_time(self):
        """Update the elapsed time display."""
        if self.is_running and self.start_time is not None:
            self.elapsed_time = int(time.time() - self.start_time)
            hours = self.elapsed_time // 3600
            minutes = (self.elapsed_time % 3600) // 60
            seconds = self.elapsed_time % 60
            
            self.time_var.set(f"Elapsed: {hours}:{minutes:02d}:{seconds:02d}")
            
            # Schedule next update
            self.window.after(1000, self.update_time)

    def start(self):
        """Show the experiment control window."""
        if self.window is None:
            self.init_gui()

    def stop(self):
        """Close the experiment control window."""
        if self.is_running:
            self.stop_experiment()
        if self.window is not None:
            self.window.destroy()
            self.window = None
            self.checkbox_var.set(False)

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional, Callable
import json

from microscope.hardware.camera import Camera  # Import the Camera class
from microscope.hardware.gcode import GCode  # Import the GCode class
from microscope.config import FILE_SETTINGS
from microscope.utils.experiment import Experiment

class ExperimentGUI:
    def __init__(self, root: tk.Tk, checkbox_var: tk.BooleanVar, camera: Camera, gcode: GCode):
        self.logger = logging.getLogger(__name__)
        self.root = root
        self.checkbox_var = checkbox_var
        self.camera = camera
        self.gcode = gcode
        self.window: Optional[tk.Toplevel] = None
        self.is_running = False

        # Initialize experiment variables
        self.experiment = Experiment(camera=self.camera, gcode=self.gcode)
        self.experiment.set_callbacks(
            status_callback=self.update_status,
            progress_callback=self.update_progress,
            error_callback=self.handle_error
        )
        
        # Initialize GUI state variables
        self.duration = {
            'hours': tk.StringVar(value="0"),
            'minutes': tk.StringVar(value="0"),
            'seconds': tk.StringVar(value="0")
        }
        self.status_var = tk.StringVar(value="Ready")
        self.save_folder = "images"  # Default save folder
        self.folder_path = tk.StringVar(value=self.save_folder)
        self.prefix_var = tk.StringVar(value="")
        self.pause_time_var = tk.StringVar(value="1.0")  # Pause time after each movement in seconds
        self.json_file_path = tk.StringVar(value="path.json")  # Default JSON file path
        
    def set_debug(self, debug: bool):
        self.experiment.set_debug(debug)

    def init_gui(self):
        if self.window is None:
            self.window = tk.Toplevel(self.root)
            self.window.title("Experiment Control")
            self.window.protocol("WM_DELETE_WINDOW", self.stop)
            
            main_frame = ttk.Frame(self.window, padding="10")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            self.create_folder_section(main_frame)
            self.create_file_section(main_frame)
            self.create_json_file_section(main_frame)
            self.create_duration_section(main_frame)
            self.create_pause_time_section(main_frame)
            self.create_control_section(main_frame)
            self.create_status_section(main_frame)

    def create_folder_section(self, parent: ttk.Frame):
        folder_frame = ttk.LabelFrame(parent, text="Save Location", padding="5")
        folder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_path, width=50)
        folder_entry.grid(row=0, column=0, padx=5)
        
        browse_button = ttk.Button(folder_frame, text="Browse...", command=self.select_folder)
        browse_button.grid(row=0, column=1, padx=5)

    def create_file_section(self, parent: ttk.Frame):
        file_frame = ttk.LabelFrame(parent, text="File Naming", padding="5")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(file_frame, text="Prefix:").grid(row=0, column=0, padx=5)
        prefix_entry = ttk.Entry(file_frame, textvariable=self.prefix_var, width=30)
        prefix_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(file_frame, text="Example:").grid(row=1, column=0, padx=5)
        self.preview_var = tk.StringVar()
        self.update_filename_preview()
        preview_label = ttk.Label(file_frame, textvariable=self.preview_var)
        preview_label.grid(row=1, column=1, padx=5)

    def create_json_file_section(self, parent: ttk.Frame):
        json_frame = ttk.LabelFrame(parent, text="JSON File", padding="5")
        json_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        json_entry = ttk.Entry(json_frame, textvariable=self.json_file_path, width=50)
        json_entry.grid(row=0, column=0, padx=5)
        
        json_button = ttk.Button(json_frame, text="Select JSON File...", command=self.select_json_file)
        json_button.grid(row=0, column=1, padx=5)

    def create_duration_section(self, parent: ttk.Frame):
        time_frame = ttk.LabelFrame(parent, text="Duration", padding="5")
        time_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        hours_frame = ttk.Frame(time_frame)
        hours_frame.grid(row=0, column=0, padx=5)
        ttk.Label(hours_frame, text="Hours:").pack()
        ttk.Entry(hours_frame, textvariable=self.duration['hours'], width=5).pack()
        
        minutes_frame = ttk.Frame(time_frame)
        minutes_frame.grid(row=0, column=1, padx=5)
        ttk.Label(minutes_frame, text="Minutes:").pack()
        ttk.Entry(minutes_frame, textvariable=self.duration['minutes'], width=5).pack()
        
        seconds_frame = ttk.Frame(time_frame)
        seconds_frame.grid(row=0, column=2, padx=5)
        ttk.Label(seconds_frame, text="Seconds:").pack()
        ttk.Entry(seconds_frame, textvariable=self.duration['seconds'], width=5).pack()

    def create_pause_time_section(self, parent: ttk.Frame):
        pause_time_frame = ttk.LabelFrame(parent, text="Pause Time", padding="5")
        pause_time_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(pause_time_frame, text="Pause Time (seconds):").pack(side=tk.LEFT, padx=5)
        ttk.Entry(pause_time_frame, textvariable=self.pause_time_var, width=10).pack(side=tk.LEFT, padx=5)

    def create_control_section(self, parent: ttk.Frame):
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=5, column=0, pady=10)
        
        self.start_button = ttk.Button(control_frame, text="Start Experiment", command=self.start_experiment)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.pause_button = ttk.Button(control_frame, text="Pause Experiment", command=self.pause_experiment, state=tk.DISABLED)
        self.pause_button.grid(row=0, column=1, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop Experiment", command=self.stop_experiment, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2, padx=5)

    def create_status_section(self, parent: ttk.Frame):
        status_frame = ttk.LabelFrame(parent, text="Status", padding="5")
        status_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.time_var = tk.StringVar(value="Elapsed: 0:00:00")
        time_label = ttk.Label(status_frame, textvariable=self.time_var)
        time_label.pack()
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack()

    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_folder)
        if folder:
            self.save_folder = folder
            self.folder_path.set(folder)
            self.update_filename_preview()

    def select_json_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], initialdir=".")
        if file_path:
            self.json_file_path.set(file_path)
        else:
            self.json_file_path.set("path.json")  # Set default JSON file path if no file selected

    def update_filename_preview(self):
        well = "A1"  # Example well name
        iteration = 1  # Example iteration number
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        preview = f"{well}_{iteration:04d}_{timestamp}.jpg"
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
            
            # Check pause time
            pause_time = float(self.pause_time_var.get())
            if pause_time <= 0:
                raise ValueError("Pause time must be greater than 0")
            
            # Check JSON file path
            json_file_path = self.json_file_path.get()
            if not json_file_path:
                raise ValueError("Please select a JSON file")
            if not os.path.isfile(json_file_path):
                raise ValueError(f"JSON file not found: {json_file_path}")
            
            return True
            
        except ValueError as e:
            messagebox.showerror("Invalid Settings", str(e))
            return False
        
        except Exception as e:
            self.logger.error(f"Error validating settings: {e}")
            messagebox.showerror("Error", "Invalid settings")
            return False

    def start_experiment(self):
        if not self.validate_settings():
            return
        try:
            config = {
                'path_points': self.load_path_points(),
                'pause_time': float(self.pause_time_var.get()),
                'duration': self.get_total_duration(),
                'save_folder': self.folder_path.get(),
                'file_prefix': self.prefix_var.get()
            }
            self.experiment.configure(config)
            if self.experiment.is_paused:
                self.experiment.resume()
            else:
                self.experiment.start()
            self.is_running = True
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set("Experiment running...")
            self.update_time()
        except Exception as e:
            self.logger.error(f"Error starting experiment: {e}")
            self.stop_experiment()
            messagebox.showerror("Error", "Failed to start experiment")

    def pause_experiment(self):
        if self.is_running:
            self.experiment.pause()
            self.is_running = False
            self.pause_button.config(state=tk.DISABLED)
            self.start_button.config(state=tk.NORMAL)
            self.status_var.set("Experiment paused")

    def stop_experiment(self):
        self.experiment.stop()
        self.is_running = False  # Add this line to set is_running to False when the experiment stops
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Experiment stopped")

    def update_time(self):
        if self.is_running and self.experiment.is_running:
            elapsed_time = self.experiment.get_elapsed_time()
            if elapsed_time is not None:
                hours = int(elapsed_time // 3600)
                minutes = int((elapsed_time % 3600) // 60)
                seconds = int(elapsed_time % 60)
                
                self.time_var.set(f"Elapsed: {hours:02d}:{minutes:02d}:{seconds:02d}")
                
                self.window.after(1000, self.update_time)
            
    def update_status(self, status: str):
        self.status_var.set(status)

    def update_progress(self, current: int, total: int):
        progress = f"Progress: {current}/{total}"
        self.status_var.set(progress)

    def handle_error(self, error: str):
        messagebox.showerror("Experiment Error", error)
        self.stop_experiment()

    def load_path_points(self) -> List[Dict[str, float]]:
        with open(self.json_file_path.get(), 'r') as f:
            return json.load(f)

    def get_total_duration(self) -> float:
        hours = int(self.duration['hours'].get())
        minutes = int(self.duration['minutes'].get())
        seconds = int(self.duration['seconds'].get())
        return hours * 3600 + minutes * 60 + seconds

    def start(self):
        if self.window is None:
            self.init_gui()

    def stop(self):
        if self.is_running:
            self.stop_experiment()
        if self.window is not None:
            self.window.destroy()
            self.window = None
            self.checkbox_var.set(False)

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import time
import cv2

class ExperimentGUI:
    def __init__(self, root, checkbox_var, gcode=None, camera=None):
        self.root = root
        self.window = None
        self.checkbox_var = checkbox_var
        self.save_folder = ""
        self.is_running = False
        self.file_prefix = "fileprefix"
        self.current_path = None
        self.gcode = gcode
        self.camera = camera
        
    def init_gui(self):
        self.window = tk.Toplevel(self.root)
        self.window.title("Experiment Control")
        self.window.protocol("WM_DELETE_WINDOW", self.stop)

        # Create main frame
        main_frame = tk.Frame(self.window, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Path selection
        self.create_path_section(main_frame)
        
        # Folder selection
        self.create_folder_section(main_frame)
        
        # File prefix
        self.create_prefix_section(main_frame)
        
        # Duration settings
        self.create_duration_section(main_frame)
        
        # Interval settings
        self.create_interval_section(main_frame)
        
        # Control buttons
        self.create_control_section(main_frame)
        
        # Status display
        self.status_var = tk.StringVar(value="Ready")
        status_label = tk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(pady=5)
        
        # Current well display
        self.well_var = tk.StringVar(value="Current Well: --")
        well_label = tk.Label(main_frame, textvariable=self.well_var)
        well_label.pack(pady=5)

    def create_path_section(self, parent):
        path_frame = tk.LabelFrame(parent, text="Path Selection", padx=5, pady=5)
        path_frame.pack(fill=tk.X, pady=5)

        self.path_var = tk.StringVar()
        path_entry = tk.Entry(path_frame, textvariable=self.path_var, width=50)
        path_entry.pack(side=tk.LEFT, padx=5)

        path_button = tk.Button(path_frame, text="Load Path...", command=self.load_path)
        path_button.pack(side=tk.LEFT, padx=5)

    def create_interval_section(self, parent):
        interval_frame = tk.LabelFrame(parent, text="Capture Interval", padx=5, pady=5)
        interval_frame.pack(fill=tk.X, pady=5)
        
        self.interval_var = tk.StringVar(value="5")
        tk.Label(interval_frame, text="Minutes:").pack(side=tk.LEFT)
        tk.Entry(interval_frame, textvariable=self.interval_var, width=5).pack(side=tk.LEFT, padx=5)

    def load_path(self):
        """Load a saved well plate path"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Load Well Plate Path"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    path_data = json.load(f)
                    
                self.current_path = path_data['path']
                self.well_positions = path_data['well_positions']
                self.path_var.set(filename)
                
                self.status_var.set(f"Loaded path with {len(self.current_path)} points")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load path: {str(e)}")

    def start_experiment(self):
        if not self.current_path:
            messagebox.showerror("Error", "Please load a path first")
            return

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
            interval_minutes = float(self.interval_var.get())
            
            if hours == 0 and minutes == 0 and seconds == 0:
                messagebox.showerror("Error", "Please set a duration greater than 0")
                return
            
            if interval_minutes <= 0:
                messagebox.showerror("Error", "Please set an interval greater than 0")
                return
                
            self.is_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set("Experiment running...")
            
            # Start the experiment loop
            self.run_experiment(hours, minutes, seconds, interval_minutes)
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for duration and interval")
            return

    def run_experiment(self, hours, minutes, seconds, interval_minutes):
        total_seconds = hours * 3600 + minutes * 60 + seconds
        interval_seconds = interval_minutes * 60
        end_time = time.time() + total_seconds
        next_capture_time = time.time()
        
        def update():
            if not self.is_running:
                return
                
            current_time = time.time()
            
            # Check if it's time for the next capture
            if current_time >= next_capture_time:
                self.capture_well_images()
                next_capture_time = current_time + interval_seconds
            
            # Update remaining time display
            if current_time < end_time:
                remaining = end_time - current_time
                hours_left = int(remaining // 3600)
                minutes_left = int((remaining % 3600) // 60)
                seconds_left = int(remaining % 60)
                
                self.status_var.set(
                    f"Running... Time remaining: {hours_left:02d}:{minutes_left:02d}:{seconds_left:02d}"
                )
                
                # Schedule next update
                self.window.after(1000, update)
            else:
                self.stop_experiment()
                
        # Start the update loop
        update()

    def capture_well_images(self):
        """Capture images for all wells in the path"""
        for i, point in enumerate(self.current_path):
            if not self.is_running:
                break
                
            # Move to the well position
            if self.gcode:
                self.gcode.move_xyz(point['X'], point['Y'], point['Z'])
                time.sleep(0.5)  # Wait for movement to complete
            
            # Update current well display
            well_name = self.get_well_name(i)
            self.well_var.set(f"Current Well: {well_name}")
            
            # Capture image if camera is available
            if self.camera:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"{self.file_prefix}_{well_name}_{timestamp}.jpg"
                filepath = os.path.join(self.save_folder, filename)
                
                frame = self.camera.get_frame()
                if frame is not None:
                    cv2.imwrite(filepath, frame)

    def get_well_name(self, index):
        """Convert numerical index to well name (A1, A2, etc.)"""
        row = chr(65 + (index // 8))  # A, B, C, ...
        col = (index % 8) + 1         # 1, 2, 3, ...
        return f"{row}{col}"

    def create_folder_section(self, parent):
        folder_frame = tk.LabelFrame(parent, text="Save Location", padx=5, pady=5)
        folder_frame.pack(fill=tk.X, pady=5)

        self.folder_path = tk.StringVar()
        folder_entry = tk.Entry(folder_frame, textvariable=self.folder_path, width=50)
        folder_entry.pack(side=tk.LEFT, padx=5)

        folder_button = tk.Button(folder_frame, text="Browse...", command=self.select_folder)
        folder_button.pack(side=tk.LEFT, padx=5)

    def create_prefix_section(self, parent):
        prefix_frame = tk.Frame(parent)
        prefix_frame.pack(fill=tk.X, pady=5)

        tk.Label(prefix_frame, text="File Prefix:").pack(side=tk.LEFT, padx=5)
        self.prefix_var = tk.StringVar()
        prefix_entry = tk.Entry(prefix_frame, textvariable=self.prefix_var, width=30)
        prefix_entry.pack(side=tk.LEFT, padx=5)

    def create_duration_section(self, parent):
        time_frame = tk.LabelFrame(parent, text="Duration", padx=5, pady=5)
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

    def create_control_section(self, parent):
        button_frame = tk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)

        self.start_button = tk.Button(button_frame, text="Start Experiment",
                                    command=self.start_experiment)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(button_frame, text="Stop Experiment",
                                   command=self.stop_experiment, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

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
            
            # Start the experiment loop
            self.run_experiment(hours, minutes, seconds)
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for duration")
            return

    def run_experiment(self, hours, minutes, seconds):
        total_seconds = hours * 3600 + minutes * 60 + seconds
        end_time = time.time() + total_seconds
        
        def update():
            if not self.is_running:
                return
                
            current_time = time.time()
            if current_time < end_time:
                remaining = end_time - current_time
                hours_left = int(remaining // 3600)
                minutes_left = int((remaining % 3600) // 60)
                seconds_left = int(remaining % 60)
                
                self.status_var.set(
                    f"Running... Time remaining: {hours_left:02d}:{minutes_left:02d}:{seconds_left:02d}"
                )
                
                # Schedule the next update
                self.window.after(1000, update)
            else:
                self.stop_experiment()
                
        # Start the update loop
        update()

    def stop_experiment(self):
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Experiment stopped")

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
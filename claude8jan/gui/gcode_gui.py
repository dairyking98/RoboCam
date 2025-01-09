import tkinter as tk

class GCodeGUI:
    def __init__(self, root, gcode):
        self.root = root
        self.gcode = gcode
        self.root.title("GCode Control")
        
        self.setup_gui()
        
    def setup_gui(self):
        # Create main frame
        self.frame = tk.Frame(self.root)
        self.frame.pack(padx=10, pady=10)

        # Coordinate controls
        self.create_coordinate_controls()
        
        # Step size controls
        self.create_step_size_controls()
        
        # Movement controls
        self.create_movement_controls()
        
        # Machine controls
        self.create_machine_controls()
        
        # Settings controls
        self.create_settings_controls()

        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_coordinate_controls(self):
        # XYZ Coordinates Entry
        for i, axis in enumerate(['X', 'Y', 'Z']):
            label = tk.Label(self.frame, text=f"{axis}:")
            label.grid(row=i, column=0, padx=5, pady=5)
            
            entry = tk.Entry(self.frame)
            entry.grid(row=i, column=1, padx=5, pady=5)
            entry.insert(0, str(self.gcode.current_position[axis]))
            setattr(self, f"{axis.lower()}_entry", entry)

        # Send coordinates button
        self.send_button = tk.Button(
            self.frame,
            text="Send Absolute Coordinates",
            command=self.send_to_printer
        )
        self.send_button.grid(row=3, column=0, columnspan=2, pady=10)

    def create_step_size_controls(self):
        self.step_size = tk.DoubleVar(value=1.0)
        sizes = [(0.1, "0.1 mm"), (1.0, "1 mm"), (10.0, "10 mm")]
        
        for i, (value, text) in enumerate(sizes):
            rb = tk.Radiobutton(
                self.frame,
                text=text,
                variable=self.step_size,
                value=value
            )
            rb.grid(row=4, column=i, padx=5, pady=5)

    def create_movement_controls(self):
        move_frame = tk.Frame(self.frame)
        move_frame.grid(row=5, column=0, columnspan=3, pady=10)

        # Movement buttons layout
        buttons = [
            ('Y+', 0, 1, lambda: self.move_increment('Y', 1)),
            ('X-', 1, 0, lambda: self.move_increment('X', -1)),
            ('X+', 1, 2, lambda: self.move_increment('X', 1)),
            ('Y-', 2, 1, lambda: self.move_increment('Y', -1)),
            ('Z+', 1, 3, lambda: self.move_increment('Z', 1)),
            ('Z-', 1, 4, lambda: self.move_increment('Z', -1))
        ]

        for text, row, col, command in buttons:
            tk.Button(move_frame, text=text, command=command).grid(
                row=row, column=col, padx=5, pady=5
            )

    def create_machine_controls(self):
        commands_frame = tk.Frame(self.frame)
        commands_frame.grid(row=6, column=0, columnspan=3, pady=10)

        tk.Button(
            commands_frame,
            text="Home All Axes",
            command=self.home_axes
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            commands_frame,
            text="Enable Steppers",
            command=self.gcode.enable_steppers
        ).grid(row=0, column=1, padx=5)

        tk.Button(
            commands_frame,
            text="Disable Steppers",
            command=self.gcode.disable_steppers
        ).grid(row=0, column=2, padx=5)

    def create_settings_controls(self):
        settings = [
            ("Feedrate (mm/min):", "feedrate"),
            ("Acceleration (mm/s²):", "acceleration"),
            ("Jerk (mm/s):", "jerk")
        ]

        for i, (label_text, attr) in enumerate(settings):
            tk.Label(self.frame, text=label_text).grid(
                row=7+i, column=0, padx=5, pady=5
            )
            
            entry = tk.Entry(self.frame)
            entry.grid(row=7+i, column=1, padx=5, pady=5)
            entry.insert(0, str(getattr(self.gcode, attr)))
            setattr(self, f"{attr}_entry", entry)

        tk.Button(
            self.frame,
            text="Apply Settings",
            command=self.apply_settings
        ).grid(row=10, column=0, columnspan=2, pady=10)

    def move_increment(self, axis, direction):
        step = self.step_size.get() * direction
        current = self.gcode.current_position[axis]
        new_pos = max(0, current + step)
        
        if axis == 'X':
            self.gcode.move_xyz(new_pos, self.gcode.current_position['Y'], self.gcode.current_position['Z'])
        elif axis == 'Y':
            self.gcode.move_xyz(self.gcode.current_position['X'], new_pos, self.gcode.current_position['Z'])
        elif axis == 'Z':
            self.gcode.move_xyz(self.gcode.current_position['X'], self.gcode.current_position['Y'], new_pos)
            
        self.update_position_displays()

    def update_position_displays(self):
        for axis in ['X', 'Y', 'Z']:
            entry = getattr(self, f"{axis.lower()}_entry")
            entry.delete(0, tk.END)
            entry.insert(0, str(self.gcode.current_position[axis]))

    def home_axes(self):
        self.gcode.home_all_axes()
        self.update_position_displays()

    def send_to_printer(self):
        try:
            x = float(self.x_entry.get())
            y = float(self.y_entry.get())
            z = float(self.z_entry.get())
            self.gcode.move_xyz(x, y, z)
        except ValueError:
            print("Invalid coordinates!")

    def apply_settings(self):
        try:
            self.gcode.set_feedrate(float(self.feedrate_entry.get()))
            self.gcode.set_acceleration(float(self.acceleration_entry.get()))
            self.gcode.set_jerk(float(self.jerk_entry.get()))
        except ValueError:
            print("Invalid settings values!")

    def on_close(self):
        self.gcode.disable_steppers()
        self.root.destroy()
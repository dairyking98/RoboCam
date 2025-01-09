"""
Configuration settings for the microscope control application
"""

# GCode Settings
GCODE_DEFAULT_SETTINGS = {
    'baudrate': 250000,
    'feedrate': 2000,  # mm/min
    'acceleration': 5,  # mm/s²
    'jerk': 1,         # mm/s
    'timeout': 30,     # seconds
}

# Camera Settings
CAMERA_SETTINGS = {
    'preview_size': (640, 480),
    'capture_size': (1920, 1080),
    'framerate': 30,
    'rotation': 0,
    'zoom': 1.0,
}

# Overlay Settings
OVERLAY_SETTINGS = {
    'colors': {
        'red': (0, 0, 255),
        'green': (0, 255, 0),
        'blue': (255, 0, 0),
        'yellow': (0, 255, 255),
        'white': (255, 255, 255),
    },
    'default_color': 'red',
    'default_thickness': 2,
    'default_circle_size': 100,
}

# Well Plate Settings
WELL_PLATE_SETTINGS = {
    'rows': 6,  # A through F
    'columns': 8,  # 1 through 8
    'well_spacing': 9.0,  # mm
    'plate_size': (127.76, 85.48),  # mm (standard 96-well plate)
}

# File Settings
FILE_SETTINGS = {
    'default_save_directory': 'experiments',
    'image_format': 'jpg',
    'default_prefix': 'exp',
    'path_file_extension': '.path',
}

# GUI Settings
GUI_SETTINGS = {
    'window_sizes': {
        'main': '800x600',
        'gcode': '400x600',
        'camera': '1000x600',
        'pathfinder': '400x300',
        'experiment': '400x500',
    },
    'update_interval': 10,  # ms
    'status_update_interval': 1000,  # ms
}

# Experiment Settings
EXPERIMENT_SETTINGS = {
    'min_interval': 1,  # seconds
    'max_duration': 72,  # hours
    'default_duration': 24,  # hours
    'image_types': ['brightfield', 'fluorescence'],
}

# Error Messages
ERROR_MESSAGES = {
    'camera_init': "Failed to initialize camera",
    'gcode_connect': "Failed to connect to printer",
    'invalid_position': "Invalid position specified",
    'path_generation': "Failed to generate path",
    'file_save': "Failed to save file",
}

# Success Messages
SUCCESS_MESSAGES = {
    'camera_init': "Camera initialized successfully",
    'gcode_connect': "Connected to printer successfully",
    'path_generation': "Path generated successfully",
    'file_save': "File saved successfully",
    'experiment_start': "Experiment started successfully",
    'experiment_complete': "Experiment completed successfully",
}

# Debug Settings
DEBUG_SETTINGS = {
    'log_level': 'INFO',
    'log_to_file': True,
    'log_directory': 'logs',
    'print_gcode_commands': True,
    'print_camera_info': True,
}

# Hardware Limits
HARDWARE_LIMITS = {
    'max_x': 200,  # mm
    'max_y': 200,  # mm
    'max_z': 200,  # mm
    'min_feedrate': 100,   # mm/min
    'max_feedrate': 5000,  # mm/min
    'min_acceleration': 1,  # mm/s²
    'max_acceleration': 20, # mm/s²
}
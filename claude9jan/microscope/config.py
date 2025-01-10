"""
Configuration settings for the microscope control system.
All settings for GUI, hardware, and experiments are centralized here.
"""

# Camera settings
CAMERA_SETTINGS = {
    'WIDTH': 640,
    'HEIGHT': 480,
    'ROTATION': 0,
    'ZOOM': 1.0,
    'DEFAULT_OVERLAY_COLOR': 'red',
    'DEFAULT_OVERLAY_THICKNESS': 2,
    'DEFAULT_CIRCLE_SIZE': 100,
    'DEFAULT_WINDOW_SIZE': '1000x600'  # Width x Height for camera window
}

# GCode settings
GCODE_SETTINGS = {
    'BAUDRATE': 250000,
    'FEEDRATE': 2000,      # Default movement speed (mm/min)
    'ACCELERATION': 5,      # Default acceleration (mm/s²)
    'JERK': 1,             # Default jerk (mm/s)
    'TIMEOUT': {
        'HOMING': 30,      # Timeout for homing operations (seconds)
        'GENERAL': 10      # Timeout for general operations (seconds)
    }
}

# GUI settings
GUI_SETTINGS = {
    'MAIN_WINDOW_SIZE': '800x600',     # Width x Height for main window
    'STEP_SIZES': [0.1, 1.0, 10.0],    # Available step sizes for movement
    'DEFAULT_STEP_SIZE': 1.0           # Default step size
}

# File and directory settings
FILE_SETTINGS = {
    'DEFAULT_SAVE_FOLDER': 'data/',    # Default directory for saving files
    'DEFAULT_FILE_PREFIX': 'microscope',# Default prefix for saved files
    'IMAGE_FORMAT': '.jpg'             # Default image format
}

# Well plate configuration
WELL_PLATE = {
    'ROWS': 6,                         # Number of rows (A-F)
    'COLS': 8,                         # Number of columns (1-8)
    'ROW_LABELS': ['A', 'B', 'C', 'D', 'E', 'F'],
    'COL_LABELS': ['1', '2', '3', '4', '5', '6', '7', '8']
}

# Experiment settings
EXPERIMENT_SETTINGS = {
    'DEFAULT_INTERVAL': 1.0,           # Default time between captures (seconds)
    'MIN_INTERVAL': 0.1,               # Minimum allowed interval
    'MAX_INTERVAL': 3600,              # Maximum allowed interval
    'DEFAULT_DURATION': 3600,          # Default experiment duration (seconds)
    'MOVEMENT_DELAY': 0.5              # Delay after movement before capture (seconds)
}

# Error messages
ERROR_MESSAGES = {
    'CAMERA_INIT': "Failed to initialize camera",
    'GCODE_CONNECT': "Failed to connect to printer",
    'FILE_SAVE': "Failed to save file",
    'MOVEMENT': "Movement error occurred",
    'CAPTURE': "Image capture failed",
    'CONFIG': "Invalid configuration"
}

# Status messages
STATUS_MESSAGES = {
    'READY': "Ready",
    'RUNNING': "Running",
    'PAUSED': "Paused",
    'STOPPED': "Stopped",
    'ERROR': "Error",
    'COMPLETED': "Completed"
}

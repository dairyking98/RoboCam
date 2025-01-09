# README.md
# Microscope Control Application

## Overview
This application provides a graphical interface for controlling an automated microscope system built on a 3D printer platform. It supports automated well plate scanning, camera control, and experiment automation.

## Features
- GCode-based motion control
- Live camera preview with overlays
- Well plate path generation
- Automated experiment execution
- Configurable settings for all components

## Installation
1. Clone the repository:
```bash
git clone https://github.com/yourusername/microscope-control.git
cd microscope-control
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure
```
microscope_control/
├── README.md
├── requirements.txt
├── main.py
├── config/
│   └── settings.py
├── hardware/
│   ├── __init__.py
│   ├── gcode.py
│   └── camera.py
├── gui/
│   ├── __init__.py
│   ├── main_gui.py
│   ├── gcode_gui.py
│   ├── camera_gui.py
│   ├── experiment_gui.py
│   └── pathfinder_gui.py
└── utils/
    ├── __init__.py
    └── path_generator.py
```

## Usage
1. Start the application:
```bash
python main.py
```

2. Use the main GUI to:
   - Control microscope movement
   - Preview camera feed
   - Set up experiments
   - Generate well plate scanning paths

## Configuration
- All settings can be configured in `config/settings.py`
- Hardware limits and default values are defined in the settings file
- GUI layouts and behaviors can be customized in the settings

## Development
- The project uses a modular structure for easy maintenance
- Each component is isolated in its own module
- Settings are centralized in the config module
- Utility functions are available in the utils module

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License
This project is licensed under the MIT License - see the LICENSE file for details

## Author
Leonard Chau
- Created: 6 Jan 2025
- Last Updated: 8 Jan 2025
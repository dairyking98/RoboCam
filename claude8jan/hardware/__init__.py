# hardware/__init__.py
"""
Hardware control module for microscope control application.
Contains classes for controlling GCode-based motion and camera systems.
"""

from .gcode import GCode
from .camera import Camera, PiCamera

__all__ = ['GCode', 'Camera', 'PiCamera']

#!/usr/bin/env python3
"""
Microscope Control Application
Author: Leonard Chau
Creation Date: 6 Jan 2025
Last Updated: 8 Jan 2025
"""
import tkinter as tk
from gui import MainGUI
from hardware.gcode import GCode
from hardware.camera import Camera, PiCamera

def main():
    root = tk.Tk()
    try:
        # Initialize real hardware
        gcode = GCode()  # Real GCode controller
        camera = PiCamera()  # PiCamera for Raspberry Pi
        # Or camera = Camera() for USB camera
        
        app = MainGUI(root)
        app.start()
    except Exception as e:
        print(f"Error initializing hardware: {e}")
        root.destroy()

if __name__ == "__main__":
    main()
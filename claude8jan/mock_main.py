#!/usr/bin/env python3
"""
Microscope Control Application
Author: Leonard Chau
Creation Date: 6 Jan 2025
Last Updated: 8 Jan 2025
"""
import tkinter as tk
from gui import MainGUI  # Just import MainGUI
from hardware.mock_gcode import MockGCode
from hardware.mock_hardware import MockCamera

def main():
    root = tk.Tk()
    gcode = MockGCode()
    camera = MockCamera()
    app = MainGUI(root)
    app.start()

if __name__ == "__main__":
    main()
import os
import sys
# Add the parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import tkinter as tk
from microscope.gui.main_gui import App

def main():
    root = tk.Tk()
    app = App(root)
    app.start()

if __name__ == "__main__":
    main()

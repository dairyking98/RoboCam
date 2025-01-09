#!/usr/bin/env python3
import tkinter as tk
from app import App  # Changed import to use new app.py

def main():
    root = tk.Tk()
    app = App(root)
    app.start()

if __name__ == "__main__":
    main()
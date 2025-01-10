"""
Camera preview and control interface for microscope imaging.
Provides live preview and image adjustment controls.
"""

import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
from PIL import Image, ImageTk
import logging
from typing import Optional, Dict, Any

from ..config import CAMERA_SETTINGS
from ..hardware.camera import Camera

class CameraGUI:
    """GUI class for camera preview and control."""
    
    def __init__(self, root: tk.Toplevel):
        """
        Initialize the camera control interface.
        
        Args:
            root: Parent window
        """
        self.logger = logging.getLogger(__name__)
        self.root = root
        
        # Set window properties
        self.root.title("Camera Preview")
        self.root.geometry(CAMERA_SETTINGS['DEFAULT_WINDOW_SIZE'])
        
        # Initialize variables
        self.camera = None
        self.running = False
        self.preview_size = (640, 480)
        
        # Initialize camera settings
        self.rotation = tk.IntVar(value=CAMERA_SETTINGS['ROTATION'])
        self.zoom = tk.DoubleVar(value=CAMERA_SETTINGS['ZOOM'])
        
        # Initialize overlay settings
        self.crosshair_enabled = tk.BooleanVar(value=False)
        self.circle_enabled = tk.BooleanVar(value=False)
        self.overlay_color = tk.StringVar(value=CAMERA_SETTINGS['DEFAULT_OVERLAY_COLOR'])
        self.overlay_size = tk.IntVar(value=CAMERA_SETTINGS['DEFAULT_CIRCLE_SIZE'])
        self.overlay_thickness = tk.IntVar(value=CAMERA_SETTINGS['DEFAULT_OVERLAY_THICKNESS'])
        
        # Create GUI
        self.create_gui()
        
        # Initialize camera and start preview
        self.initialize_camera()
        
    def create_gui(self):
        """Create the GUI elements."""
        # Create main layout frames
        self.preview_frame = ttk.Frame(self.root)
        self.preview_frame.pack(side=tk.LEFT, padx=10, pady=10, expand=True)
        
        self.controls_frame = ttk.Frame(self.root)
        self.controls_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.Y)
        
        # Create preview label
        self.preview_label = ttk.Label(self.preview_frame)
        self.preview_label.pack(expand=True)
        
        # Create control panels
        self.create_camera_controls()
        self.create_overlay_controls()
        
    def create_camera_controls(self):
        """Create camera control panel."""
        camera_frame = ttk.LabelFrame(self.controls_frame, text="Camera Settings", padding="5")
        camera_frame.pack(fill=tk.X, pady=5)
        
        # Rotation control
        ttk.Label(camera_frame, text="Rotation:").pack(anchor=tk.W)
        for angle in [0, 90, 180, 270]:
            ttk.Radiobutton(
                camera_frame,
                text=f"{angle}°",
                variable=self.rotation,
                value=angle,
                command=self.update_camera_settings
            ).pack(anchor=tk.W)
        
        # Zoom control
        ttk.Label(camera_frame, text="Zoom:").pack(anchor=tk.W)
        zoom_scale = ttk.Scale(
            camera_frame,
            from_=1.0,
            to=4.0,
            orient=tk.HORIZONTAL,
            variable=self.zoom,
            command=lambda _: self.update_camera_settings()
        )
        zoom_scale.pack(fill=tk.X)
        
        # Camera controls
        control_frame = ttk.Frame(camera_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            control_frame,
            text="Reset Settings",
            command=self.reset_camera_settings
        ).pack(side=tk.LEFT, padx=5)
        
    def create_overlay_controls(self):
        """Create overlay control panel."""
        overlay_frame = ttk.LabelFrame(self.controls_frame, text="Overlay Settings", padding="5")
        overlay_frame.pack(fill=tk.X, pady=5)
        
        # Overlay toggles
        ttk.Checkbutton(
            overlay_frame,
            text="Crosshair",
            variable=self.crosshair_enabled
        ).pack(anchor=tk.W)
        
        ttk.Checkbutton(
            overlay_frame,
            text="Circle",
            variable=self.circle_enabled
        ).pack(anchor=tk.W)
        
        # Color selection
        ttk.Label(overlay_frame, text="Color:").pack(anchor=tk.W)
        colors = ["red", "green", "blue", "yellow", "white"]
        color_menu = ttk.OptionMenu(
            overlay_frame,
            self.overlay_color,
            self.overlay_color.get(),
            *colors
        )
        color_menu.pack(fill=tk.X)
        
        # Size control
        ttk.Label(overlay_frame, text="Circle Size:").pack(anchor=tk.W)
        size_scale = ttk.Scale(
            overlay_frame,
            from_=50,
            to=400,
            orient=tk.HORIZONTAL,
            variable=self.overlay_size
        )
        size_scale.pack(fill=tk.X)
        
        # Thickness control
        ttk.Label(overlay_frame, text="Line Thickness:").pack(anchor=tk.W)
        thickness_scale = ttk.Scale(
            overlay_frame,
            from_=1,
            to=5,
            orient=tk.HORIZONTAL,
            variable=self.overlay_thickness
        )
        thickness_scale.pack(fill=tk.X)
        
    def initialize_camera(self):
        """Initialize the camera and start preview."""
        try:
            self.camera = Camera()
            self.running = True
            self.update_preview()
        except Exception as e:
            self.logger.error(f"Error initializing camera: {e}")
            self.show_error("Failed to initialize camera")
            
    def update_preview(self):
        """Update the preview image."""
        if self.running and self.camera:
            try:
                # Capture frame
                frame = self.camera.capture_frame()
                if frame is not None:
                    # Apply camera transformations
                    frame = self.apply_camera_transformations(frame)
                    
                    # Draw overlays
                    frame = self.draw_overlays(frame)
                    
                    # Convert to PhotoImage
                    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = Image.fromarray(image)
                    photo = ImageTk.PhotoImage(image)
                    
                    # Update preview
                    self.preview_label.configure(image=photo)
                    self.preview_label.image = photo
                
                # Schedule next update
                self.root.after(10, self.update_preview)
                    
            except Exception as e:
                self.logger.error(f"Error updating preview: {e}")
                self.running = False
                self.show_error("Preview error")
                
    def apply_camera_transformations(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply rotation and zoom transformations to the frame.
        
        Args:
            frame: Input frame
            
        Returns:
            Transformed frame
        """
        # Apply rotation
        if self.rotation.get() != 0:
            rows, cols = frame.shape[:2]
            matrix = cv2.getRotationMatrix2D((cols/2, rows/2), self.rotation.get(), 1)
            frame = cv2.warpAffine(frame, matrix, (cols, rows))
        
        # Apply zoom
        if self.zoom.get() != 1.0:
            rows, cols = frame.shape[:2]
            zoom = self.zoom.get()
            crop_size = (int(cols/zoom), int(rows/zoom))
            x = (cols - crop_size[0]) // 2
            y = (rows - crop_size[1]) // 2
            frame = frame[y:y+crop_size[1], x:x+crop_size[0]]
            frame = cv2.resize(frame, (cols, rows))
            
        return frame
        
    def draw_overlays(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw overlays on the frame.
        
        Args:
            frame: Input frame
            
        Returns:
            Frame with overlays
        """
        height, width = frame.shape[:2]
        center_x = width // 2
        center_y = height // 2
        
        # Convert color name to BGR
        color_map = {
            "red": (0, 0, 255),
            "green": (0, 255, 0),
            "blue": (255, 0, 0),
            "yellow": (0, 255, 255),
            "white": (255, 255, 255)
        }
        color = color_map[self.overlay_color.get()]
        thickness = self.overlay_thickness.get()
        
        # Draw crosshair
        if self.crosshair_enabled.get():
            cv2.line(frame, (0, center_y), (width, center_y), color, thickness)
            cv2.line(frame, (center_x, 0), (center_x, height), color, thickness)
        
        # Draw circle
        if self.circle_enabled.get():
            radius = self.overlay_size.get() // 2
            cv2.circle(frame, (center_x, center_y), radius, color, thickness)
        
        return frame
        
    def update_camera_settings(self):
        """Update camera settings."""
        if self.camera:
            try:
                self.camera.set_rotation(self.rotation.get())
                self.camera.set_zoom(self.zoom.get())
            except Exception as e:
                self.logger.error(f"Error updating camera settings: {e}")
                self.show_error("Failed to update settings")
                
    def reset_camera_settings(self):
        """Reset camera settings to defaults."""
        self.rotation.set(CAMERA_SETTINGS['ROTATION'])
        self.zoom.set(CAMERA_SETTINGS['ZOOM'])
        self.update_camera_settings()
        
    def show_error(self, message: str):
        """Show error message to user."""
        tk.messagebox.showerror("Camera Error", message)
        
    def stop(self):
        """Stop the camera preview and release resources."""
        self.running = False
        if self.camera:
            self.camera.stop()
            self.camera = None

    def __del__(self):
        """Ensure camera is properly stopped on deletion."""
        self.stop()

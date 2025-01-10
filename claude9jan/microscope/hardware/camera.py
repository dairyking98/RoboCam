"""
Camera control module for microscope imaging.
Handles camera initialization, image capture, and settings management.
"""

import cv2
import numpy as np
from picamera2 import Picamera2
import logging
from typing import Optional, Dict, Any

from ..config import CAMERA_SETTINGS

class Camera:
    """Camera control class for microscope imaging."""
    
    def __init__(self):
        """Initialize the camera with specified settings."""
        self.logger = logging.getLogger(__name__)
        self.capture = cv2.VideoCapture(0)  # Initialize camera device 0
        
        if not self.capture.isOpened():
            self.logger.error("Could not open video device")
            raise Exception("Could not open video device")
            
        # Set camera properties
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_SETTINGS['WIDTH'])
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_SETTINGS['HEIGHT'])
        
        # Initialize state variables
        self.is_running = True
        self.rotation = CAMERA_SETTINGS['ROTATION']
        self.zoom = CAMERA_SETTINGS['ZOOM']

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Get a frame from the camera.
        
        Returns:
            numpy.ndarray or None: Captured frame if successful, None otherwise
        """
        try:
            ret, frame = self.capture.read()
            if not ret:
                self.logger.error("Failed to grab frame")
                return None
                
            # Apply any transformations
            frame = self.apply_transformations(frame)
            return frame
            
        except Exception as e:
            self.logger.error(f"Error capturing frame: {e}")
            return None

    def apply_transformations(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply rotation and zoom transformations to the frame.
        
        Args:
            frame: Input frame
            
        Returns:
            numpy.ndarray: Transformed frame
        """
        # Apply rotation if needed
        if self.rotation != 0:
            rows, cols = frame.shape[:2]
            matrix = cv2.getRotationMatrix2D((cols/2, rows/2), self.rotation, 1)
            frame = cv2.warpAffine(frame, matrix, (cols, rows))
        
        # Apply zoom if needed
        if self.zoom != 1.0:
            rows, cols = frame.shape[:2]
            crop_size = (int(cols/self.zoom), int(rows/self.zoom))
            x = (cols - crop_size[0]) // 2
            y = (rows - crop_size[1]) // 2
            frame = frame[y:y+crop_size[1], x:x+crop_size[0]]
            frame = cv2.resize(frame, (cols, rows))
            
        return frame

    def set_rotation(self, rotation: int) -> bool:
        """
        Set the image rotation.
        
        Args:
            rotation: Rotation angle in degrees (0, 90, 180, or 270)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if rotation in [0, 90, 180, 270]:
            self.rotation = rotation
            return True
        return False

    def set_zoom(self, zoom: float) -> bool:
        """
        Set the digital zoom factor.
        
        Args:
            zoom: Zoom factor (1.0 = no zoom)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if 1.0 <= zoom <= 4.0:
            self.zoom = zoom
            return True
        return False

    def get_settings(self) -> Dict[str, Any]:
        """
        Get current camera settings.
        
        Returns:
            dict: Dictionary containing current settings
        """
        return {
            'rotation': self.rotation,
            'zoom': self.zoom,
            'is_running': self.is_running
        }

    def save_image(self, filepath: str, frame: Optional[np.ndarray] = None) -> bool:
        """
        Save a frame to file.
        
        Args:
            filepath: Path to save the image
            frame: Frame to save. If None, captures new frame
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if frame is None:
                frame = self.get_frame()
                
            if frame is not None:
                return cv2.imwrite(filepath, frame)
            return False
            
        except Exception as e:
            self.logger.error(f"Error saving image: {e}")
            return False

    def stop(self):
        """Stop the camera and release resources."""
        self.is_running = False
        if self.capture:
            self.capture.release()

    def __del__(self):
        """Destructor to ensure camera is properly released."""
        self.stop()

"""
Experiment execution module.
Handles automated microscope operation and image capture.
"""

import os
import time
import logging
import threading
import cv2
from datetime import datetime
from typing import List, Dict, Optional, Callable
from queue import Queue
import json

from ..config import FILE_SETTINGS
from ..hardware.camera import Camera
from ..hardware.gcode import GCode

class Experiment:
    """Class to manage experiment execution and data collection."""
    
    def __init__(self, camera: Camera, gcode: GCode):
        """
        Initialize the experiment manager.
        
        Args:
            camera: Camera instance for image capture
            gcode: GCode instance for motion control
        """
        self.logger = logging.getLogger(__name__)
        self.camera = camera
        self.gcode = gcode
        
        # Experiment state
        self.is_running = False
        self.is_paused = False
        self.start_time: Optional[float] = None
        self.current_iteration = 0
        self.total_iterations = 0
        
        # Path and timing
        self.path_points: List[Dict[str, float]] = []
        self.interval = 1.0  # Time between captures in seconds
        self.duration = 0  # Total experiment duration in seconds
        
        # File management
        self.save_folder = FILE_SETTINGS['DEFAULT_SAVE_FOLDER']
        self.file_prefix = FILE_SETTINGS['DEFAULT_FILE_PREFIX']
        
        # Event handling
        self.status_callback: Optional[Callable[[str], None]] = None
        self.progress_callback: Optional[Callable[[int, int], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None
        
        # Threading
        self.experiment_thread: Optional[threading.Thread] = None
        self.command_queue: Queue = Queue()
        
    def configure(self, config: Dict):
        """
        Configure the experiment with the provided settings.
        
        Args:
            config: Dictionary containing experiment settings
                Required keys:
                - path_points: List of coordinates to visit
                - interval: Time between captures
                - duration: Total experiment duration
                - save_folder: Directory to save images
                - file_prefix: Prefix for saved files
        """
        try:
            self.path_points = config['path_points']
            self.interval = float(config['interval'])
            self.duration = float(config['duration'])
            self.save_folder = config['save_folder']
            self.file_prefix = config['file_prefix']
            
            # Validate configuration
            if not self.validate_configuration():
                raise ValueError("Invalid experiment configuration")
                
            # Create save directory if it doesn't exist
            os.makedirs(self.save_folder, exist_ok=True)
            
            # Save configuration file
            self.save_configuration()
            
            self.logger.info("Experiment configured successfully")
            self._update_status("Configuration complete")
            
        except Exception as e:
            self.logger.error(f"Error configuring experiment: {e}")
            self._handle_error(f"Configuration error: {str(e)}")
            raise
            
    def validate_configuration(self) -> bool:
        """
        Validate experiment configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        try:
            # Check path points
            if not self.path_points:
                raise ValueError("No path points defined")
                
            # Check timing
            if self.interval <= 0:
                raise ValueError("Interval must be positive")
            if self.duration <= 0:
                raise ValueError("Duration must be positive")
                
            # Check file paths
            if not os.path.exists(os.path.dirname(self.save_folder)):
                raise ValueError("Save directory parent does not exist")
                
            # Check hardware
            if not self.camera or not self.gcode:
                raise ValueError("Hardware not properly initialized")
                
            return True
            
        except Exception as e:
            self._handle_error(f"Validation error: {str(e)}")
            return False
            
    def save_configuration(self):
        """Save experiment configuration to file."""
        try:
            config = {
                'path_points': self.path_points,
                'interval': self.interval,
                'duration': self.duration,
                'file_prefix': self.file_prefix,
                'timestamp': datetime.now().isoformat()
            }
            
            config_path = os.path.join(self.save_folder, 'experiment_config.json')
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            self._handle_error(f"Failed to save configuration: {str(e)}")
            
    def start(self):
        """Start the experiment execution."""
        if self.is_running:
            self.logger.warning("Experiment already running")
            return
            
        try:
            # Initialize experiment state
            self.is_running = True
            self.is_paused = False
            self.start_time = time.time()
            self.current_iteration = 0
            self.total_iterations = int(self.duration / self.interval)
            
            # Start experiment thread
            self.experiment_thread = threading.Thread(target=self._experiment_loop)
            self.experiment_thread.daemon = True
            self.experiment_thread.start()
            
            self.logger.info("Experiment started")
            self._update_status("Experiment running")
            
        except Exception as e:
            self.logger.error(f"Error starting experiment: {e}")
            self._handle_error(f"Failed to start experiment: {str(e)}")
            self.stop()
            
    def pause(self):
        """Pause the experiment execution."""
        self.is_paused = True
        self._update_status("Experiment paused")
        
    def resume(self):
        """Resume the experiment execution."""
        self.is_paused = False
        self._update_status("Experiment resumed")
        
    def stop(self):
        """Stop the experiment execution."""
        self.is_running = False
        self.is_paused = False
        self._update_status("Experiment stopped")
        
    def _experiment_loop(self):
        """Main experiment execution loop."""
        try:
            while self.is_running:
                # Check if experiment duration is exceeded
                if time.time() - self.start_time > self.duration:
                    self.logger.info("Experiment duration completed")
                    self.stop()
                    break
                    
                # Check if paused
                if self.is_paused:
                    time.sleep(0.1)
                    continue
                    
                # Execute one iteration
                self._execute_iteration()
                
                # Wait for next interval
                time.sleep(self.interval)
                
        except Exception as e:
            self.logger.error(f"Error in experiment loop: {e}")
            self._handle_error(f"Experiment error: {str(e)}")
            self.stop()
            
    def _execute_iteration(self):
        """Execute one iteration of the experiment."""
        try:
            self.current_iteration += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Visit each point in the path
            for point in self.path_points:
                # Move to position
                if not self.gcode.move_xyz(point['X'], point['Y'], point['Z']):
                    raise RuntimeError(f"Failed to move to position: {point}")
                    
                # Allow for motion completion
                time.sleep(0.5)
                
                # Capture image
                frame = self.camera.capture_frame()
                if frame is None:
                    raise RuntimeError("Failed to capture image")
                    
                # Save image
                filename = f"{self.file_prefix}_well{point['well']}_{timestamp}.jpg"
                filepath = os.path.join(self.save_folder, filename)
                
                if not cv2.imwrite(filepath, frame):
                    raise RuntimeError(f"Failed to save image: {filepath}")
                
            # Update progress
            if self.progress_callback:
                self.progress_callback(self.current_iteration, self.total_iterations)
                
        except Exception as e:
            self.logger.error(f"Error in iteration {self.current_iteration}: {e}")
            self._handle_error(f"Iteration error: {str(e)}")
            raise
            
    def _update_status(self, status: str):
        """Update experiment status."""
        self.logger.info(f"Status: {status}")
        if self.status_callback:
            self.status_callback(status)
            
    def _handle_error(self, error: str):
        """Handle experiment error."""
        self.logger.error(f"Error: {error}")
        if self.error_callback:
            self.error_callback(error)
            
    def set_callbacks(self,
                     status_callback: Optional[Callable[[str], None]] = None,
                     progress_callback: Optional[Callable[[int, int], None]] = None,
                     error_callback: Optional[Callable[[str], None]] = None):
        """
        Set callback functions for experiment events.
        
        Args:
            status_callback: Function to handle status updates
            progress_callback: Function to handle progress updates
            error_callback: Function to handle error notifications
        """
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.error_callback = error_callback

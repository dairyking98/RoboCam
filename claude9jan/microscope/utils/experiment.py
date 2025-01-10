import os
import time
import logging
import threading
from datetime import datetime
from typing import List, Dict, Optional, Callable
from queue import Queue
import json
import cv2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Import the entire module
import microscope.hardware.camera as camera_module
import microscope.hardware.gcode as gcode_module
from microscope.config import FILE_SETTINGS

class Experiment:
    """Class to manage experiment execution and data collection."""

    def __init__(self, camera: camera_module.Camera, gcode: gcode_module.GCode):
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
        self.pause_time = 1.0  # Pause time after each movement in seconds
        self.duration = 0  # Total experiment duration in seconds
        
        # File management
        self.save_folder = ""
        self.file_prefix = ""
        
        # Event handling
        self.status_callback: Optional[Callable[[str], None]] = None
        self.progress_callback: Optional[Callable[[int, int], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None
        
        # Threading
        self.experiment_thread: Optional[threading.Thread] = None
        self.command_queue: Queue = Queue()
        
        # Debug flag
        self.debug = False
        
        if self.debug:
            print("DEBUG: Experiment instance created")

    def set_debug(self, debug: bool):
        self.debug = debug
        if self.debug:
            print("DEBUG: Debug mode enabled for Experiment class")
        else:
            print("DEBUG: Debug mode disabled for Experiment class")
        
    def configure(self, config: Dict):
        """
        Configure the experiment with the provided settings.
        
        Args:
            config: Dictionary containing experiment settings
                Required keys:
                - path_points: List of coordinates to visit
                - pause_time: Pause time after each movement
                - duration: Total experiment duration
                - save_folder: Directory to save images
                - file_prefix: Prefix for saved files
        """
        if self.debug:
            print(f"DEBUG: Configuring experiment with settings: {config}")
        try:
            self.path_points = config['path_points']
            self.pause_time = float(config['pause_time'])
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
        if self.debug:
            print("DEBUG: Validating configuration")
        try:
            # Check path points
            if not self.path_points:
                raise ValueError("No path points defined")
                
            # Check timing
            if self.pause_time <= 0:
                raise ValueError("Pause time must be positive")
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
        if self.debug:
            print("DEBUG: Saving configuration to file")
        try:
            config = {
                'path_points': self.path_points,
                'pause_time': self.pause_time,
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
        if self.debug:
            print("DEBUG: Starting experiment")
        if self.is_running:
            self.logger.warning("Experiment already running")
            return
            
        try:
            # Initialize experiment state
            self.is_running = True
            self.is_paused = False
            self.start_time = time.time()
            self.current_iteration = 0
            self.total_iterations = int(self.duration / self.pause_time)
            
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
        if self.debug:
            print("DEBUG: Pausing experiment")
        self.is_paused = True
        self._update_status("Experiment paused")
        
    def resume(self):
        """Resume the experiment execution."""
        if self.debug:
            print("DEBUG: Resuming experiment")
        self.is_paused = False
        self._update_status("Experiment resumed")
        
    def stop(self):
        """Stop the experiment execution."""
        if self.debug:
            print("DEBUG: Stopping experiment")
        self.is_running = False
        self.is_paused = False
        self._update_status("Experiment stopped")
        
    def _experiment_loop(self):
        """Main experiment execution loop."""
        if self.debug:
            print("DEBUG: Entering experiment loop")
        try:
            while self.is_running:
                # Check if experiment duration is exceeded
                if time.time() - self.start_time > self.duration:
                    if self.debug:
                        print("DEBUG: Experiment duration completed")
                    self.logger.info("Experiment duration completed")
                    self.stop()
                    break
                    
                # Check if paused
                if self.is_paused:
                    if self.debug:
                        print("DEBUG: Experiment paused, waiting...")
                    time.sleep(0.1)
                    continue
                    
                # Execute one iteration
                self._execute_iteration()
                
        except Exception as e:
            self.logger.error(f"Error in experiment loop: {e}")
            self._handle_error(f"Experiment error: {str(e)}")
            self.stop()
            
    def _execute_iteration(self):
        """Execute one iteration of the experiment."""
        if self.debug:
            print(f"DEBUG: Starting iteration {self.current_iteration}")
        
        try:
            start_time = time.time()
            iteration = self.current_iteration

            for point in self.path_points:
                if not self.is_running or self.is_paused:
                    if self.debug:
                        print("DEBUG: Experiment stopped or paused, exiting iteration")
                    return

                well = point['well']
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                if self.debug:
                    print(f"DEBUG: Moving to position: {point}")

                # Move to position
                if not self.gcode.move_xyz(point['X'], point['Y'], point['Z']):
                    raise RuntimeError(f"Failed to move to position: {point}")

                # Wait for movement to complete
                if self.debug:
                    print("DEBUG: Waiting for movement to complete")
                self.gcode.wait_for_movement_completion()

                # Pause for specified time
                if self.debug:
                    print(f"DEBUG: Pausing for {self.pause_time} seconds")
                time.sleep(self.pause_time)

                # Capture image
                if self.debug:
                    print("DEBUG: Capturing frame")
                frame = self.camera.capture_frame()
                if frame is None:
                    raise RuntimeError("Failed to capture image")

                # Save image
                filename = f"{well}_{iteration:04d}_{timestamp}.jpg"
                filepath = os.path.join(self.save_folder, filename)
                if self.debug:
                    print(f"DEBUG: Saving image to {filepath}")

                if not cv2.imwrite(filepath, frame):
                    raise RuntimeError(f"Failed to save image: {filepath}")

                if self.debug:
                    print(f"DEBUG: Image saved successfully: {filepath}")

            # Update progress
            self.current_iteration += 1
            if self.progress_callback:
                self.progress_callback(self.current_iteration, self.total_iterations)

            if self.debug:
                print(f"DEBUG: Iteration {iteration} completed")

        except Exception as e:
            self.logger.error(f"Error in iteration {iteration}: {e}")
            self._handle_error(f"Iteration error: {str(e)}")
            raise

        if self.debug:
            print(f"DEBUG: Iteration {iteration} duration: {time.time() - start_time:.2f} seconds")

    def _wait_for_movement(self, x: float, y: float, z: float) -> bool:
        """Wait for the G-code printer to complete movement."""
        if self.debug:
            print(f"DEBUG: Waiting for movement to ({x}, {y}, {z})")
        try:
            # Send movement command
            if not self.gcode.move_xyz(x, y, z):
                raise RuntimeError(f"Failed to move to position: ({x}, {y}, {z})")

            # Wait for movement to complete
            while self.gcode.is_moving():
                if self.debug:
                    print("DEBUG: Printer is still moving...")
                time.sleep(0.1)

            if self.debug:
                print("DEBUG: Movement completed")
            return True

        except Exception as e:
            self.logger.error(f"Error during movement: {e}")
            return False

    def _update_status(self, status: str):
        """Update experiment status."""
        if self.debug:
            print(f"DEBUG: Status update - {status}")
        self.logger.info(f"Status: {status}")
        if self.status_callback:
            self.status_callback(status)
            
    def _handle_error(self, error: str):
        """Handle experiment error."""
        if self.debug:
            print(f"DEBUG: Error occurred - {error}")
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
        if self.debug:
            print("DEBUG: Setting callbacks")
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.error_callback = error_callback

    def get_elapsed_time(self) -> Optional[float]:
        """Get the elapsed time since the experiment started."""
        if self.start_time is None:
            return None
        elapsed_time = time.time() - self.start_time
        if self.debug:
            print(f"DEBUG: Elapsed time: {elapsed_time} seconds")
        return elapsed_time

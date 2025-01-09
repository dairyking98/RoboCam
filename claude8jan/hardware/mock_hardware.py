"""
Simplified mock hardware implementations for testing without external dependencies
"""
import time
import threading

class MockSerial:
    """Mock serial connection that prints GCode commands to console"""
    def __init__(self, port=None, baudrate=None, timeout=None):
        self.is_open = True
        self.in_waiting = 0
        self._response_queue = []
        print(f"Mock Serial initialized (port={port}, baudrate={baudrate})")
        
    def write(self, data):
        """Print the GCode command to console"""
        command = data.decode('utf-8').strip()
        print(f"Mock Serial received: {command}")
        # Simulate printer response
        if command.startswith('G28'):
            # Homing takes longer
            time.sleep(0.5)
        else:
            time.sleep(0.1)
        self._response_queue.append("ok")
        self.in_waiting = 1
        return len(data)
        
    def readline(self):
        """Return simulated response"""
        if self._response_queue:
            response = self._response_queue.pop(0)
            self.in_waiting = len(self._response_queue)
            return response.encode('utf-8') + b'\n'
        return b''
        
    def reset_input_buffer(self):
        """Clear input buffer"""
        self._response_queue = []
        self.in_waiting = 0
        
    def close(self):
        """Close the mock connection"""
        self.is_open = False
        print("Mock Serial connection closed")

class MockPrinter:
    """Simulated 3D printer for testing"""
    def __init__(self):
        self.position = {'X': 0, 'Y': 0, 'Z': 0}
        self.is_homed = False
        self.steppers_enabled = True
        
    def process_command(self, command):
        """Process a GCode command and return appropriate response"""
        if command.startswith('G28'):
            self.position = {'X': 0, 'Y': 0, 'Z': 0}
            self.is_homed = True
            return "ok"
        elif command.startswith('G1'):
            # Parse movement command
            parts = command.split()
            for part in parts[1:]:  # Skip G1
                if part[0] in ['X', 'Y', 'Z']:
                    self.position[part[0]] = float(part[1:])
            return "ok"
        elif command.startswith('M84'):  # Disable steppers
            self.steppers_enabled = False
            return "ok"
        elif command.startswith('M17'):  # Enable steppers
            self.steppers_enabled = True
            return "ok"
        return "ok"

class MockCamera:
    """Simple mock camera that just logs operations"""
    def __init__(self):
        self.running = False
        self.frame_count = 0
        print("Mock camera initialized")
        
    def get_frame(self):
        """Return None - no actual frame data needed for testing"""
        if self.running:
            self.frame_count += 1
            print(f"Mock camera frame captured ({self.frame_count})")
        return None
        
    def start(self):
        """Start the mock camera"""
        self.running = True
        print("Mock camera started")
        
    def stop(self):
        """Stop the mock camera"""
        self.running = False
        print("Mock camera stopped")

    def release(self):
        """Release the mock camera"""
        self.stop()
        print("Mock camera released")
import cv2
from picamera2 import Picamera2

class Camera:
    def __init__(self):
        self.capture = cv2.VideoCapture(0)
        if not self.capture.isOpened():
            raise Exception("Could not open video device")

    def get_frame(self):
        ret, frame = self.capture.read()
        if not ret:
            raise Exception("Failed to grab frame")
        return frame

    def release(self):
        self.capture.release()

class PiCamera:
    def __init__(self):
        self.picam2 = None
        self.running = False

    def initialize(self):
        try:
            self.picam2 = Picamera2()
            picam2_config = self.picam2.create_preview_configuration(main={"size": (640, 480)})
            self.picam2.configure(picam2_config)
            self.picam2.start()
            self.running = True
            return True
        except Exception as e:
            print(f"Error initializing camera: {e}")
            if self.picam2:
                self.picam2.close()
                self.picam2 = None
            self.running = False
            return False

    def get_frame(self):
        if self.running and self.picam2:
            return self.picam2.capture_array("main")
        return None

    def stop(self):
        self.running = False
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
                self.picam2 = None
            except Exception as e:
                print(f"Error stopping camera: {e}")
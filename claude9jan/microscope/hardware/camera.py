from picamera2 import Picamera2

class Camera:
    def __init__(self):
        self.picam2 = Picamera2()
        self.picam2_config = self.picam2.create_preview_configuration(main={"size": (640, 480)})
        self.picam2.configure(self.picam2_config)
        self.picam2.start()

    def capture_frame(self):
        frame = self.picam2.capture_array("main")
        return frame

    def stop(self):
        self.picam2.stop()

    def is_open(self):
        return self.picam2.camera is not None

    def start(self):
        if not self.is_open():
            self.picam2.start()

import tkinter as tk
import cv2
from hardware.camera import PiCamera

class CameraGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Camera Preview")
        self.root.geometry("1000x600")
        
        self.setup_gui()
        self.initialize_camera()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_gui(self):
        # Create main frames
        self.preview_frame = tk.Frame(self.root)
        self.preview_frame.pack(side=tk.LEFT, padx=10, pady=10, expand=True)
        
        self.controls_frame = tk.Frame(self.root)
        self.controls_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.Y)

        # Initialize settings variables
        self.rotation = tk.IntVar(value=0)
        self.zoom = tk.DoubleVar(value=1.0)
        self.crosshair_enabled = tk.BooleanVar(value=False)
        self.circle_enabled = tk.BooleanVar(value=False)
        self.overlay_color = tk.StringVar(value="red")
        self.overlay_size = tk.IntVar(value=100)
        self.overlay_thickness = tk.IntVar(value=2)
        
        # Create preview label
        self.image_label = tk.Label(self.preview_frame, width=640, height=480)
        self.image_label.pack(expand=True)
        
        # Create control panels
        self.create_camera_controls()
        self.create_overlay_controls()

    def create_camera_controls(self):
        camera_frame = tk.LabelFrame(self.controls_frame, text="Camera Settings")
        camera_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Rotation control
        tk.Label(camera_frame, text="Rotation:").pack(anchor=tk.W)
        for r in [0, 90, 180, 270]:
            tk.Radiobutton(camera_frame, text=f"{r}°", 
                          variable=self.rotation, value=r).pack(anchor=tk.W)
        
        # Zoom control
        tk.Label(camera_frame, text="Zoom:").pack(anchor=tk.W)
        tk.Scale(camera_frame, from_=1.0, to=4.0, resolution=0.1,
                orient=tk.HORIZONTAL, variable=self.zoom).pack(fill=tk.X)

    def create_overlay_controls(self):
        overlay_frame = tk.LabelFrame(self.controls_frame, text="Overlay Settings")
        overlay_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Overlay type selection
        tk.Label(overlay_frame, text="Overlays:").pack(anchor=tk.W)
        tk.Checkbutton(overlay_frame, text="Crosshair", 
                       variable=self.crosshair_enabled).pack(anchor=tk.W)
        tk.Checkbutton(overlay_frame, text="Circle", 
                       variable=self.circle_enabled).pack(anchor=tk.W)
        
        # Color selection
        tk.Label(overlay_frame, text="Color:").pack(anchor=tk.W)
        colors = ["red", "green", "blue", "yellow", "white"]
        tk.OptionMenu(overlay_frame, self.overlay_color, *colors).pack(fill=tk.X)
        
        # Size control
        tk.Label(overlay_frame, text="Circle Size:").pack(anchor=tk.W)
        tk.Scale(overlay_frame, from_=100, to=500, orient=tk.HORIZONTAL,
                variable=self.overlay_size).pack(fill=tk.X)
        
        # Thickness control
        tk.Label(overlay_frame, text="Thickness:").pack(anchor=tk.W)
        tk.Scale(overlay_frame, from_=1, to=5, orient=tk.HORIZONTAL,
                variable=self.overlay_thickness).pack(fill=tk.X)

    def initialize_camera(self):
        self.camera = PiCamera()
        if self.camera.initialize():
            self.running = True
            self.update_frame()
        else:
            self.running = False
            tk.messagebox.showerror("Error", "Failed to initialize camera")

    def draw_overlay(self, frame):
        height, width = frame.shape[:2]
        center_x = width // 2
        center_y = height // 2
        
        color_map = {
            "red": (0, 0, 255),
            "green": (0, 255, 0),
            "blue": (255, 0, 0),
            "yellow": (0, 255, 255),
            "white": (255, 255, 255)
        }
        color = color_map[self.overlay_color.get()]
        thickness = self.overlay_thickness.get()
        
        if self.crosshair_enabled.get():
            cv2.line(frame, (0, center_y), (width, center_y), color, thickness)
            cv2.line(frame, (center_x, 0), (center_x, height), color, thickness)
        
        if self.circle_enabled.get():
            radius = self.overlay_size.get() // 2
            cv2.circle(frame, (center_x, center_y), radius, color, thickness)
        
        return frame

    def apply_transformations(self, frame):
        if self.rotation.get() != 0:
            rows, cols = frame.shape[:2]
            matrix = cv2.getRotationMatrix2D((cols/2, rows/2), self.rotation.get(), 1)
            frame = cv2.warpAffine(frame, matrix, (cols, rows))
        
        if self.zoom.get() != 1.0:
            rows, cols = frame.shape[:2]
            zoom = self.zoom.get()
            crop_size = (int(cols/zoom), int(rows/zoom))
            x = (cols - crop_size[0]) // 2
            y = (rows - crop_size[1]) // 2
            frame = frame[y:y+crop_size[1], x:x+crop_size[0]]
            frame = cv2.resize(frame, (cols, rows))
        
        return frame

    def update_frame(self):
        if self.running:
            frame = self.camera.get_frame()
            if frame is not None:
                frame = self.apply_transformations(frame)
                frame = self.draw_overlay(frame)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                photo = tk.PhotoImage(data=cv2.imencode('.ppm', frame)[1].tobytes())
                self.image_label.configure(image=photo)
                self.image_label.image = photo
            self.root.after(10, self.update_frame)

    def stop(self):
        self.running = False
        self.camera.stop()

    def on_closing(self):
        self.stop()
        self.root.destroy()
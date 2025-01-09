import tkinter as tk
from tkinter import messagebox
from utils.path_generator import generate_well_plate_path

class PathfinderGUI:
    def __init__(self, root, gcode):
        self.root = root
        self.gcode = gcode
        self.root.title("Pathfinder")
        self.root.geometry("400x300")
        
        # Initialize well coordinates and path
        self.well_positions = {
            'A1': None, 'A8': None,
            'F8': None, 'F1': None
        }
        self.generated_path = None  # Store the generated path
        
        self.setup_gui()
        
    def setup_gui(self):
        # ... existing GUI setup code ...
        
        # Add Export Path button
        self.export_button = tk.Button(
            self.main_frame,
            text="Export Path",
            command=self.export_path,
            state=tk.DISABLED
        )
        self.export_button.pack(pady=5)
        
    def create_well_buttons(self):
        for well in self.well_positions.keys():
            frame = tk.Frame(self.main_frame)
            frame.pack(anchor=tk.W, padx=5, pady=5)
            
            button = tk.Button(
                frame,
                text=f"Capture {well} Well",
                command=lambda w=well: self.capture_well_position(w)
            )
            button.pack(side=tk.LEFT)
            
            label = tk.Label(frame, text="Not captured")
            label.pack(side=tk.LEFT, padx=5)
            
            setattr(self, f"{well}_label", label)
            
    def capture_well_position(self, well):
        """Capture the current position for the specified well"""
        position = {
            'X': self.gcode.current_position['X'],
            'Y': self.gcode.current_position['Y'],
            'Z': self.gcode.current_position['Z']
        }
        self.well_positions[well] = position
        
        # Update label
        label = getattr(self, f"{well}_label")
        label.config(text=f"X: {position['X']:.2f}, Y: {position['Y']:.2f}, Z: {position['Z']:.2f}")
        
        # Check if all wells are captured
        self.check_capture_status()
        
    def check_capture_status(self):
        """Check if all well positions have been captured"""
        if all(pos is not None for pos in self.well_positions.values()):
            self.generate_button.config(state=tk.NORMAL)
            self.status_var.set("Ready to generate path")
        
    def generate_path(self):
        try:
            self.generated_path = generate_well_plate_path(
                self.well_positions['A1'],
                self.well_positions['A8'],
                self.well_positions['F8'],
                self.well_positions['F1']
            )
            
            self.status_var.set(f"Path generated successfully: {len(self.generated_path)} points")
            self.save_button.config(state=tk.NORMAL)
            self.export_button.config(state=tk.NORMAL)  # Enable export button
            
            # Display preview of the path
            self.display_path_preview()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate path: {str(e)}")

    def export_path(self):
        """Export the generated path to a file"""
        if not self.generated_path:
            messagebox.showerror("Error", "No path generated to export")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save Path As"
        )
        
        if filename:
            try:
                path_data = {
                    'well_positions': self.well_positions,
                    'path': self.generated_path,
                    'metadata': {
                        'timestamp': time.strftime("%Y%m%d-%H%M%S"),
                        'num_points': len(self.generated_path)
                    }
                }
                
                with open(filename, 'w') as f:
                    json.dump(path_data, f, indent=2)
                    
                self.status_var.set(f"Path exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export path: {str(e)}")
            
    def display_path_preview(self):
        """Display a preview of the generated path"""
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Path Preview")
        
        # Create text widget for path display
        text_widget = tk.Text(preview_window, height=20, width=50)
        text_widget.pack(padx=10, pady=10)
        
        # Insert path information
        text_widget.insert(tk.END, "Generated Path:\n\n")
        for i, point in enumerate(self.path):
            well_name = self.get_well_name(i)
            text_widget.insert(tk.END, 
                f"{well_name}: X={point['X']:.2f}, Y={point['Y']:.2f}, Z={point['Z']:.2f}\n")
        
        text_widget.config(state=tk.DISABLED)
        
    def get_well_name(self, index):
        """Convert numerical index to well name (A1, A2, etc.)"""
        row = chr(65 + (index // 8))  # A, B, C, ...
        col = (index % 8) + 1         # 1, 2, 3, ...
        return f"{row}{col}"
        
    def save_path(self):
        """Save the generated path"""
        # Implementation for saving the path
        # This could save to a file or pass to another component
        pass
        
    def on_closing(self):
        """Handle window closing"""
        self.root.destroy()
"""
Utility functions for generating well plate scanning paths
"""

def interpolate_position(pos1, pos2, fraction):
    """
    Interpolate between two positions.
    
    Args:
        pos1 (dict): Starting position with X, Y, Z coordinates
        pos2 (dict): Ending position with X, Y, Z coordinates
        fraction (float): Fraction of distance (0.0 to 1.0)
        
    Returns:
        dict: Interpolated position with X, Y, Z coordinates
    """
    return {
        'X': pos1['X'] + (pos2['X'] - pos1['X']) * fraction,
        'Y': pos1['Y'] + (pos2['Y'] - pos1['Y']) * fraction,
        'Z': pos1['Z'] + (pos2['Z'] - pos1['Z']) * fraction
    }

def generate_well_plate_path(A1, A8, F8, F1):
    """
    Generate a path for scanning a 6x8 well plate given the corner positions.
    
    Args:
        A1 (dict): Position of well A1 (top-left)
        A8 (dict): Position of well A8 (top-right)
        F8 (dict): Position of well F8 (bottom-right)
        F1 (dict): Position of well F1 (bottom-left)
        
    Returns:
        list: List of positions for each well in sequence
    """
    path = []
    num_rows = 6  # A to F
    num_cols = 8  # 1 to 8
    
    for row in range(num_rows):
        # Calculate the start and end points for this row
        row_fraction = row / (num_rows - 1)
        row_start = interpolate_position(A1, F1, row_fraction)
        row_end = interpolate_position(A8, F8, row_fraction)
        
        # Generate positions for each well in the row
        for col in range(num_cols):
            col_fraction = col / (num_cols - 1)
            position = interpolate_position(row_start, row_end, col_fraction)
            path.append(position)
    
    return path

def calculate_travel_time(path, feedrate):
    """
    Calculate the total travel time for a given path.
    
    Args:
        path (list): List of positions
        feedrate (float): Movement speed in mm/min
        
    Returns:
        float: Estimated travel time in minutes
    """
    total_distance = 0
    for i in range(1, len(path)):
        prev_pos = path[i-1]
        curr_pos = path[i]
        
        # Calculate Euclidean distance
        distance = (
            (curr_pos['X'] - prev_pos['X'])**2 +
            (curr_pos['Y'] - prev_pos['Y'])**2 +
            (curr_pos['Z'] - prev_pos['Z'])**2
        )**0.5
        
        total_distance += distance
    
    return total_distance / feedrate

def validate_corner_positions(A1, A8, F8, F1):
    """
    Validate that the corner positions form a reasonable rectangle.
    
    Args:
        A1 (dict): Position of well A1
        A8 (dict): Position of well A8
        F8 (dict): Position of well F8
        F1 (dict): Position of well F1
        
    Returns:
        bool: True if positions are valid, False otherwise
    """
    # Check that all positions are provided and have X, Y, Z coordinates
    corners = [A1, A8, F8, F1]
    if not all(isinstance(pos, dict) and all(k in pos for k in ['X', 'Y', 'Z']) 
              for pos in corners):
        return False
    
    # Check that the rectangle is not too skewed
    # This could be expanded with more sophisticated validation
    return True

def generate_preview(path, width=600, height=400):
    """
    Generate a text-based preview of the path.
    
    Args:
        path (list): List of positions
        width (int): Width of preview in characters
        height (int): Height of preview in characters
        
    Returns:
        str: ASCII art preview of the path
    """
    # Find the bounds of the path
    min_x = min(p['X'] for p in path)
    max_x = max(p['X'] for p in path)
    min_y = min(p['Y'] for p in path)
    max_y = max(p['Y'] for p in path)
    
    # Create a blank canvas
    canvas = [[' ' for _ in range(width)] for _ in range(height)]
    
    # Plot each point
    for i, pos in enumerate(path):
        # Scale coordinates to canvas size
        x = int((pos['X'] - min_x) / (max_x - min_x) * (width - 1))
        y = int((pos['Y'] - min_y) / (max_y - min_y) * (height - 1))
        
        # Mark the point
        canvas[y][x] = 'O'
        
        # Add well label
        row = chr(65 + (i // 8))
        col = (i % 8) + 1
        label = f"{row}{col}"
        
        # Try to place label next to point
        if x + len(label) < width:
            for j, char in enumerate(label):
                canvas[y][x+1+j] = char
    
    # Convert canvas to string
    return '\n'.join(''.join(row) for row in canvas)
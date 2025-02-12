import ezdxf
import math
import logging
from scipy.spatial import KDTree
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

def line_length(start, end):
    return math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2 + (end.z - start.z) ** 2)

def extract_lines(dxf_file):
    """Extracts all lines from a DXF file and returns them as a list of tuples (start, end, length)."""
    logging.info(f"Reading DXF file: {dxf_file}")
    
    try:
        doc = ezdxf.readfile(dxf_file)
        msp = doc.modelspace()
    except Exception as e:
        logging.error(f"Error reading DXF file: {e}")
        return [], []

    lines = []
    points = []  # Collect start and end points for KDTree

    for entity in msp.query("LINE"):
        start = entity.dxf.start
        end = entity.dxf.end
        length = line_length(start, end)
        
        logging.debug(f"Line: Start ({start.x}, {start.y}, {start.z}) -> End ({end.x}, {end.y}, {end.z}), Length: {length}")
        
        lines.append((start, end, length))
        points.append((start.x, start.y, start.z))
        points.append((end.x, end.y, end.z))

    logging.info(f"Extracted {len(lines)} lines from DXF file.")
    return lines, points

def order_lines(lines, points):
    """Orders lines based on proximity using a KDTree."""
    if not lines:
        logging.warning("No lines found to order.")
        return []

    logging.info("Building KDTree for line points...")
    tree = KDTree(points)
    ordered_lines = []
    visited = set()

    # Start with the first line
    current_line = lines[0]
    ordered_lines.append(current_line)
    visited.add(current_line)

    logging.debug(f"Starting ordering with line: {current_line}")

    while len(ordered_lines) < len(lines):
        current_end = current_line[1]  # End of the current line
        nearest_dist, nearest_indices = tree.query([(current_end.x, current_end.y, current_end.z)], k=min(10, len(points)))

        found_next = False
        for idx in nearest_indices[0]:
            candidate_idx = idx // 2
            if candidate_idx < len(lines):
                candidate = lines[candidate_idx]
                if candidate not in visited:
                    ordered_lines.append(candidate)
                    visited.add(candidate)
                    current_line = candidate
                    found_next = True
                    break

        if not found_next:
            logging.warning("No connected unvisited lines. Jumping to the next closest unvisited line.")

            # Find the next closest unvisited line by direct distance computation
            remaining_lines = [line for line in lines if line not in visited]
            if not remaining_lines:
                break

            current_line = min(remaining_lines, key=lambda line: min(
                line_length(current_line[1], line[0]), 
                line_length(current_line[1], line[1])
            ))
            ordered_lines.append(current_line)
            visited.add(current_line)

    logging.info(f"Ordered {len(ordered_lines)} lines out of {len(lines)} total.")
    return ordered_lines


def write_ordered_lines(ordered_lines, output_file):
    """Writes the ordered line lengths to a text file."""
    logging.info(f"Writing ordered line lengths to {output_file}")
    with open(output_file, "w") as f:
        for start, end, length in ordered_lines:
            f.write(f"{length}\n")
    logging.info("File write complete.")

def create_horizontal_lines_with_dividers(input_txt):
    """Creates a horizontal line of connected segments with vertical dividers and a top horizontal line in a DXF file."""
    with open(input_txt, "r") as f:
        lengths = [float(line.strip()) for line in f if line.strip()]

    doc = ezdxf.new()
    msp = doc.modelspace()

    x = 0  # Start position
    y = 0  # Base horizontal line position
    vertical_height = float(input("Enter wall height: "))  # Height of vertical lines
    top_y = y + vertical_height  # Y-coordinate for the top horizontal line

    horizontal_color = 7  # Black
    vertical_color = 1  # Red

    for length in lengths:
        end_x = x + length
        # Draw the main bottom horizontal segment
        msp.add_line((x, y), (end_x, y)).dxf.color = horizontal_color
        # Draw a vertical line at the joint (different color)
        msp.add_line((x, y), (x, top_y)).dxf.color = vertical_color
        x = end_x  # Move to the next starting point

    # Add a final vertical line at the last joint (different color)
    msp.add_line((x, y), (x, top_y)).dxf.color = vertical_color

    # Draw the top horizontal line across the vertical dividers
    msp.add_line((0, top_y), (x, top_y)).dxf.color = horizontal_color

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dxf = f"horizontal_lines_{timestamp}.dxf"

    doc.saveas(output_dxf)
    logging.info(f"DXF file saved as {output_dxf}")

if __name__ == "__main__":
    dxf_input = "input.dxf"  # Change this to your DXF file
    output_txt = "ordered_line_lengths.txt"

    # Extract lines and order them
    lines, points = extract_lines(dxf_input)
    
    if lines:
        ordered_lines = order_lines(lines, points)
        write_ordered_lines(ordered_lines, output_txt)
        create_horizontal_lines_with_dividers(output_txt)
    else:
        logging.error("No lines extracted, skipping processing.")

    logging.info(f"Processing complete. Output saved to {output_txt}")

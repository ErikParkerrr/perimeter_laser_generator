import ezdxf
import math
import logging
from scipy.spatial import KDTree
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

def transform_point(point, insert):
    """Applies translation, scaling, and rotation to a point based on an INSERT entity."""
    import cmath

    x, y, z = point.x, point.y, point.z

    # Apply translation
    x += insert.dxf.insert.x
    y += insert.dxf.insert.y
    z += insert.dxf.insert.z

    # Apply scaling
    x *= insert.dxf.xscale
    y *= insert.dxf.yscale
    z *= insert.dxf.zscale

    # Apply rotation (2D rotation)
    angle_rad = math.radians(insert.dxf.rotation)
    rotated = cmath.rect(math.hypot(x, y), math.atan2(y, x) + angle_rad)

    return ezdxf.math.Vec3(rotated.real, rotated.imag, z)


def line_length(start, end):
    return math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2 + (end.z - start.z) ** 2)

def extract_lines(dxf_file):
    """Extracts all lines from a DXF file, including lines inside block references."""
    logging.info(f"Reading DXF file: {dxf_file}")
    
    try:
        doc = ezdxf.readfile(dxf_file)
        msp = doc.modelspace()
    except Exception as e:
        logging.error(f"Error reading DXF file: {e}")
        return [], []

    lines = []
    points = []  # Collect start and end points for KDTree

    # Extract standalone LINE entities
    for entity in msp.query("LINE"):
        start = entity.dxf.start
        end = entity.dxf.end
        length = line_length(start, end)

        logging.debug(f"Line: Start ({start.x}, {start.y}, {start.z}) -> End ({end.x}, {end.y}, {end.z}), Length: {length}")

        lines.append((start, end, length))
        points.append((start.x, start.y, start.z))
        points.append((end.x, end.y, end.z))

    # Process block references (INSERT entities)
    for insert in msp.query("INSERT"):
        block_name = insert.dxf.name
        logging.info(f"Processing block reference: {block_name}")

        try:
            block = doc.blocks.get(block_name)
        except KeyError:
            logging.warning(f"Block '{block_name}' not found in the DXF file.")
            continue

        for entity in block.query("LINE"):
            start = entity.dxf.start
            end = entity.dxf.end

            # Apply block transformation (position, rotation, scale)
            transformed_start = transform_point(start, insert)
            transformed_end = transform_point(end, insert)
            length = line_length(transformed_start, transformed_end)

            logging.debug(f"Block Line: Start ({transformed_start.x}, {transformed_start.y}, {transformed_start.z}) -> "
                          f"End ({transformed_end.x}, {transformed_end.y}, {transformed_end.z}), Length: {length}")

            lines.append((transformed_start, transformed_end, length))
            points.append((transformed_start.x, transformed_start.y, transformed_start.z))
            points.append((transformed_end.x, transformed_end.y, transformed_end.z))

    logging.info(f"Extracted {len(lines)} lines including blocks from DXF file.")
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

    current_line = lines[0]
    ordered_lines.append(current_line)
    visited.add(current_line)

    logging.debug(f"Starting ordering with line: {current_line}")

    while len(ordered_lines) < len(lines):
        current_end = current_line[1]
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

    x = 0
    y = 0
    vertical_height = float(input("Enter wall height: "))
    top_y = y + vertical_height

    horizontal_color = 7
    vertical_color = 1

    for length in lengths:
        end_x = x + length
        msp.add_line((x, y), (end_x, y)).dxf.color = horizontal_color
        msp.add_line((x, y), (x, top_y)).dxf.color = vertical_color
        x = end_x

    msp.add_line((x, y), (x, top_y)).dxf.color = vertical_color
    msp.add_line((0, top_y), (x, top_y)).dxf.color = horizontal_color

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dxf = f"horizontal_lines_{timestamp}.dxf"
    doc.saveas(output_dxf)
    logging.info(f"DXF file saved as {output_dxf}")

if __name__ == "__main__":
    dxf_input = "input.dxf"
    output_txt = "ordered_line_lengths.txt"

    lines, points = extract_lines(dxf_input)
    
    if lines:
        ordered_lines = order_lines(lines, points)
        write_ordered_lines(ordered_lines, output_txt)
        create_horizontal_lines_with_dividers(output_txt)
    else:
        logging.error("No lines extracted, skipping processing.")

    logging.info(f"Processing complete. Output saved to {output_txt}")

import ezdxf

dxf_file_path = "input.dxf"  # Update with the correct path

try:
    doc = ezdxf.readfile(dxf_file_path)
    msp = doc.modelspace()

    line_count = len(list(msp.query("LINE")))
    lwpolyline_count = len(list(msp.query("LWPOLYLINE")))
    polyline_count = len(list(msp.query("POLYLINE")))
    all_entity_types = {entity.dxftype() for entity in msp}

    print(f"Total LINE entities: {line_count}")
    print(f"Total LWPOLYLINE entities: {lwpolyline_count}")
    print(f"Total POLYLINE entities: {polyline_count}")
    print(f"Other entity types present: {all_entity_types}")

except Exception as e:
    print(f"Error reading DXF file: {e}")

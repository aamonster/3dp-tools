#!/usr/bin/env python3
"""
Simple backlash compensation for Orca Slicer
Applies offset to endpoint only for positive movements
Adds take-up moves on direction changes
"""

import math
import re
import sys

# Backlash compensation values (positive values)
DX = 0.35  # X-axis backlash in mm
DY = 0.35  # Y-axis backlash in mm

def process_gcode(lines):
    output_lines = []
    
    # State tracking - храним скомпенсированные значения
    last_comp_x = 0  # последняя скомпенсированная X координата
    last_comp_y = 0  # последняя скомпенсированная Y координата
    last_target_x = 0  # оригинальная целевая X
    last_target_y = 0  # оригинальная целевая Y

    dir_x = 0  # направление последнего движения по X: -1, 0, 1
    dir_y = 0  # направление последнего движения по Y: -1, 0, 1
    
    # Regex patterns
    x_pattern = re.compile(r'X([-\d.]+)')
    y_pattern = re.compile(r'Y([-\d.]+)')
    
    for line_num, line in enumerate(lines):
        original_line = line.rstrip('\n')
        processed_line = original_line
        
        # Skip comments and empty lines for processing
        if (original_line.startswith(';') or 
            original_line.startswith('(') or
            not original_line.strip()):
            output_lines.append(original_line)
            continue
        
        # Only process G0/G1/G2/G3/G5 moves with coordinates
        if (original_line.startswith('G0') or 
            original_line.startswith('G1') or
            original_line.startswith('G2') or
            original_line.startswith('G3') or
            original_line.startswith('G5')):
            
            # Parse current line
            x_match = x_pattern.search(original_line)
            y_match = y_pattern.search(original_line)
            
            # Get target coordinates from input
            target_x = float(x_match.group(1)) if x_match else last_target_x
            target_y = float(y_match.group(1)) if y_match else last_target_y
                        
            # Calculate deltas from original targets

            delta_x = target_x - last_target_x if x_match else 0
            delta_y = target_y - last_target_y if y_match else 0

            dir_x = math.copysign(1, delta_x) if abs(delta_x) > 0.0001 else dir_x # сохраняем направление, если движение есть, иначе не меняем
            dir_y = math.copysign(1, delta_y) if abs(delta_y) > 0.0001 else dir_y # сохраняем направление, если движение есть, иначе не меняем
            
            # Calculate compensated coordinates
            comp_x = target_x
            comp_y = target_y
            comp_start_x = last_target_x
            comp_start_y = last_target_y
            
            if dir_x > 0:
                # Positive movement: add DX
                comp_x += DX
                comp_start_x += DX
            
            if dir_y > 0:
                comp_y += DY
                comp_start_y += DY
            
            # Debug output
            # output_lines.append(f"; from: ({last_target_x:.3f}, {last_target_y:.3f}) to ({target_x:.3f}, {target_y:.3f}) delta: ({delta_x:.3f}, {delta_y:.3f})")
            # output_lines.append(f"; comp: ({comp_start_x:.3f}, {comp_start_y:.3f}) to ({comp_x:.3f}, {comp_y:.3f})")
            # output_lines.append(f"; last_comp: ({last_comp_x:.3f}, {last_comp_y:.3f}) comp_start: ({comp_start_x:.3f}, {comp_start_y:.3f})")


            # Add backlash take-up moves if we have skip from last_comp to comp_start (direction changed)
            if abs(comp_start_x - last_comp_x) > 0.0001 or abs(comp_start_y - last_comp_y) > 0.0001:
                # Create take-up move without extrusion
                take_up_cmd = f"G1 X{comp_start_x:.3f} Y{comp_start_y:.3f} ; Backlash take-up"
                # Add take-up lines before the compensated move
                # !!! output_lines.append(take_up_cmd)
            
            # Apply compensation to the line
            if x_match and abs(comp_x - target_x) > 0.0001:
                # Positive movement: replace X coordinate
                processed_line = re.sub(
                    r'X[-\d.]+', 
                    f"X{comp_x:.3f}", 
                    processed_line, 
                    count=1
                )
            
            if y_match and abs(comp_y - target_y) > 0.0001:
                # Positive movement: replace Y coordinate
                processed_line = re.sub(
                    r'Y[-\d.]+', 
                    f"Y{comp_y:.3f}", 
                    processed_line, 
                    count=1
                )
            
            output_lines.append(processed_line)
            
            # Update state with COMPENSATED values
            if x_match:
                last_comp_x = comp_x
                last_target_x = target_x
            if y_match:
                last_comp_y = comp_y
                last_target_y = target_y
                        
        else:
            # Non-move commands pass through unchanged
            output_lines.append(original_line)
    
    print(f"Processed: {len(lines)} lines -> {len(output_lines)} lines")
    print(f"Backlash compensation applied: X={DX}mm, Y={DY}mm")
    print(f"Compensation only for positive movements")
    return output_lines

def main():
    if len(sys.argv) < 2:
        print("Usage: script.py file.gcode [output.gcode]", file=sys.stderr)
        print("If output file not specified, input file will be overwritten", file=sys.stderr)
        sys.exit(1)

    infile = sys.argv[1]
    
    if len(sys.argv) > 2:
        outfile = sys.argv[2]
    else:
        outfile = infile
        print(f"Warning: Overwriting input file {infile}", file=sys.stderr)

    with open(infile, "r") as f:
        gcode_lines = f.read().splitlines()

    new_lines = process_gcode(gcode_lines)

    with open(outfile, "w") as f:
        f.write("\n".join(new_lines))
    
    print(f"Output saved to: {outfile}")

if __name__ == "__main__":
    main()
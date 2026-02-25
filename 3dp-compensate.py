#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK - magic string for argcomplete

"""
Simple backlash compensation for Orca Slicer
Applies offset to endpoint only for positive movements
Adds take-up moves on direction changes

Usage:
    backlash_comp.py input.gcode [output.gcode] [--dx VALUE] [--dy VALUE]
    
Options:
    --dx VALUE      X-axis backlash compensation in mm (default: 0.35)
    --dy VALUE      Y-axis backlash compensation in mm (default: 0.35)
    
If output file not specified, input file will be overwritten
"""

import argparse
import math
import re
import sys

try:
    import argcomplete
except ImportError:
    # Fallback if argcomplete not installed
    argcomplete = None

def parse_arguments():
    """Parse command line arguments with argcomplete support"""
    parser = argparse.ArgumentParser(
        description="Apply backlash compensation to G-code files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        'input',
        help='Input G-code file to process'
    )
    
    parser.add_argument(
        'output',
        nargs='?',
        help='Output G-code file (optional, defaults to overwriting input)'
    )
    
    parser.add_argument(
        '--dx',
        type=float,
        default=0.35,
        help='X-axis backlash compensation in mm (default: 0.35)'
    )
    
    parser.add_argument(
        '--dy',
        type=float,
        default=0.35,
        help='Y-axis backlash compensation in mm (default: 0.35)'
    )
    
    # Enable argcomplete if available
    if argcomplete:
        argcomplete.autocomplete(parser)
    
    return parser.parse_args()

def process_gcode(lines, dx, dy):
    """
    Apply backlash compensation to G-code lines
    
    Args:
        lines: List of G-code lines
        dx: X-axis compensation value
        dy: Y-axis compensation value
    
    Returns:
        List of processed G-code lines
    """
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

            # Update direction only if there's actual movement
            # сохраняем направление, если движение есть, иначе не меняем
            if abs(delta_x) > 0.0001:
                dir_x = math.copysign(1, delta_x)
            if abs(delta_y) > 0.0001:
                dir_y = math.copysign(1, delta_y)
            
            # Calculate compensated coordinates
            comp_x = target_x
            comp_y = target_y
            comp_start_x = last_target_x
            comp_start_y = last_target_y
            
            if dir_x > 0:
                # Positive movement: add DX
                comp_x += dx
                comp_start_x += dx
            
            if dir_y > 0:
                comp_y += dy
                comp_start_y += dy
            
            # Debug output (commented out by default)
            # output_lines.append(f"; from: ({last_target_x}, {last_target_y}) to ({target_x}, {target_y}) delta: ({delta_x}, {delta_y})")
            # output_lines.append(f"; comp: ({comp_start_x}, {comp_start_y}) to ({comp_x}, {comp_y})")
            # output_lines.append(f"; last_comp: ({last_comp_x}, {last_comp_y}) comp_start: ({comp_start_x}, {comp_start_y})")

            # Add backlash take-up moves if we have skip from last_comp to comp_start (direction changed)
            if (abs(comp_start_x - last_comp_x) > 0.0001 or 
                abs(comp_start_y - last_comp_y) > 0.0001):
                # Create take-up move without extrusion
                take_up_cmd = f"G1 X{comp_start_x} Y{comp_start_y} ; Backlash take-up"
                # Add take-up lines before the compensated move
                output_lines.append(take_up_cmd)
            
            # Apply compensation to the line
            if x_match and abs(comp_x - target_x) > 0.0001:
                # Positive movement: replace X coordinate
                processed_line = re.sub(
                    r'X[-\d.]+', 
                    f"X{comp_x}", 
                    processed_line, 
                    count=1
                )
            
            if y_match and abs(comp_y - target_y) > 0.0001:
                # Positive movement: replace Y coordinate
                processed_line = re.sub(
                    r'Y[-\d.]+', 
                    f"Y{comp_y}", 
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
    print(f"Backlash compensation applied: X={dx}mm, Y={dy}mm")
    print(f"Compensation only for positive movements")
    
    return output_lines

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Determine output file
    if args.output:
        outfile = args.output
    else:
        outfile = args.input
        print(f"Warning: Overwriting input file {args.input}", file=sys.stderr)
    
    # Read input file
    try:
        with open(args.input, "r") as f:
            gcode_lines = f.read().splitlines()
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Process G-code with specified backlash values
    new_lines = process_gcode(gcode_lines, args.dx, args.dy)
    
    # Write output file
    try:
        with open(outfile, "w") as f:
            f.write("\n".join(new_lines))
        print(f"Output saved to: {outfile}")
    except IOError as e:
        print(f"Error writing file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
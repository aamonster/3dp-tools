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
from itertools import islice


# limit for applying take-up: avoid it on smooth lines
# basically calculated as jerk/speed
take_up_tolerance = 8/40 # dimensionless

take_up_speed = 8/40 # dimensionless: how many dx compensation we can apply for length L

# for searching h/v lines (to apply take-up during the line)
horizontal_vertical_tolerance = 0.1 # mm

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
    
def clamp(value, min_val, max_val):
    if value < min_val:
        return min_val
    elif value > max_val:
        return max_val
    else:
        return value
    
def format3(number):
    return f"{number:.3f}".rstrip('0').rstrip('.')
    
def strip_comment(line):
    """Removes comment from G-code line"""
    comment_pos = line.find(';')
    if comment_pos != -1:
        return line[:comment_pos]
    return line
    
def is_movement(line):
    # Only G0/G1/G2/G3/G5 moves
    return (line.startswith('G0') or
            line.startswith('G1') or
            line.startswith('G2') or
            line.startswith('G3') or
            line.startswith('G5'))

def is_linear_movement(line):
    # Only G0/G1 moves (G2/G3/G5 need more complex processing – recalculate I, J etc)
    return (line.startswith('G0') or
            line.startswith('G1'))


def get_coord(line, coord_name, default_value=0.0):
    """
    Extracts value from G-code line
    """
    # regex cache
    if not hasattr(get_coord, '_patterns'):
        get_coord._patterns = {}

    # add pattern if not exists
    if coord_name not in get_coord._patterns:
        pattern_str = rf'{coord_name}([+-]?\d*\.?\d*)'
        get_coord._patterns[coord_name] = re.compile(pattern_str)
    
    pattern = get_coord._patterns[coord_name]

    clean_line = strip_comment(line)
    match = pattern.search(clean_line)
    
    val = float(match.group(1)) if match else default_value
    #print(f"get: {coord_name}={val} from {clean_line}, match={match}, pattern={pattern}")

    
    return float(match.group(1)) if match else default_value

# wrappers
def get_x(line, default=0.0):
    return get_coord(line, 'X', default)

def get_y(line, default=0.0):
    return get_coord(line, 'Y', default)

def get_z(line, default=0.0):
    return get_coord(line, 'Z', default)

def get_f(line, default=0.0):
    return get_coord(line, 'F', default)

def get_e(line, default=0.0):
    return get_coord(line, 'E', default)

def replace_xy(line, x=None, y=None):
    """
    Replace existing X/Y with new ones, insert missing ones in reverse order
    
    Args:
        line: G-code line
        x: new X value (None = keep original or don't add)
        y: new Y value (None = keep original or don't add)
    
    Returns:
        Modified G-code line
    """
    # Extract comment
    line, *comment = line.split(';', 1)
    comment = f";{comment[0]}" if comment else ''
    
    # Split into parts
    parts = line.strip().split()
    if not parts:
        return line + comment
    
    new_parts = []
    found_x = False
    found_y = False
    
    # Process each part - REPLACE existing ones
    for part in parts:
        if part[0] == 'X' and x is not None:
            new_parts.append(f"X{x}")
            found_x = True
        elif part[0] == 'Y' and y is not None:
            new_parts.append(f"Y{y}")
            found_y = True
        else:
            new_parts.append(part)
    
    # Insert missing ones in REVERSE order (Y then X)
    # This ensures X comes before Y in the final result
    insert_pos = 1  # After command
    
    if y is not None and not found_y:
        new_parts.insert(insert_pos, f"Y{y}")
        # Don't increment pos - X will be inserted before Y
    
    if x is not None and not found_x:
        new_parts.insert(insert_pos, f"X{x}")
    
    return ' '.join(new_parts) + comment


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
    
    # State tracking
    target_x = 0
    target_y = 0
    delta_x = 0 # movement direction (to detect angle)
    delta_y = 0
    dir_x = 0  # направление последнего движения по X: -1, 0, 1
    dir_y = 0  # направление последнего движения по Y: -1, 0, 1
    
    wanted_comp_dx = 0 # wanted value for backlash compensation; current will pursue it as fast as possible in jerk/acceleration limits
    wanted_comp_dy = 0
    
    current_comp_dx = 0 # it will pursue wanted_comp_dx
    current_comp_dy = 0

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
        if is_movement(original_line):
        
            # State tracking - храним скомпенсированные значения
            last_target_x = target_x
            last_target_y = target_y
            last_delta_x = delta_x
            last_delta_y = delta_y

            # Get target coordinates from input
            target_x = get_x(original_line, last_target_x)
            target_y = get_y(original_line, last_target_y)
            target_e = get_e(original_line, 0)
            #output_lines.append(f"; x:{target_x}, y:{target_y}, e:{target_e}")

            # Calculate deltas from original targets
            delta_x = target_x - last_target_x
            delta_y = target_y - last_target_y

            # check if g-code leads to stop for changing direction. If so – we can perform take-up
            # simple approximation – by angle presuming v=V_MAX
            cross = delta_x * last_delta_y - delta_y * last_delta_x
            dot = delta_x * last_delta_x + delta_y * last_delta_y
            # cross = L1*L2*sin(angle); dot = L1*L2*cos(angle)
            # tan(angle) = cross/dot but if dot==0 - stop for sure
            tan_a = cross/dot if dot>1e-2 else 100
            # printer will probably stop here so it's safe to add take-up movement
            can_stop = tan_a>take_up_tolerance*2 # ??? should really be something more smart but...

            is_linear = is_linear_movement(original_line)
            # for cases where we cannot work without take-up (like G2, G3 – I'm too lazy to recalculate I/J so just perform take-up)
            must_stop = not is_linear

            # skip lines without x/y movement
            # TODO: if it has extrusion – maybe integrate with take-up
            if delta_x == 0 and delta_y == 0:
                output_lines.append(original_line)
                continue


            # look-ahead for horizontal/vertical lines (to take sign from next line)
            # if abs(delta_x)=0 - it's better to take dir_x from next line
            if abs(delta_x) < horizontal_vertical_tolerance:
                future_lines_iterator = islice(lines, line_num + 1, None)
                for future_line in future_lines_iterator:
                    if is_movement(future_line):
                        # take total direction of all segments from last_target_x to current, if big enough - break
                        # TODO: maybe consider current backlash direction and use horizontal_vertical_tolerance limit in one direction and dx in opposite
                        future_x = get_x(future_line, last_target_x)
                        delta_x = future_x - last_target_x
                        if abs(delta_x) >= horizontal_vertical_tolerance:
                            break

            # if abs(delta_x)=0 - it's better to take dir_x from next line
            if abs(delta_y) < horizontal_vertical_tolerance:
                future_lines_iterator = islice(lines, line_num + 1, None)
                for future_line in future_lines_iterator:
                    if is_movement(future_line):
                        # take total direction of all segments from last_target_y to current, if big enough - break
                        # TODO: maybe consider current backlash direction and use horizontal_vertical_tolerance limit in one direction and dy in opposite
                        future_y = get_y(future_line, last_target_y)
                        delta_y = future_y - last_target_y
                        if abs(delta_y) >= horizontal_vertical_tolerance:
                            break
                    

            # Update direction only if there's actual movement
            # сохраняем направление, если движение есть, иначе не меняем
            if abs(delta_x) > 0.0001:
                dir_x = math.copysign(1, delta_x)
            if abs(delta_y) > 0.0001:
                dir_y = math.copysign(1, delta_y)

            if dir_x > 0:
                # Positive movement: add DX
                wanted_comp_dx = dx
            elif dir_x < 0:
                wanted_comp_dx = 0
            
            
            if dir_y > 0:
                wanted_comp_dy = dx
            elif dir_y <0:
                wanted_comp_dy = 0

            if can_stop or must_stop:
                # Add backlash take-up moves if appropriate

                take_up_x = wanted_comp_dx - current_comp_dx
                take_up_y = wanted_comp_dy - current_comp_dy

                if (abs(take_up_x) > horizontal_vertical_tolerance or abs(take_up_y) > horizontal_vertical_tolerance):
                    # minor hack for now: if next line is vertical or horizontal -
                    # we can ignore take-up in perpendicular direction
                    # (it will be performed inside of line)
                    # TODO: if possible - apply take-up at start of horizontal/vertical line, not the end (so we can use the hack too)
                    is_vertical = is_linear and abs(target_x - last_target_x) <= abs(target_y - last_target_y)*take_up_tolerance
                    is_horizontal = is_linear and abs(target_y - last_target_y) <= abs(target_x - last_target_x)*take_up_tolerance
                    is_print = target_e > 0
                    is_small = abs(target_x - last_target_x) < horizontal_vertical_tolerance and abs(target_y - last_target_y) < horizontal_vertical_tolerance
                    # TODO: maybe process special case X45.3,Y54.7 -> Y45.34 => Y45.3 -> X54.7 -> Y54.7
                    # (Y decreases then minor decrease less than take-up then increase - so take-up changes direction of this minor movement to opposite)
                    
                    if is_vertical or is_horizontal or (not is_print) or is_small:
                        take_up_x = 0
                        take_up_y = 0

                if (abs(take_up_x) > 0.0001 or abs(take_up_y) > 0.0001):
                    # Calculate compensated coordinates
                    comp_start_x = last_target_x + wanted_comp_dx
                    comp_start_y = last_target_y + wanted_comp_dy
                    
                    current_comp_dx = wanted_comp_dx
                    current_comp_dy = wanted_comp_dy

                    # Create take-up move without extrusion
                    take_up_cmd = f"G1 X{format3(comp_start_x)} Y{format3(comp_start_y)} ; Backlash take-up"
                    # Add take-up lines before the compensated move
                    output_lines.append(take_up_cmd)

            # --- take-up completed (if any), perform actual movement

            comp_avail = max(abs(delta_x), abs(delta_y)) * take_up_speed
            
            # how much we can: change not more than avail (with sign)
            # TODO: take into account previous and current speed vectors (limits will be asymmetric)
            current_comp_dx = clamp(wanted_comp_dx, current_comp_dx-comp_avail, current_comp_dx+comp_avail)
            current_comp_dy = clamp(wanted_comp_dy, current_comp_dy-comp_avail, current_comp_dy+comp_avail)
            
            #TODO: ? if line is long(so we can catch up before it ended) – split it

            # Apply compensation to the line
            comp_x = target_x + current_comp_dx
            comp_y = target_y + current_comp_dy

            if abs(comp_x-target_x) > 0.0001 or abs(comp_y-target_y) > 0.0001:
                # replace X/Y coordinates
                processed_line = replace_xy(processed_line, x=format3(comp_x), y=format3(comp_y))

            output_lines.append(processed_line)
            
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

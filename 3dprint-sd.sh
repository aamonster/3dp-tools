#!/bin/zsh

# Usage: 3dprint-sd "filename"
# Processes the file with 3dp-compensate.py, copies to SD card (mounted at $SD_PATH)
# and then safely ejects the SD card.
# Supports .gcode and .3mf files - .3mf files are sliced first using OrcaSlicer.

set -euo pipefail

# Path to SD card (mount point)
SD_PATH="/Volumes/K10"

SCRIPT_DIR="${0:A:h}"

# Path to the compensator script (adjust if needed)
COMPENSATOR="${SCRIPT_DIR}/3dp-compensate.py"

# Path to OrcaSlicer (adjust if needed)
ORCA_SLICER="/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"


# Check that an argument was provided
if [[ $# -lt 1 ]]; then
  echo "Error: No filename provided."
  echo "Usage: $0 filename"
  exit 1
fi

filename="$1"

# Check if input file exists
if [[ ! -f "$filename" ]]; then
    echo "Error: File '$filename' not found."
    exit 1
fi

# Check if compensator exists
if [[ ! -f "$COMPENSATOR" ]]; then
    echo "Error: Compensator script not found at $COMPENSATOR"
    exit 1
fi

# Create temporary folder next to source file
TEMP_DIR=$(mktemp -d "${filename}.preprocessed.XXXXXX")
echo "📁 Created temporary folder: $TEMP_DIR"

# Cleanup function to remove temp folder on exit
cleanup() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        # comment next line for debugging
        rm -rf "$TEMP_DIR"
        echo "🧹 Removed temporary folder: $TEMP_DIR"
    fi
}

# Set trap to cleanup on script exit (success, error, or interrupt)
trap cleanup EXIT INT TERM

# Determine file extension and process accordingly
file_ext="${filename##*.}"
file_ext_lower=$(echo "$file_ext" | tr '[:upper:]' '[:lower:]')

# Temporary file for processed G-code (final output before compensation)
TEMP_GCODE=""
# Temporary file for intermediate results (if slicing needed)
SLICED_GCODE=""

if [[ "$file_ext_lower" == "3mf" ]]; then
    echo "📦 Input is 3MF file - slicing with OrcaSlicer first..."
    
    # Check if unzip is available (needed for extraction)
    if ! command -v unzip &> /dev/null; then
        echo "Error: unzip not found. Please install it."
        exit 1
    fi
    
    # Create temporary file for the sliced output (as .3mf container)
    SLICED_3MF="${TEMP_DIR}/sliced.3mf"
    
    # Check if OrcaSlicer is available
    if [[ ! -x "$ORCA_SLICER" ]]; then
        echo "Error: OrcaSlicer not found at $ORCA_SLICER"
        exit 1
    fi
    
    # Slice the 3MF file to a .3mf container (which includes G-code)
    echo "Slicing $filename to temporary .3mf container..."
    if ! "$ORCA_SLICER" "$filename" --slice 0 --export-3mf "$SLICED_3MF"; then
        echo "Error: Slicing failed"
        exit 1
    fi
    echo "✅ Slicing complete"
    
    # Extract the actual G-code from the container
    echo "Extracting G-code from sliced container..."
    # The G-code inside is typically at Metadata/plate_1.gcode
    if ! unzip -p "$SLICED_3MF" "Metadata/plate_1.gcode" > "${TEMP_DIR}/sliced.gcode"; then
        echo "Error: Failed to extract G-code from sliced file"
        exit 1
    fi
    
    # Set TEMP_GCODE to the extracted G-code file
    TEMP_GCODE="${TEMP_DIR}/sliced.gcode"
    echo "✅ G-code extracted to: $TEMP_GCODE"
    
    # Optionally remove the .3mf container to save space (can be kept for debugging)
    # rm -f "$SLICED_3MF"
    
elif [[ "$file_ext_lower" == "gcode" || "$file_ext_lower" == "g" ]]; then
    echo "📄 Input is G-code file - processing directly"
    # Create a temporary file for the compensated output
    TEMP_GCODE="${TEMP_DIR}/input.gcode"
    # Copy original to temp folder as input for compensator
    cp "$filename" "$TEMP_GCODE"
else
    echo "Error: Unsupported file type. Please provide .3mf or .gcode file"
    exit 1
fi

# Create final compensated file in temp folder
FINAL_TEMP="${TEMP_DIR}/final.gcode"

echo "⚙️ Processing with backlash compensation..."
if ! "$COMPENSATOR" "$TEMP_GCODE" "$FINAL_TEMP"; then
    echo "Error: Compensation failed"
    exit 1
fi

echo "✅ Compensation complete"

# Wait until the SD card is mounted and writable
if [[ ! -d "$SD_PATH" || ! -w "$SD_PATH" ]]; then
  echo "Waiting for SD card at $SD_PATH with write access..."
  while [[ ! -d "$SD_PATH" || ! -w "$SD_PATH" ]]; do
    sleep 1
  done
  echo "✅ SD card detected and writable."
fi

# Copy the processed file to the SD card, renaming it to print.gcode
if [[ -f "$FINAL_TEMP" ]]; then
    rsync -ah --progress "$FINAL_TEMP" "$SD_PATH/print.gcode"
    echo "✅ File copied to SD card as print.gcode"
else
    echo "Error: Processed file not found"
    exit 1
fi

# Eject the SD card volume
diskutil eject "$SD_PATH"
echo "✅ SD card ejected safely."

# Cleanup happens automatically via trap

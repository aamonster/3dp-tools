#!/bin/zsh

# Usage: 3dprint-sd "filename"
# Processes the file with 3dp-compensate.py, copies to SD card (mounted at $SD_PATH)
# and then safely ejects the SD card.

set -euo pipefail

# Путь к флешке (точка монтирования)
SD_PATH="/Volumes/K10"

SCRIPT_DIR="${0:A:h}"

# Path to the compensator script (adjust if needed)
COMPENSATOR="${SCRIPT_DIR}/3dp-compensate.py"


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

# Temporary file for processed G-code
TEMP_FILE=$(mktemp "${filename}.processed_XXXXXX")

# Process the file through compensator
echo "Processing $filename with backlash compensation..."
if ! "$COMPENSATOR" "$filename" "$TEMP_FILE"; then
    echo "Error: Compensation failed"
    rm -f "$TEMP_FILE"
    exit 1
fi

echo "Compensation complete, temp file: $TEMP_FILE"

# Wait until the SD card is mounted and writable
if [[ ! -d "$SD_PATH" || ! -w "$SD_PATH" ]]; then
  echo "Waiting for SD card at $SD_PATH with write access..."
  while [[ ! -d "$SD_PATH" || ! -w "$SD_PATH" ]]; do
    sleep 1
  done
  echo "SD card detected and writable."
fi


# Copy the processed file to the SD card, renaming it to print.gcode
if [[ -f "$TEMP_FILE" ]]; then
    rsync -ah --progress "$TEMP_FILE" "$SD_PATH/print.gcode"
    echo "File copied to SD card as print.gcode"
    
    # Clean up temp file
    rm -f "$TEMP_FILE"
    echo "Temporary file removed"
else
    echo "Error: Processed file not found"
    exit 1
fi

# Eject the SD card volume
diskutil eject "$SD_PATH"
echo "SD card ejected safely."
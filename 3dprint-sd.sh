#!/bin/zsh

# Usage: 3dprint-sd "filename"
# Copies the given file to the SD card (mounted at $SD_PATH)
# and then safely ejects the SD card.

set -euo pipefail

# Путь к флешке (точка монтирования)
SD_PATH="/Volumes/K10"

# Check that an argument was provided
if [[ $# -lt 1 ]]; then
  echo "Error: No filename provided."
  echo "Usage: $0 filename"
  exit 1
fi

filename="$1"

# Wait until the SD card is mounted and writable
if [[ ! -d "$SD_PATH" || ! -w "$SD_PATH" ]]; then
  echo "Waiting for SD card at $SD_PATH with write access..."
  while [[ ! -d "$SD_PATH" || ! -w "$SD_PATH" ]]; do
    sleep 1
  done
  echo "SD card detected and writable."
fi

# Copy the file to the SD card, renaming it to print.gcode
# cp "$filename" "$SD_PATH/print.gcode"
rsync -ah --progress "$filename" "$SD_PATH/print.gcode"
echo "File copied to SD card."

# Eject the SD card volume
diskutil eject "$SD_PATH"
echo "SD card ejected safely."

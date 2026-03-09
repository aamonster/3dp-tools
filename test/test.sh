#!/bin/bash
mkdir -p processed

for a in *.gcode
do
    echo "Processing $a"
    ../3dp-compensate.py "$a" "processed/$a"
    #opendiff "$a" "processed/$a"
done

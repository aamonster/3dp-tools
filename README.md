# aamonster's tools for 3d print
Developed for using with EasyThreed K10
basically developed for MacOS

## 3dp-sd.py
Tool for pushing file to SD-card:
- wait for SD to mount
- write file into print.gcode file  
  (I use the only one filename because of K10 selects random file if there is more than one)
- eject SD-card

3dp-compensate called before sending to SD
(via temporary file, for debug you can Ctrl-C while waiting for SD –
it will be nearby to source file with name like myfile.gcode.processed_jFsclF)

TODO: if input file is m3f, not gcode – use `orca-slicer --slice 0 --export-gcode output.gcode input.3mf`
(proposed usage path: save file in Orca and print, no gcode file remains in storage).

TODO: maybe convert stl files too. Maybe I should use keys like
```
orca-slicer --input part.stl --output part.gcode \
  --preset "PETG_0.25mm" \
  --override "layer_height=0.15,line_width=0.45,infill=30"
```
As an option – use 3mf-file with the same name (if exists) as template:
```
# Example of Python script to unpack Orca settings
import zipfile
import json
import os

# 1. Unpack 3MF as a ZIP
with zipfile.ZipFile('шаблон.3mf', 'r') as z:
    # Extract settings files
    z.extract('Metadata/print_profile.config', 'temp/')
    z.extract('Metadata/project_settings.config', 'temp/')
    z.extract('Metadata/slice_info.config', 'temp/')

# 2. Use settings
os.system('''
orca-slicer \
  --load-settings "temp/print_profile.config;temp/project_settings.config" \
  --load-settings "temp/slice_info.config" \
  --arrange 1 \
  --slice 0 \
  --export-gcode result.gcode \
  part.gcode
''')
```

TODO: maybe autoconvert scad files too (`openscad -o my_design.stl my_design.scad`). Then process stl.
- maybe I should allow to get some "--override" values from scad file. Or maybe any keys for Orca.


## 3dp-compensate
Tool for post-processing G-code to compensate K10 quirks and problems
- Currently compensates backlash in X and Y axes

TODO: compensate Z offset (because of Orca Slicer "Z Offset" setting sometimes breaks Preview for G2/G3 codes)

TODO: try to simulate Linear Advance

To use autocomplete in zsh:
```
    python3 -m venv venv
    source venv/bin/activate
    pip3 install argcomplete
    eval "$(register-python-argcomplete --shell zsh 3dp-compensate.py)"
```
Can be performed globally via pipx
```
brew install pipx
pipx ensurepath
pipx install argcomplete

# install script (we need setup.py or pyproject.toml)
# Or temporary use --break-system-packages for global installation
pip3 install --user argcomplete --break-system-packages
```

### backlash compensation:
- When head moves left-to-right (X++) or back-to-forward (Y++) - dx/dy added to final coordinate to compensate backlash;
- Between X++ and X-- movement (when head changes direction thus it have to take-up backlash) we add travel by DX (take-up move)
- The same between Y++ and Y--

DX and DY calibrated for my printer - see calibration experiments caliber/readme.md, caliber/xy/test-backlash.3mf

Problems:
- take-up movement is often almost perpendicular to regular movement so printer stop head - minor blob at this point

Solution: if it's possible to integrate take-up into next or previous move (they are perpendicular or almost perpendicular) - do it.
Maybe use soft take-up switching on - use values less than DX in some cases

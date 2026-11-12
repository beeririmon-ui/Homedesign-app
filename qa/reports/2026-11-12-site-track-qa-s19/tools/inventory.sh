#!/bin/bash
# The rasters under the live assets/renders (read only): path, size, mtime. Taken before and after the scan, so a file
# render-agent wrote or changed during it is known (the scan reads the live tree; nothing is written there).
find /home/user/homedesign-app/assets/renders -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' -o -iname '*.avif' -o -iname '*.gif' -o -iname '*.tif' -o -iname '*.tiff' \) -printf '%P\t%s\t%T@\n' | sort

#!/bin/bash
# The live tree while I measure (read only): HEAD, git status, and the rasters under assets/renders (path, size, mtime).
# Taken at the start and the end, so a commit or a file written by another agent during the round is known.
R=/home/user/homedesign-app
echo "HEAD $(git -C $R rev-parse --short HEAD)  $(date -u +%FT%TZ)"
git -C $R status --short | head -200
echo "--- renders"
find $R/assets/renders -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' -o -iname '*.avif' \) -printf '%P\t%s\t%T@\n' | sort | md5sum

#!/usr/bin/env python3
"""
prep_plate_kids.py: the model input of the K-boy empty plate, render-agent, 2026-11-24. 0 tokens.
MB0's recipe (master stage1-2026-11-17/tools/prep_plate.py, imported, nothing changed there): the lit clay K-boy-plate recoloured
through its id pass, chroma per material from base.png (the living room), as the work room's prep_plate_work.py. The K-boy ids:
plaster 1-4, 9, 12; the olive band 5, 8 and its skirting 19 (#A8A88E's a* b*: -4.6, 13.5); oak 10 (joints 11); walnut 20, 21, 23-25
(the bed boards and frame, the desk, the chair); bronze 13; limestone 14; the bare mattress 22.

  python3 prep_plate_kids.py <clay.png> <clay-id.png> <out.png> <out.json>
"""
import os
import sys

sys.path.insert(0, "/home/user/homedesign-app/assets/renders/master/warm-modern/stage1-2026-11-17/tools")
import prep_plate as P  # noqa: E402

P.TARGET.clear()
P.TARGET.update({"plaster": ((1, 2, 3, 4, 6, 9, 12), 0.5, 4.0), "band": ((5, 8, 19), -4.6, 13.5), "oak": ((10,), 7.6, 16.3),
                 "walnut": ((20, 21, 23, 24, 25), 11.4, 17.6), "bronze": ((13,), 2.4, 5.1), "stone": ((14,), 2.5, 13.5),
                 "mattress": ((22,), 0.7, 4.6)})

if __name__ == "__main__":
    P.main(*sys.argv[1:5])

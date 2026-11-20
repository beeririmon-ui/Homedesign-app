#!/usr/bin/env python3
"""
prep_plate_work.py: the model input of the W0 empty plate, render-agent, 2026-11-20. 0 tokens.
MB0's recipe (master stage1-2026-11-17/tools/prep_plate.py, imported, nothing changed there): the lit clay W0-plate recoloured through
its id pass, chroma per material from base.png (the living room). The W0 ids: plaster 1-6, 9, 12, 17, 18; oak 10 (joints 11); walnut
20-22, 24, 25 (the desk, drawer, shelf and chair); the drawer recess 23 as the dark walnut; bronze 13; limestone 14; the cognac seat 26.

  python3 prep_plate_work.py <clay.png> <clay-id.png> <out.png> <out.json>
"""
import os
import sys

sys.path.insert(0, "/home/user/homedesign-app/assets/renders/master/warm-modern/stage1-2026-11-17/tools")
import prep_plate as P  # noqa: E402

P.TARGET.clear()
P.TARGET.update({"plaster": ((1, 2, 3, 4, 5, 6, 9, 12, 17, 18), 0.5, 4.0), "oak": ((10,), 7.6, 16.3),
                 "walnut": ((20, 21, 22, 24, 25), 11.4, 17.6), "dark walnut": ((23,), 7.0, 9.0), "bronze": ((13,), 2.4, 5.1),
                 "stone": ((14,), 2.5, 13.5), "cognac leather": ((26,), 16.0, 24.0)})

if __name__ == "__main__":
    P.main(*sys.argv[1:5])

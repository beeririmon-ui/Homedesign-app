#!/usr/bin/env python3
"""
prep_plate_mb1.py: the model input of the MB1 empty plate, render-agent, 2026-11-19. 0 tokens.
MB0's recipe (stage1-2026-11-17/tools/prep_plate.py, imported, nothing changed there): the lit clay MB1-plate recoloured through its id
pass, chroma per material from base.png; the MB1 shelf (28) and the plan-B bench (29, 30) take the walnut's (a* 11.4, b* 17.6).

  python3 prep_plate_mb1.py <clay.png> <clay-id.png> <out.png> <out.json>
"""
import os
import sys

sys.path.insert(0, "/home/user/homedesign-app/assets/renders/master/warm-modern/stage1-2026-11-17/tools")
import prep_plate as P  # noqa: E402

P.TARGET["walnut"] = ((20, 21, 24, 25, 28, 29, 30), 11.4, 17.6)

if __name__ == "__main__":
    P.main(*sys.argv[1:5])

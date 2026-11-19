#!/usr/bin/env python3
"""
prep_b1_plate.py: the model input of the B1 empty plate, render-agent, 2026-11-19. 0 tokens.
As B2's prep_plate.py (the same targets, the same rule: chroma only, the clay's lightness and shading kept, half the local chroma
variation), on the lit clay B1-plate (assets/blockout/house/framing/wm-bath-b1-2026-11-19/), with B1's own ids added:
  plaster (1-4, 6, 28 the WC ledge box, 32 the window reveals); limestone (5, 9, 11, 12, 14, 29 the ledge slab and sill, 4 L* down);
  joints (10, 13); walnut (20-22); bronze (15, 18, 25, 27 the flush plate, 30 the window frame); warm white ceramic (24, 26 the WC).
The fluted glass (31) and everything else stay as the clay drew them.

  python3 prep_b1_plate.py <clay.png> <clay-id.png> <out.png>
"""
import sys

sys.path.insert(0, "/home/user/homedesign-app/assets/renders/bath/warm-modern/stage1-2026-11-17/tools")
import prep_plate as P  # noqa: E402

P.TARGET = {"plaster": ((1, 2, 3, 4, 6, 28, 32), 0.5, 4.0), "stone": ((5, 9, 11, 12, 14, 29), 2.5, 13.5), "walnut": ((20, 21, 22), 11.4, 17.6),
            "bronze": ((15, 18, 25, 27, 30), 2.4, 5.1), "basin": ((24, 26), 0.5, 5.0)}

if __name__ == "__main__":
    P.main(*sys.argv[1:4])

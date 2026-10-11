import sys, json
sys.path.insert(0, "/home/user/homedesign-app/scripts/ae")
import scale
for room in ["living-room", "dining-room", "master"]:
    cards = scale.existing_cards(room)
    print("=====", room)
    for slot in sorted(cards):
        for c in cards[slot]:
            print("  %-22s %-60s %-10s L=%-7s %s %s" % (slot, c["card_id"][:60], c["supplier"][:10], c["landed_ils"], c["ship_src"], {k: v for k, v in c["fits"].items() if v is not None}))

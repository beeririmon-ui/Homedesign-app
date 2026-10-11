"""Contact sheets of the shortlisted images, per room and slot, 12 per sheet (4 x 3), to look at.

python3 -I sheets.py <room>  -> scratch/sheets/<room>-<slot>-<n>.jpg + index json
"""
import json, os, sys, textwrap
from PIL import Image, ImageDraw, ImageFont

WORK = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.dirname(WORK)
IMG = os.path.join(SCR, "scale-images")
OUT = os.path.join(SCR, "sheets")
os.makedirs(OUT, exist_ok=True)
W, H, IM, COLS, ROWS = 360, 470, 350, 4, 3
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    FONTB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
except OSError:
    FONT = FONTB = ImageFont.load_default()


def run(room):
    rs = {(r["slot"], r["item_id"]): r for r in json.load(open(os.path.join(WORK, "prep-%s.json" % room)))}
    sh = json.load(open(os.path.join(WORK, "short-%s.json" % room)))
    index = {}
    for slot, v in sh["slots"].items():
        items = v["items"]
        if not items:
            continue
        styles_of = {}
        for st, xs in v["per_style"].items():
            for x in xs:
                styles_of.setdefault(x["item_id"], []).append(st[:4])
        for page in range(0, len(items), COLS * ROWS):
            chunk = items[page:page + COLS * ROWS]
            rows = (len(chunk) + COLS - 1) // COLS
            sheet = Image.new("RGB", (W * COLS, H * rows), "white")
            d = ImageDraw.Draw(sheet)
            for i, iid in enumerate(chunk):
                n = page + i + 1
                r = rs[(slot, iid)]
                x, y = (i % COLS) * W, (i // COLS) * H
                try:
                    im = Image.open(os.path.join(IMG, iid + ".jpg")).convert("RGB")
                    im.thumbnail((IM, IM))
                    sheet.paste(im, (x + 5, y + 5))
                except Exception:
                    d.text((x + 20, y + 150), "no image", fill="red", font=FONTB)
                d.rectangle([x + 5, y + 5, x + 45, y + 30], fill="black")
                d.text((x + 9, y + 7), "%d" % n, fill="white", font=FONTB)
                ty = y + IM + 10
                d.text((x + 5, ty), "%s  %s" % (iid[-7:], ",".join(styles_of.get(iid, []))), fill="black", font=FONT)
                d.text((x + 5, ty + 16), "$%.2f+%.2f q%d  L%.0f  m%d%%  %s" % (r["price_usd"], r["ship_usd"], r["qty"], r["landed_ils"], round(r["margin_pct"] * 100), r.get("size")), fill="black", font=FONT)
                d.text((x + 5, ty + 32), (r.get("sku_label") or "")[:48], fill="#333", font=FONT)
                for k, line in enumerate(textwrap.wrap(r.get("title") or "", 50)[:4]):
                    d.text((x + 5, ty + 48 + 15 * k), line, fill="#666", font=FONT)
                index["%s#%d" % (slot, n)] = iid
            fn = os.path.join(OUT, "%s-%s-%d.jpg" % (room, slot, page // (COLS * ROWS) + 1))
            sheet.save(fn, quality=85)
    json.dump(index, open(os.path.join(OUT, "%s-index.json" % room), "w"), indent=0)
    print(room, len(index))


if __name__ == "__main__":
    for room in sys.argv[1:]:
        run(room)

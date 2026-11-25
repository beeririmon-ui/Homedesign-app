# Brief: kids' art, contact sheets from the existing AE cards (general-purpose, 2026-11-25)

## Why
FB12 asks for child-appropriate art in the kids' rooms, as a wheel of about 10 sets per room. The designer's proposal is `docs/proposals/wm-fb12-2026-11-25.md`, ב.3–ב.7.

ב.7 says two existing cards can already give 4–6 sets per room. Their designs need an image review first, by the designer. The designer can't download, so this run prepares the images.

## The task
1. **The two cards:**
   - `data/products/kids/framed-prints/framed-prints-aliexpress-watercolour-sun-and-rainbow-nursery-prints.json`, about 33 designs × sizes;
   - `data/products/kids/framed-prints/framed-prints-aliexpress-watercolour-bunny-nursery-prints.json`, about 23 designs.
2. **One image per design.**
   - **Grouping:** group `options.skus` by the design value (not size or frame). Take the first SKU's `image` URL for each design.
   - **Download:** the URLs are supplier CDN images that came from the official API. Fetch each URL directly once, with plain `curl` and no special headers. No listing pages, no scraping, no scraper services.
   - **Where:** `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/kids-art-review/raw/` (an empty new folder).
3. **Contact sheets** in `.../scratchpad/kids-art-review/`:
   - one sheet per card, about 12 designs per sheet, so several sheets per card;
   - each tile at least 360 px on its long side, with a printed label: the design value exactly as in the card, and a short number (S01…, B01…).
4. **An index,** `.../scratchpad/kids-art-review/index.json`: for each number, the card id, the design value, the SKU ids by size, whether a 30×40 (or 30×42) unframed SKU exists, the image path, and the pixel size of the downloaded image.

## Fixed rules
- Images stay in the scratchpad. Nothing goes into the repo, and no commits.
- Any Python that reads downloaded images runs with `python3.12 -I`, from a script kept outside the download folder.
- **The disk is tight** (about 1.6 GB free). Use JPG sheets at quality 85, and keep the raw folder small.
- No keys, no contact with anyone, no edits under `data/`, `docs/`, `assets/` or `site/`.
- Never `git stash`, `checkout`, `reset` or `commit`.
- Return a short Hebrew summary: the number of designs per card, the sheet paths, and any URL that failed.

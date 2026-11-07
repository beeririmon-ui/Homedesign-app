# Evidence of the story prototype (measured headless, Chromium + SwiftShader)

Run 2026-11-07T11:16:33.049Z; 30 screenshots under screens/. The figures are in evidence.json; README.md reads them.

## Screenshots
- `screens/desk-1-opening.png`: 1280: the opening, Nordic A at rest (no dot), the title and the story line, the test mark
- `screens/desk-2-dots.png`: 1280: the dots after the pointer moves (one per faithful product the screen shows)
- `screens/desk-3-sheet.png`: 1280: "קנה את המראה" from a dot: the card's photo, the name, the credit with the price, the action, the links and the browse
- `screens/desk-3b-added.png`: 1280: after "הוספה לסל": the button says "נוסף לסל", the cart count in the top band is 1
- `screens/desk-3c-sheet-no-price.png`: 1280: a product without a price yet (the pendant): the caption says so, no add button, no disabled button
- `screens/desk-4-list.png`: 1280: "כל המוצרים בתמונה" for Nordic A: the card photo or the colour swatch, the name (opens the sheet), the credit; the rug without a dot (QA: partly)
- `screens/desk-4b-list-full.png`: 1280: the whole list section
- `screens/desk-5-second-frame.png`: 1280: the story scroll, Nordic B (the window corner), at rest
- `screens/desk-6-tool.png`: 1280: the way into the tool: "עצב בעצמך" opens the room engine (/rooms/living-room/)
- `screens/desk-7-other-styles.png`: 1280: "בסגנונות אחרים": warm modern marked "טיוטה · כמעט מוכן", the next styles only as "בגיליונות הבאים"
- `screens/desk-8-warm-modern.png`: 1280: warm modern A (QA: almost), the draft mark
- `screens/desk-9-cart.png`: 1280: the test cart (an in-browser mock of the store API's cart)
- `screens/phone-1-opening.png`: 400: the opening, Nordic A at rest (no dot), the title and the story line, the test mark
- `screens/phone-2-dots.png`: 400: the dots after a touch (one per faithful product the 4:5 crop carries)
- `screens/phone-3-sheet.png`: 400: "קנה את המראה" from a dot: the card's photo, the name, the credit with the price, the action, the links and the browse
- `screens/phone-3b-added.png`: 400: after "הוספה לסל": the button says "נוסף לסל", the cart count in the top band is 1
- `screens/phone-3c-sheet-no-price.png`: 400: a product without a price yet (the pendant): the caption says so, no add button, no disabled button
- `screens/phone-4-list.png`: 400: "כל המוצרים בתמונה" for Nordic A: the card photo or the colour swatch, the name (opens the sheet), the credit; the rug without a dot (QA: partly)
- `screens/phone-4b-list-full.png`: 400: the whole list section
- `screens/phone-5-second-frame.png`: 400: the story scroll, Nordic B (the window corner), at rest
- `screens/phone-6-tool.png`: 400: the way into the tool: "עצב בעצמך" opens the room engine (/rooms/living-room/)
- `screens/phone-7-other-styles.png`: 400: "בסגנונות אחרים": warm modern marked "טיוטה · כמעט מוכן", the next styles only as "בגיליונות הבאים"
- `screens/phone-8-warm-modern.png`: 400: warm modern A (QA: almost), the draft mark
- `screens/phone-9-cart.png`: 400: the test cart (an in-browser mock of the store API's cart)
- `screens/desk-k1-dot-focus.png`: 1280: a dot in keyboard focus: every dot shows, the focused one has the double ring, the wall label says its credit
- `screens/desk-k2-sheet-focus.png`: 1280: inside the sheet by keyboard (the page behind is inert)
- `screens/desk-r1-reduced-sheet.png`: 1280: reduced motion, the sheet open (a fade only)
- `screens/phone-r1-reduced-sheet.png`: 400: reduced motion, the sheet open (a fade only)
- `screens/desk-2b-pendant-dot.png`: 1280: Nordic A, v0 0.10: the pendant's dot at the bottom of the shade, clear of the top band; the band's words on the label paper, the 0.35 scrim
- `screens/desk-8b-warm-modern-dots.png`: 1280: warm modern A ed5 (QA: final test): the pendant, now faithful, has its dot under the band

## Problems
- the story leaks into real routes: media/test/story/nordic-A/stamp.json, media/test/story/nordic-B/stamp.json, media/test/story/warm-modern-A/stamp.json

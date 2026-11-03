# Evidence of the test page (measured headless, Chromium + SwiftShader)

Run 2026-11-03T21:23:14.439Z; 40 screenshots under screens/. The figures per check are in evidence.json; README.md maps them to the 25 checks of art direction §10.

## Screenshots
- `screens/desk-cover-1-lqip.png`: the cover at first paint: the LQIP of H0 under the paper, the type not yet printed
- `screens/desk-cover-2-invite.png`: the cover developed: the brand in the band, the cover line in Display, the invitation with its 24 px hairline
- `screens/desk-paper-mid.png`: the paper transition, mid-way: paper over the cover (150 ms out, 200 ms hold)
- `screens/desk-living-after-paper.png`: the living room after the paper transition, the running head "02 · הסלון · נורדי"
- `screens/phone-cover-1-lqip.png`: the cover at first paint: the LQIP of H0 under the paper, the type not yet printed
- `screens/phone-cover-2-invite.png`: the cover developed: the brand in the band, the cover line in Display, the invitation with its 24 px hairline
- `screens/phone-paper-mid.png`: the paper transition, mid-way: paper over the cover (150 ms out, 200 ms hold)
- `screens/phone-living-after-paper.png`: the living room after the paper transition, the running head "02 · הסלון · נורדי"
- `screens/desk-living-rest.png`: the living room at rest, 3 s without input: no marks, no label, nothing on the picture
- `screens/desk-living-marks.png`: the marks after a pointer movement: 6 px ink dots on the products, nothing else
- `screens/desk-living-label.png`: hover on the vase: the product outline and the wall label (name · material · size · price) 12 px above it
- `screens/desk-focus-approach.png`: the approach to the vase, mid-way (1.6 s, --e-approach): the camera moves, the room still whole
- `screens/desk-focus-on.png`: focus mode: the room uniformly soft and a third of a stop darker, the vase sharp and lifted; the variant strip with the credit, "הוספה לסל" and "בחירה"
- `screens/desk-focus-variant-2.png`: the second variant chosen by the arrow key: the thumb ring moves, the credit dissolves; the picture waits for the final layers
- `screens/desk-focus-return.png`: the return, mid-way (1.8 s, --e-land)
- `screens/desk-focus-landed.png`: after the landing: the frame at rest again, pixel for pixel
- `screens/desk-focus-ring-thumb.png`: the keyboard in focus mode: the 2 px ring on the chosen thumb
- `screens/desk1920-living-rest.png`: the living room at rest at 1920×1080 (the 1920 rendition 1:1)
- `screens/desk-reduced-focus.png`: reduced motion: focus mode reached by a 300 ms dissolve, nothing moved
- `screens/desk-dining-rest.png`: the dining room D1 at rest
- `screens/desk-pan-0.png`: the P-D pan block, frame 1 (the registered test clip of 2026-11-02)
- `screens/desk-pan-mid.png`: the pan mid-way, constant speed between the ramps
- `screens/desk-pan-end.png`: the pan at its last frame (D2 of the test clip)
- `screens/desk-states-rest.png`: the states block at rest: primary, secondary, link, the field, the unavailable product
- `screens/desk-states-hover.png`: hover on the primary button (ink-press, 120 ms)
- `screens/desk-states-press.png`: press on the primary button (80 ms)
- `screens/desk-states-added.png`: after the press: "נוסף לסל" in the same button, no toast
- `screens/desk-states-focus-field.png`: the field focused: the 2 px ring
- `screens/desk-states-error.png`: the error state: the message under the field, the field marked
- `screens/desk-states-loading.png`: the loading state: "רגע…" and the 1 px progress hairline, no spinner
- `screens/desk-ring-mark.png`: the ring on a mark (Tab into the room)
- `screens/desk-grid-story.png`: the story page with the 12-column grid overlay at 1280
- `screens/phone-toc.png`: the contents on the phone: the rooms, the unavailable styles "בגיליונות הבאים"
- `screens/phone-living-rest.png`: the living room on the phone at rest: the frame at full height, the view on the Bible window (u 0.567–0.905), the sides by a swipe
- `screens/phone-living-marks.png`: the marks after a touch
- `screens/phone-focus-cushions.png`: the cushions close-up on the phone (FOC2): the strip at the bottom with the credit, the thumbs and "בחירה"
- `screens/phone-grid-story.png`: the story on the phone with the 4-column grid overlay, 24 px margins
- `screens/phone-states.png`: the states block on the phone
- `screens/phone-dining-rest.png`: the dining room on the phone, the view on its window (u 0.33–0.67)
- `screens/phone-pan-0.png`: the pan block on the phone (the mobile variant of the clip)

## Problems
- none (no page errors, no console errors)

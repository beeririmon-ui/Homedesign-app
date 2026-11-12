/**
 * frontend-dev, S19 (2026-11-12): QA's mut-rights.mjs (qa/reports/2026-11-12-site-track-qa-s17/tools/), unchanged but for
 * two mutations added at the end from QA's ת51 list: R17 padded onto a white 4:3 canvas, R18 a grey 3% border. It runs
 * on the live tree's public build (QA_PUB = site/ after `HD_PUBLIC=1 npm run build`), and QA's own scan beside the gate.
 *
 * qa-agent, S17 (2026-11-12): my mutations of a PUBLIC build (HD_PUBLIC=1, dummy analytics token), each on a fresh copy of
 * its dist, against the content-based gate (`check:rights`, --dist=) and my own scan (rights-scan.mjs, S15).
 *   R0  the clean public build
 *   R1  an option picture at its own path               R2  the same bytes as media/og/look-1.webp + og:image
 *   R3  og:image hotlinked to the supplier's CDN         R4  the picture inlined as a data: URI in a page
 *   R6  the story's 321 copies (from the flag build; this public build's story ledger is empty)
 *   — new —
 *   R7  a supplier original resized to 50% and recompressed (JPEG q60), as og:image
 *   R8  a crop: 10% off each side (R8a); the left third off (R8b)
 *   R9  flipped left-right
 *   R10 a light colour shift (brightness +6%, hue +12°, saturation ×1.1)
 *   R11 in CSS: (a) a data: URI background in the main stylesheet; (b) a background file under a non-image name
 *       (media/bg/hero.dat); (c) image-set() hotlinked to another server of the same CDN (ae04.alicdn.com)
 *   R12 the original's bytes under a text name (media/notes/readme.txt)
 *   R13 an SVG file framing a resized copy as a data: URI (<image href="data:…">)
 *   R14 a hotlink to an AliExpress image host no card names (ae-pic-a1.aliexpress-media.com)
 *   R15 a data: URI in CSS broken by line breaks (browsers decode it: forgiving base64)
 *   R16 a resized copy inlined in a JS chunk (what Vite does with a small imported image)
 * R5 (the public build reads the full manifest) needs a rebuild: mut-r5.sh.
 *
 *   QA_PUB=<public copy>/site QA_FLAG=<flag copy>/site QA_DATA=<out dir> QA_TOOLS=<this dir> QA_TMP=<scratch> node mut-rights.mjs
 */
import { spawnSync } from "node:child_process";
import {
  cpSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
  appendFileSync,
  existsSync,
} from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
const PUB = process.env.QA_PUB;
const FLAG = process.env.QA_FLAG;
const DATA = process.env.QA_DATA;
const TOOLS = process.env.QA_TOOLS;
const TMP = process.env.QA_TMP;
const sharp = createRequire(join(PUB, "package.json"))("sharp");
const LOG = join(DATA, "mut-rights.log");
writeFileSync(LOG, "");
const say = (s) => {
  console.log(s);
  appendFileSync(LOG, s + "\n");
};
const CLEAN = join(TMP, "dist-clean");
const D = join(TMP, "d");
rmSync(CLEAN, { recursive: true, force: true });
cpSync(join(PUB, "web/dist"), CLEAN, { recursive: true });
const fresh = () => {
  rmSync(D, { recursive: true, force: true });
  cpSync(CLEAN, D, { recursive: true });
};
const results = {};
function check(name, dist) {
  const json = join(DATA, `rights-${name}.json`);
  const r = spawnSync(
    "npx",
    [
      "--no-install",
      "tsx",
      "tools/check-image-rights.ts",
      `--dist=${dist}`,
      `--json=${json}`,
    ],
    { cwd: PUB, env: { ...process.env, HD_PUBLIC: "1" }, encoding: "utf8" },
  );
  const out = `${r.stdout}\n${r.stderr}`;
  let found = null;
  try {
    found = JSON.parse(readFileSync(json, "utf8")).by_content.found;
  } catch {
    /* none */
  }
  const lines = out
    .split("\n")
    .filter((l) =>
      /by (?:bytes|pixels|host|data-uri)|a file of|names products/.test(l),
    );
  say(`    check:rights exit ${r.status}; found ${JSON.stringify(found)}`);
  for (const l of lines.slice(0, 3)) say(`      ${l.trim().slice(0, 240)}`);
  const s = spawnSync(
    "node",
    [
      join(TOOLS, "rights-scan.mjs"),
      dist,
      join(FLAG, "web/public/media/products"),
      join(PUB, ".cache/supplier-images"),
      join(PUB, "../data/products"),
      join(DATA, `qa-scan-${name}.json`),
    ],
    {
      env: { ...process.env, NODE_PATH: join(PUB, "node_modules") },
      encoding: "utf8",
    },
  );
  const v = (s.stdout.split("\n")[0] ?? "").replace(/^rights-scan \S+: /, "");
  say(`    QA scan: ${v}`);
  results[name] = { gate_exit: r.status, gate_found: found, qa_scan: v };
}

const shop = JSON.parse(
  readFileSync(join(PUB, ".generated/rights/shop.json"), "utf8"),
);
const opt = shop.entries.find(
  (x) =>
    x.source === "shop" && x.rights !== "confirmed" && /\/opt-/.test(x.file),
);
const OPT = join(PUB, opt.file);
// a withheld product's own original in the cache (the supplier's photo as downloaded)
const orig =
  shop.entries.find(
    (x) =>
      x.source === "cache" &&
      x.rights !== "confirmed" &&
      /\.bin$/.test(x.file) &&
      /vase|lamp|basket|planter/.test(x.product),
  ) ?? shop.entries.find((x) => x.source === "cache");
const ORIG = join(PUB, orig.file);
const PAGE = (() => {
  const p = readdirSync(join(CLEAN, "p"))[0];
  return `p/${p}/index.html`;
})();
const CSS = readdirSync(join(CLEAN, "assets"))
  .filter((f) => f.endsWith(".css"))
  .sort(
    (a, b) =>
      readFileSync(join(CLEAN, "assets", b)).length -
      readFileSync(join(CLEAN, "assets", a)).length,
  )[0];
const JS = readdirSync(join(CLEAN, "assets")).filter((f) =>
  f.endsWith(".js"),
)[0];
const CARDURL = /https:\/\/ae01\.alicdn\.com\/kf\/[A-Za-z0-9_./-]+\.jpg/.exec(
  spawnSync(
    "grep",
    [
      "-rhoE",
      "https://ae01\\.alicdn\\.com/kf/[A-Za-z0-9_./-]+\\.jpg",
      join(PUB, "../data/products"),
    ],
    { encoding: "utf8" },
  ).stdout,
)?.[0];
const om = await sharp(ORIG, { failOn: "none" }).rotate().metadata();
say(
  `the option picture: ${opt.file} (${opt.product}); the original: ${orig.file} (${orig.product}, ${om.width}×${om.height}); the page: ${PAGE}; CSS ${CSS}; JS ${JS}`,
);
const addHead = (rel, tag) => {
  const p = join(D, rel);
  writeFileSync(p, readFileSync(p, "utf8").replace("</head>", `${tag}</head>`));
};
const put = (rel, buf) => {
  mkdirSync(join(D, rel, ".."), { recursive: true });
  writeFileSync(join(D, rel), buf);
};
const S = () => sharp(ORIG, { failOn: "none" }).rotate();

say("=== R0 the clean public build");
check("r0", CLEAN);
say("=== R1 an option picture at its own path");
fresh();
put(opt.file.replace(/^web\/public\//, ""), readFileSync(OPT));
check("r1", D);
say("=== R2 the same bytes under another name, as og:image");
fresh();
put("media/og/look-1.webp", readFileSync(OPT));
addHead(
  PAGE,
  '<meta property="og:image" content="https://example.co.il/media/og/look-1.webp">',
);
check("r2", D);
say("=== R3 og:image hotlinked to the supplier CDN");
fresh();
addHead(PAGE, `<meta property="og:image" content="${CARDURL}">`);
check("r3", D);
say("=== R4 inlined as a data: URI");
fresh();
{
  const p = join(D, PAGE);
  writeFileSync(
    p,
    readFileSync(p, "utf8").replace(
      "</body>",
      `<img alt="" src="data:image/webp;base64,${readFileSync(OPT).toString("base64")}"></body>`,
    ),
  );
}
check("r4", D);
const STORY = join(FLAG, "web/dist/media/story/products");
say(
  `=== R6 the story's own copies (${spawnSync("bash", ["-c", `find ${STORY} -type f | wc -l`], { encoding: "utf8" }).stdout.trim()} files from the flag build); this public build's story ledger: ${JSON.parse(readFileSync(join(PUB, ".generated/rights/story.json"), "utf8")).entries.length} entries`,
);
fresh();
cpSync(STORY, join(D, "media/story/products"), { recursive: true });
check("r6", D);
{
  const f = JSON.parse(
    readFileSync(join(DATA, "rights-r6.json"), "utf8"),
  ).findings;
  const files = new Set(f.map((x) => x.where));
  const near = f.filter((x) => (x.hamming ?? 0) > 24);
  say(
    `    R6: ${files.size} files found; ${near.length} by the near-miss rule (dHash ${Math.min(...near.map((x) => x.hamming))}–${Math.max(...near.map((x) => x.hamming))}, MAD ${Math.min(...near.map((x) => x.mad32))}–${Math.max(...near.map((x) => x.mad32))})`,
  );
  results.r6.files = files.size;
  results.r6.near_miss = near.length;
}

say(
  "=== R7 the original resized to 50% and recompressed (JPEG q60), as og:image",
);
fresh();
put(
  "media/og/look-7.jpg",
  await S()
    .resize(Math.round(om.width / 2))
    .jpeg({ quality: 60 })
    .toBuffer(),
);
addHead(
  PAGE,
  '<meta property="og:image" content="https://example.co.il/media/og/look-7.jpg">',
);
check("r7", D);
say("=== R8a a crop: 10% off each side");
fresh();
put(
  "media/journal/crop-a.webp",
  await S()
    .extract({
      left: Math.round(om.width * 0.1),
      top: Math.round(om.height * 0.1),
      width: Math.round(om.width * 0.8),
      height: Math.round(om.height * 0.8),
    })
    .webp()
    .toBuffer(),
);
check("r8a", D);
say("=== R8b a crop: the left third off");
fresh();
put(
  "media/journal/crop-b.webp",
  await S()
    .extract({
      left: Math.round(om.width / 3),
      top: 0,
      width: om.width - Math.round(om.width / 3),
      height: om.height,
    })
    .webp()
    .toBuffer(),
);
check("r8b", D);
say("=== R9 flipped left-right");
fresh();
put("media/journal/flip.webp", await S().flop().webp().toBuffer());
check("r9", D);
say("=== R10 a light colour shift (brightness +6%, hue +12°, saturation ×1.1)");
fresh();
put(
  "media/journal/tint.webp",
  await S()
    .modulate({ brightness: 1.06, hue: 12, saturation: 1.1 })
    .webp()
    .toBuffer(),
);
check("r10", D);
const small = await S()
  .resize(Math.round(om.width * 0.7))
  .jpeg({ quality: 70 })
  .toBuffer();
say("=== R11a CSS: a data: URI background in the main stylesheet");
fresh();
appendFileSync(
  join(D, "assets", CSS),
  `.qa-hero{background-image:url(data:image/jpeg;base64,${small.toString("base64")})}`,
);
check("r11a", D);
say(
  "=== R11b CSS: a background file under a non-image name (media/bg/hero.dat)",
);
fresh();
put("media/bg/hero.dat", small);
appendFileSync(
  join(D, "assets", CSS),
  ".qa-hero{background-image:url(/media/bg/hero.dat)}",
);
check("r11b", D);
say(
  "=== R11c CSS: image-set() hotlinked to another server of the same CDN (ae04.alicdn.com)",
);
fresh();
appendFileSync(
  join(D, "assets", CSS),
  `.qa-hero{background-image:image-set("${CARDURL.replace("ae01.", "ae04.")}" 1x)}`,
);
check("r11c", D);
say("=== R12 the original bytes under a text name (media/notes/readme.txt)");
fresh();
put("media/notes/readme.txt", readFileSync(ORIG));
check("r12", D);
say("=== R13 an SVG file framing a resized copy as a data: URI");
fresh();
put(
  "media/journal/frame.svg",
  Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800"><rect width="800" height="800" fill="#f4efe8"/><image x="40" y="40" width="720" height="720" href="data:image/jpeg;base64,${small.toString("base64")}"/></svg>`,
  ),
);
check("r13", D);
say(
  "=== R14 a hotlink to an AliExpress image host no card names (ae-pic-a1.aliexpress-media.com)",
);
fresh();
addHead(
  PAGE,
  `<meta property="og:image" content="${CARDURL.replace("ae01.alicdn.com", "ae-pic-a1.aliexpress-media.com")}">`,
);
check("r14", D);
say("=== R15 a data: URI in CSS broken by line breaks");
fresh();
appendFileSync(
  join(D, "assets", CSS),
  `.qa-hero{background-image:url("data:image/jpeg;base64,${small.toString("base64").replace(/(.{76})/g, "$1\\\n")}")}`,
);
check("r15", D);
say(
  "=== R16 a resized copy inlined in a JS chunk (as Vite inlines a small imported image)",
);
fresh();
appendFileSync(
  join(D, "assets", JS),
  `\nexport const qaThumb="data:image/webp;base64,${(await S().resize(96).webp({ quality: 60 }).toBuffer()).toString("base64")}";\n`,
);
check("r16", D);
say("=== R17 padded onto a white 4:3 canvas, as og:image (S19, ת51)");
fresh();
put(
  "media/og/look-17.jpg",
  await S()
    .resize(800)
    .flatten({ background: "#ffffff" })
    .extend({
      left: 160,
      right: 160,
      top: 0,
      bottom: 80,
      background: "#ffffff",
    })
    .jpeg({ quality: 80 })
    .toBuffer(),
);
addHead(
  PAGE,
  '<meta property="og:image" content="https://example.co.il/media/og/look-17.jpg">',
);
check("r17", D);
say("=== R18 a grey 3% border (S19, ת51)");
fresh();
put(
  "media/journal/border.webp",
  await S()
    .resize(800)
    .flatten({ background: "#ffffff" })
    .extend({ left: 24, right: 24, top: 24, bottom: 24, background: "#bbbbbb" })
    .webp()
    .toBuffer(),
);
check("r18", D);
rmSync(D, { recursive: true, force: true });
writeFileSync(
  join(DATA, "mut-rights.json"),
  JSON.stringify(
    { picture: opt.file, original: orig.file, page: PAGE, results },
    null,
    1,
  ),
);
say(
  `QA mut-rights: ${Object.entries(results)
    .map(
      ([k, v]) =>
        `${k} gate ${v.gate_exit === 1 ? "FAIL(caught)" : v.gate_exit === 0 ? "pass" : `exit ${v.gate_exit}`} / scan ${/FOUND/.test(v.qa_scan) ? "found" : "clean"}`,
    )
    .join("; ")}`,
);
if (!existsSync(join(DATA, "mut-rights.json"))) process.exit(1);

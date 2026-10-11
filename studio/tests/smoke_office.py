#!/usr/bin/env python3
"""Smoke test for the Studio's office screen (#office): the agents of the project on a floor plan (2026-10-11).

1. Python checks on studio/build.py: load_office parses status/agents.json, every agent file in .claude/agents/ and
   CLAUDE.md (frontmatter name/description/tools/model, the body, lines that state a limit), counts each agent's lines in
   the board log (last 5 kept), and redacts anything that looks like a secret.
2. Browser, the real data built offline into a temp folder (studio/dist is not touched):
   - 1280px and 390px, light and dark: one room per agent, a state in every aria-label, the legend, planned rooms marked
     "פנוי"; no horizontal scroll; axe-core finds no WCAG 2.0/2.1 A or AA violation; no JavaScript errors.
   - working rooms glow (an animated halo) and light travels along the threads of working agents; with
     prefers-reduced-motion there are no particles and the halo does not animate.
   - hover or focus on a room highlights its threads; a click opens the panel (role, state, tools, limits, board lines,
     the full instructions as markdown), Escape closes it and focus returns to the room.
   - live state: a mock db collection "agents" overrides status/agents.json; an empty collection falls back to it.
   - 390px: the plan is a mini-map out of the tab order, the wing list opens the panel, "הגדלת השרטוט" makes the plan usable.
3. With --shots: assets/qa/studio-2026-10-11/office-*.png.

Usage:  python3 studio/tests/smoke_office.py [--shots] [--keep]
Exit code 0 = all checks passed, 1 = a check failed.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smoke_products as T  # noqa: E402  (shared helpers: build, serve, axe, the mock db)

ROOT = T.ROOT
SHOTS = T.SHOTS
AGENTS = json.loads((ROOT / "status" / "agents.json").read_text(encoding="utf-8"))
AGENT_FILES = sorted((ROOT / ".claude" / "agents").glob("*.md"))
STATE_HE = {"working": "עובד עכשיו", "idle": "ממתין למשימה", "blocked": "חסום", "planned": "משרד פנוי"}
check = T.check


def python_checks():
    print("- build.py: the office")
    B = T.load_build()
    board = B.parse_board(ROOT / "status" / "board.md")
    O = B.load_office(board["log"])
    check(O is not None and len(O["agents"]) == len(AGENTS["agents"]), f"office: every agent of status/agents.json ({len(O['agents'])})")
    check(len(O["flows"]) == len(AGENTS["flows"]) and not O["warnings"], f"office: every flow ({len(O['flows'])}), no warnings {O['warnings'][:2]}")
    by_src = {a["instructions"]["src"]: a for a in O["agents"] if a["instructions"]}
    for f in AGENT_FILES:
        a = by_src.get(f.relative_to(ROOT).as_posix())
        ins = a and a["instructions"]
        check(bool(ins) and ins["name"] == f.stem and bool(ins["description"]) and len(ins["body"]) > 200,
              f"parsed {f.name}: name, description, body ({len(ins['body']) if ins else 0} chars)")
        head = f.read_text(encoding="utf-8").split("\n---", 1)[0]
        has_tools = "\ntools:" in head
        check(bool(ins) and (bool(ins["tools"]) == has_tools), f"{f.name}: tools {'listed' if has_tools else 'not limited in the file'} ({ins and ins['tools']})")
        check(bool(ins) and len(ins["limits"]) >= 1, f"{f.name}: limits found in the instructions ({ins and len(ins['limits'])})")
    ad = by_src.get("CLAUDE.md")
    check(bool(ad) and ad["id"] == "art-director" and "המנהל" in ad["instructions"]["body"] and len(ad["instructions"]["limits"]) >= 3,
          f"CLAUDE.md is the art director's instructions ({ad and len(ad['instructions']['limits'])} limits)")
    check(len(by_src) == len(AGENT_FILES) + 1, f"all {len(AGENT_FILES)} agent files and CLAUDE.md ({len(by_src)})")
    u = next(a for a in O["agents"] if a["id"] == "user")
    check(u["board"]["count"] > 10 and len(u["board"]["last"]) == 5 and u["board"]["last"][0]["date"] >= u["board"]["last"][-1]["date"],
          f"board: the user's lines counted ({u['board']['count']}), the last 5 newest first")
    txt, n = B.redact("key sk-proj-abcdefghijklmnop and e7ba6de9" + "0" * 24 + " and CJ5029507@api")
    check(n == 3 and "sk-proj" not in txt and "e7ba6de9" not in txt and "@api" not in txt, f"secrets are redacted ({n}: {txt})")
    check(O["redacted"] == 0, f"nothing secret-looking in the real instructions ({O['redacted']})")


def open_office(browser, base, width, scheme="light", seed=None, reduced="no-preference", db=True):
    ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 400 else 844}, color_scheme=scheme, locale="he-IL", reduced_motion=reduced)
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" and "Failed to load resource" not in m.text else None)
    page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
    page.add_init_script("try{localStorage.clear()}catch(e){}" + (T.MOCK_DB % json.dumps(seed or {}) if db else ""))
    page.goto(base + "#office")
    page.wait_for_selector("#screen-office:not([hidden]) #off-plan svg", timeout=15000)
    page.wait_for_timeout(250)
    return ctx, page, errors


def browser_checks(browser, base):
    n_agents = len(AGENTS["agents"])
    working = [a["id"] for a in AGENTS["agents"] if a.get("state") == "working"]
    planned = [a["id"] for a in AGENTS["agents"] if a.get("state") == "planned"]
    for width in (1280, 390):
        for scheme in ("light", "dark"):
            label = f"office {width}px {scheme}"
            print(f"- {label}")
            ctx, page, errors = open_office(browser, base, width, scheme)
            check(page.locator("#off-plan .room-btn").count() == n_agents, f"{label}: one room per agent ({page.locator('#off-plan .room-btn').count()})")
            labels = page.eval_on_selector_all("#off-plan .room-btn", "e => e.map(x => [x.dataset.state, x.getAttribute('aria-label')])")
            check(all(STATE_HE[s] in (lab or "") for s, lab in labels), f"{label}: every room's aria-label names its state")
            check(page.locator(".off-legend li").count() >= 5, f"{label}: legend for the states and the threads")
            check(all("פנוי" in page.locator(f".room-btn[data-agent='{p}'] .rb-state").inner_text() for p in planned[:3]), f"{label}: planned rooms say 'פנוי'")
            check(page.locator("#off-plan rect.room.planned").count() == len(planned), f"{label}: planned rooms have dashed walls ({len(planned)})")
            check(page.locator("#off-plan .halo.working").count() == len(working), f"{label}: a green glow around each working room ({len(working)})")
            anim = page.eval_on_selector("#off-plan .halo.working", "e => getComputedStyle(e).animationName")
            check(anim == "off-breathe", f"{label}: the glow breathes ({anim})")
            live_threads = page.locator("#off-plan .thread.live").count()
            check(live_threads >= 1 and page.locator("#off-plan .thread.live .particle").count() == 3 * live_threads,
                  f"{label}: light travels along the {live_threads} threads of working agents")
            sw = page.evaluate("document.documentElement.scrollWidth")
            check(sw <= width + 1, f"{label}: no horizontal scroll ({sw})")
            if width == 390:
                check(page.evaluate("document.getElementById('off-plan').hasAttribute('inert')"), f"{label}: the plan is a mini-map, out of the tab order")
                items = page.locator(".off-list .off-item")
                check(items.count() == n_agents and items.first.is_visible(), f"{label}: the wing list holds every office ({items.count()})")
                axe_root = "#screen-office"
                T.axe(page, label, axe_root)
                items.nth(1).click()
                page.wait_for_selector("#agentdlg[open] #ag-ins")
                check(page.evaluate("document.activeElement && document.activeElement.matches('#agentdlg [data-close]')"), f"{label}: the list opens the panel, focus on close")
                T.no_hscroll(page, width, f"{label} panel")
                page.keyboard.press("Escape")
                page.wait_for_function("() => !document.getElementById('agentdlg').open", timeout=5000)
                check(page.evaluate("document.activeElement && document.activeElement.classList.contains('off-item')"), f"{label}: focus returns to the list item")
                # a live update re-renders the office: focus stays on the same list item
                fid = page.evaluate("document.activeElement.dataset.agent")
                page.evaluate("window.claude.use('db').then(db => db.collection('agents').doc('astra').set({state: 'working', task_he: 'FIXTURE'}))")
                page.wait_for_function("() => { const b = document.querySelector(\".off-item[data-agent='astra']\"); return b && b.dataset.state === 'working'; }", timeout=5000)
                check(page.evaluate("document.activeElement && document.activeElement.classList.contains('off-item') && document.activeElement.dataset.agent") == fid,
                      f"{label}: a live update keeps focus on the list item ({fid})")
                page.click("#off-zoom")
                check(not page.evaluate("document.getElementById('off-plan').hasAttribute('inert')") and page.locator("#off-plan .room-btn").first.is_visible(),
                      f"{label}: 'הגדלת השרטוט' makes the plan usable")
                box = page.evaluate("(() => { const b = document.getElementById('off-plan-box'); return [b.scrollWidth, b.clientWidth]; })()")
                check(box[0] > box[1] and page.evaluate("document.documentElement.scrollWidth") <= width + 1, f"{label}: the zoomed plan scrolls inside its box, not the page ({box})")
                page.click("#off-zoom")
            else:
                T.axe(page, label, "#screen-office")
                # hover and focus highlight a room's threads and their labels
                rid = "master-designer"
                n_fl = sum(1 for f in AGENTS["flows"] if rid in (f["from"], f["to"]))
                page.hover(f".room-btn[data-agent='{rid}']")
                hl = page.locator("#off-plan .thread.is-hl")
                check(hl.count() == n_fl and page.eval_on_selector("#off-plan .off-labels .tl.is-hl", "e => +getComputedStyle(e).opacity") > 0.9 and page.locator("#off-plan .off-labels .tl.is-hl").count() == n_fl,
                      f"{label}: hover highlights the {n_fl} threads of {rid} with their labels")
                page.mouse.move(2, 2)
                page.focus(".room-btn[data-agent='qa-agent']")
                n_qa = sum(1 for f in AGENTS["flows"] if "qa-agent" in (f["from"], f["to"]))
                check(page.locator("#off-plan .thread.is-hl").count() == n_qa, f"{label}: focus highlights qa-agent's {n_qa} threads")
                # the panel
                page.keyboard.press("Enter")
                page.wait_for_selector("#agentdlg[open] #ag-ins")
                body = page.locator("#agent-body")
                txt = body.inner_text()
                check(page.locator("#agent-title").inner_text() == "בקרת איכות", f"{label}: Enter opens the qa-agent panel")
                check(all(w in txt for w in ("תפקיד", "כלים מותרים", "הגבלות", "ביומן הלוח", "ההוראות המלאות")), f"{label}: panel sections")
                check(body.locator(".tools code").count() >= 3 and body.locator(".limits li").count() >= 2, f"{label}: tools and limits listed")
                check(body.locator(".md-lite h4, .md-lite h5").count() >= 1 and body.locator(".md-lite li").count() >= 3, f"{label}: the instructions render as markdown (headings, lists)")
                check(body.locator(".board-lines li").count() >= 1, f"{label}: recent board lines")
                T.axe(page, f"{label} panel", "#agentdlg")
                page.keyboard.press("Escape")
                page.wait_for_function("() => !document.getElementById('agentdlg').open", timeout=5000)
                check(page.evaluate("document.activeElement && document.activeElement.dataset.agent") == "qa-agent", f"{label}: Escape closes, focus back on the room")
                # a room without an agent file: the art director reads CLAUDE.md, a planned room has none
                page.click(".room-btn[data-agent='art-director']")
                page.wait_for_selector("#agentdlg[open] #ag-ins")
                check("CLAUDE.md" in page.locator("#agent-body").inner_text(), f"{label}: the art director's instructions come from CLAUDE.md")
                page.keyboard.press("Escape")
                page.wait_for_function("() => !document.getElementById('agentdlg').open", timeout=5000)
            check(not errors, f"{label}: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
            ctx.close()

    print("- live state from the db (collection agents)")
    seed = {"agents": {"qa-agent": {"state": "working", "task_he": "FIXTURE live task", "since": "2026-10-11T19:05:00Z", "by": "smoke"},
                       "frontend-dev": {"state": "blocked", "task_he": "FIXTURE waiting for an answer"},
                       "nobody": {"state": "working"}, "astra": {"state": "dancing"}}}
    ctx, page, errors = open_office(browser, base, 1280, seed=seed)
    page.wait_for_function("() => { const b = document.querySelector(\".room-btn[data-agent='qa-agent']\"); return b && b.dataset.state === 'working'; }", timeout=5000)
    qa = page.locator(".room-btn[data-agent='qa-agent']")
    check("עובד עכשיו" in qa.get_attribute("aria-label") and "FIXTURE live task" in qa.get_attribute("aria-label"), "live: qa-agent is working, with its task")
    fd = page.locator(".room-btn[data-agent='frontend-dev']")
    check(fd.get_attribute("data-state") == "blocked" and "FIXTURE waiting" in fd.inner_text(), "live: frontend-dev is blocked, with the reason on the room")
    check(page.locator(".room-btn[data-agent='astra']").get_attribute("data-state") == next(a["state"] for a in AGENTS["agents"] if a["id"] == "astra"),
          "live: an unknown state falls back to status/agents.json")
    check(page.locator("#off-plan .thread.live[data-from='qa-agent'] .particle").count() >= 3, "live: light starts along qa-agent's threads")
    check("מצב חי" in page.locator("#off-source").inner_text(), "live: the source line says the state is live")
    qa.click()
    page.wait_for_selector("#agentdlg[open]")
    t = page.locator("#agent-body .now").inner_text()
    check("FIXTURE live task" in t and "מצב חי" in t and "smoke" in t, "live: the panel shows the task, since when and by whom")
    page.keyboard.press("Escape")
    check(not errors, "live: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
    ctx.close()
    ctx, page, errors = open_office(browser, base, 1280, seed={"agents": {}})
    states = dict(page.eval_on_selector_all(".room-btn", "e => e.map(x => [x.dataset.agent, x.dataset.state])"))
    check(all(states.get(a["id"]) == a["state"] for a in AGENTS["agents"]), "an empty collection falls back to status/agents.json")
    ctx.close()
    ctx, page, errors = open_office(browser, base, 1280, db=False)
    check(page.locator(".room-btn").count() == n_agents and not errors, "without a db (local preview) the office renders from status/agents.json")
    ctx.close()

    print("- prefers-reduced-motion")
    for scheme in ("light", "dark"):
        ctx, page, errors = open_office(browser, base, 1280, scheme, reduced="reduce")
        check(page.locator("#off-plan .particle").count() == 0 and page.get_attribute("#off-plan", "data-reduced") == "1", f"reduced motion {scheme}: no travelling light")
        anim = page.eval_on_selector("#off-plan .halo.working", "e => getComputedStyle(e).animationName")
        check(anim in ("none", ""), f"reduced motion {scheme}: the glow is static ({anim})")
        check(page.locator("#off-plan .thread.live").count() >= 1, f"reduced motion {scheme}: live threads still drawn (static)")
        check(not errors, f"reduced motion {scheme}: no JavaScript errors")
        ctx.close()


def shots(browser, base):
    print("- screenshots into " + str(SHOTS.relative_to(ROOT)))
    SHOTS.mkdir(parents=True, exist_ok=True)
    for width, scheme in ((1280, "light"), (1280, "dark"), (390, "light")):
        ctx, page, errors = open_office(browser, base, width, scheme)
        page.unroute("**/*")
        page.reload()
        page.wait_for_selector("#off-plan svg")
        page.wait_for_timeout(900)  # web fonts, the glow mid-breath
        h = page.evaluate("document.documentElement.scrollHeight")
        page.screenshot(path=str(SHOTS / f"office-{width}-{scheme}.png"), full_page=True, clip={"x": 0, "y": 0, "width": width, "height": min(h, 2400)})
        if width == 1280:
            page.hover(".room-btn[data-agent='master-designer']")
            page.wait_for_timeout(300)
            page.screenshot(path=str(SHOTS / f"office-hover-{width}-{scheme}.png"))
            page.mouse.move(2, 2)
            page.click(".room-btn[data-agent='qa-agent']")
            page.wait_for_selector("#agentdlg[open] #ag-ins")
            page.wait_for_timeout(300)
            page.screenshot(path=str(SHOTS / f"office-panel-{width}-{scheme}.png"))
            page.evaluate("document.getElementById('ag-ins').scrollIntoView({block: 'start'})")
            page.wait_for_timeout(200)
            page.screenshot(path=str(SHOTS / f"office-panel-instructions-{width}-{scheme}.png"))
        else:
            page.click("#off-zoom")
            page.wait_for_timeout(200)
            page.evaluate("document.getElementById('off-plan-box').scrollIntoView({block: 'start'})")
            page.screenshot(path=str(SHOTS / f"office-{width}-zoomed.png"))
            page.click("#off-zoom")
            page.locator(".off-list .off-item").nth(3).click()
            page.wait_for_selector("#agentdlg[open] #ag-ins")
            page.wait_for_timeout(300)
            page.screenshot(path=str(SHOTS / f"office-panel-{width}.png"))
        check(not errors, f"shots {width}px {scheme}: no JavaScript errors" + ("" if not errors else ": " + "; ".join(errors[:3])))
        ctx.close()
    for p in sorted(SHOTS.glob("office-*.png")):
        print(f"    {p.relative_to(ROOT)}")


def main() -> int:
    python_checks()
    tmp = Path(tempfile.mkdtemp(prefix="studio-office-"))
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=T.CHROMIUM if Path(T.CHROMIUM).exists() else None)
            print("- build with the real data")
            T.build(tmp / "dist", None)
            srv, base = T.serve(tmp / "dist")
            try:
                browser_checks(browser, base)
                if "--shots" in sys.argv:
                    shots(browser, base)
            finally:
                srv.shutdown()
            browser.close()
    finally:
        if "--keep" not in sys.argv:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"kept {tmp}")
    print(f"\n{'FAILED' if T.failures else 'PASSED'}: {len(T.failures)} failed checks")
    return 1 if T.failures else 0


if __name__ == "__main__":
    sys.exit(main())

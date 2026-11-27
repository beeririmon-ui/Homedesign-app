/**
 * MOCK10 (2026-11-27, briefs/site-mock10-ui-polish-2026-11-27.md; FB26), behind HD_PUBLIC=0, design C:
 *
 *  1. no play icon, ever: every video of the tour is muted, inline, without controls, with a poster (its first frame);
 *     the stylesheet hides WebKit's and Chromium's own buttons; no video is shown at the door, and none is shown
 *     before it has a frame — at the door, on the walk, in the room and on leg 1;
 *  2. a browser that refuses a play outside a gesture (an app's web view, iOS Low Power Mode — emulated per element):
 *     a scroll at the door holds the walk still on the door, with no system icon and a quiet line asking for a touch;
 *     one touch plays it. A press of "היכנסו" unlocks every video, and leg 1 then plays from "הלאה";
 *  3. the corners (a wide screen): the picture fills the screen; the caption in the lower right; the next station and
 *     the menu in the lower left, and the menu's panel rises there;
 *  4. a phone upright (400): the whole frame, and one control in the lower corner — the next station and the menu;
 *     the menu opens the rooms;
 *  5. the opening: the night from the first frame (no paper), the door fades in, the scroll cue under "היכנסו".
 */
import { test, expect, type Page } from '@playwright/test';

const atRest = (page: Page) =>
  page.waitForFunction(() => window.__hdTourState?.phase === 'room' && window.__hdTourState.busy === false && window.__hdTour?.busy === false, undefined, {
    timeout: 120_000,
  });
const noIntro = (page: Page) => page.addInitScript(() => sessionStorage.setItem('hd-intro', '1'));
const warm = (page: Page) =>
  page.waitForFunction(() => window.__hdTour?.ready === true && !document.querySelector('#tour-enter')?.getAttribute('aria-busy'), undefined, {
    timeout: 120_000,
  });
type Vid = { cls: string; controls: boolean; muted: boolean; inline: boolean; src: boolean; poster: string; ready: number; shown: boolean };
const videos = (page: Page): Promise<Vid[]> =>
  page.evaluate(() =>
    Array.from(document.querySelectorAll('video')).map((v) => {
      const cs = getComputedStyle(v);
      return {
        cls: v.className,
        controls: v.controls || v.hasAttribute('controls'),
        muted: v.muted,
        inline: v.playsInline && v.hasAttribute('playsinline'),
        src: !!v.getAttribute('src'),
        poster: v.getAttribute('poster') ?? '',
        ready: v.readyState,
        shown: cs.visibility === 'visible' && Number(cs.opacity) > 0,
      };
    }),
  );
/** the invariant of every moment: no controls, muted, inline, a poster with a source, never shown without a frame */
const clean = (vs: Vid[], where: string) => {
  for (const v of vs) {
    expect(v.controls, `${where}: ${v.cls} controls`).toBe(false);
    expect(v.muted, `${where}: ${v.cls} muted`).toBe(true);
    expect(v.inline, `${where}: ${v.cls} playsinline`).toBe(true);
    if (v.src) expect(v.poster, `${where}: ${v.cls} poster`).toMatch(/\.webp$/);
    if (v.shown) expect(v.ready >= 2 || v.poster !== '', `${where}: ${v.cls} shown without a frame`).toBe(true);
  }
};
/** every play() refused unless the element was played inside a gesture once (per element, like a web view) */
const gestureOnly = (page: Page) =>
  page.addInitScript(() => {
    let inGesture = false;
    for (const t of ['pointerdown', 'pointerup', 'touchend', 'click', 'keydown'])
      addEventListener(
        t,
        () => {
          inGesture = true;
          setTimeout(() => (inGesture = false), 0);
        },
        true,
      );
    const ok = new WeakSet<HTMLMediaElement>();
    const play = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function (this: HTMLMediaElement) {
      if (inGesture) ok.add(this);
      if (!ok.has(this)) return Promise.reject(new DOMException('blocked', 'NotAllowedError'));
      return play.call(this);
    };
  });

test.describe('MOCK10: no play icon, the corners, the opening', () => {
  test.describe.configure({ timeout: 300_000 });

  test('no video ever shows controls or a play overlay: the door, the walk, the room, leg 1', async ({ page }) => {
    await noIntro(page);
    await page.goto('/tour/');
    await warm(page);
    // the stylesheet hides the browsers' own buttons on the tour's videos
    const hidden = await page.evaluate(() => {
      const rules: string[] = [];
      const walk = (list: CSSRuleList) => {
        for (const r of Array.from(list)) {
          if (r instanceof CSSStyleRule && /display:\s*none/.test(r.cssText)) rules.push(r.selectorText);
          else if ('cssRules' in r) walk((r as CSSGroupingRule).cssRules);
        }
      };
      for (const s of Array.from(document.styleSheets)) walk(s.cssRules);
      const all = rules.join(' ');
      return ['start-playback-button', 'overlay-play-button', 'media-controls-enclosure'].every((k) => all.includes(k));
    });
    expect(hidden).toBe(true);
    const door = await videos(page);
    clean(door, 'door');
    // at the door no video is shown: the door is a picture (the walk's first frame)
    expect(door.filter((v) => v.shown)).toEqual([]);
    expect(door.find((v) => v.cls === 'tour-video')!.poster).toMatch(/tour\/arrival\/d0\.\d+\.webp$/);
    await page.locator('#tour-enter').click();
    await page.waitForFunction(() => (window.__hdTourState?.walk ?? 0) > 20, undefined, { timeout: 60_000 });
    clean(await videos(page), 'walk');
    await page.locator('#tour-skip').click();
    await atRest(page);
    clean(await videos(page), 'room');
    await page.waitForTimeout(2500);
    await page.locator('#route-next').click();
    await page.waitForFunction(() => (window.__hdTourState?.leg?.frame ?? 0) > 30, undefined, { timeout: 60_000 });
    const leg = await videos(page);
    clean(leg, 'leg 1');
    expect(leg.find((v) => v.shown && v.cls === 'tour-leg')?.poster).toMatch(/tour\/route\/leg1\.1920\.poster\.webp$/);
    await atRest(page);
    expect(await page.evaluate(() => window.__hdMedia?.refused ?? 0)).toBe(0);
  });

  test('a play refused outside a gesture: the walk holds still on the door, a touch plays it; leg 1 after a press', async ({ page }) => {
    await gestureOnly(page);
    await noIntro(page);
    await page.goto('/tour/');
    await warm(page);
    const win = (await page.locator('.tour-win').boundingBox())!;
    // a scroll is not a gesture: the walk starts, its play is refused, and it holds on its first frame
    await page.mouse.move(win.x + win.width / 2, win.y + win.height / 2);
    await page.mouse.wheel(0, 120);
    await page.waitForFunction(() => document.querySelector('.tour')?.hasAttribute('data-blocked'), undefined, { timeout: 30_000 });
    await page.waitForTimeout(1500);
    const held = await page.evaluate(() => ({ walk: window.__hdTourState?.walk ?? 0, media: window.__hdMedia }));
    expect(held.walk).toBeLessThanOrEqual(2);
    expect(held.media?.refused).toBeGreaterThanOrEqual(1);
    await expect(page.locator('.tour-tap')).toHaveCSS('opacity', '1');
    clean(await videos(page), 'held');
    // one touch on the picture: the walk plays
    await page.mouse.click(win.x + win.width * 0.3, win.y + win.height * 0.4);
    await page.waitForFunction(() => (window.__hdTourState?.walk ?? 0) > 30, undefined, { timeout: 30_000 });
    await expect(page.locator('.tour')).not.toHaveAttribute('data-blocked', '');
    await page.locator('#tour-skip').click();
    await atRest(page);
    // the press unlocked the legs too: "הלאה" plays leg 1 without a refusal
    const before = await page.evaluate(() => window.__hdMedia?.refused ?? 0);
    await page.waitForTimeout(2500);
    await page.locator('#route-next').click();
    await page.waitForFunction(() => (window.__hdTourState?.leg?.frame ?? 0) > 60, undefined, { timeout: 60_000 });
    await atRest(page);
    expect(await page.evaluate(() => window.__hdTourState?.room)).toBe('dining');
    expect(await page.evaluate(() => window.__hdMedia?.refused ?? 0)).toBe(before);
  });

  test('the corners on a wide screen: the picture fills it; the caption, the next station and the menu', async ({ page }) => {
    await noIntro(page);
    await page.goto('/tour/?skip=1');
    await atRest(page);
    const vp = page.viewportSize()!;
    const win = (await page.locator('.tour-win').boundingBox())!;
    // the picture is the hero: the whole 16:9 frame, as large as the screen allows (the bar floats over it)
    expect(win.width).toBeGreaterThan(vp.width - 2);
    expect(win.y).toBeLessThan(2);
    await expect(page.locator('.site-header')).toHaveCSS('position', 'absolute');
    await expect(page.locator('.site-header')).toHaveCSS('border-bottom-width', '0px');
    // the caption in the lower right quarter, the cluster in the lower left
    const cap = (await page.locator('.tour-top').boundingBox())!;
    expect(cap.x).toBeGreaterThan(win.x + win.width / 2);
    expect(cap.y).toBeGreaterThan(win.y + win.height / 2);
    const next = (await page.locator('#route-next').boundingBox())!;
    const fold = (await page.locator('#tour-fold').boundingBox())!;
    for (const b of [next, fold]) {
      expect(b.x + b.width).toBeLessThan(win.x + win.width / 2);
      expect(b.y).toBeGreaterThan(win.y + win.height * 0.75);
    }
    expect(fold.x).toBeLessThan(next.x);
    // no box round them: no border on the menu and the next station
    await expect(page.locator('#tour-fold')).toHaveCSS('border-top-width', '0px');
    await expect(page.locator('#route-next')).toHaveCSS('border-top-width', '0px');
    // the menu's panel rises from the corner
    await page.locator('#tour-fold').click();
    await expect(page.locator('#tour-more')).toBeVisible();
    await page.waitForTimeout(600);
    const more = (await page.locator('#tour-more').boundingBox())!;
    expect(more.x).toBeLessThan(win.x + win.width / 2);
    expect(more.y + more.height).toBeLessThan(fold.y);
    await page.keyboard.press('Escape');
  });

  test('a phone upright: the whole frame, and one control in the lower corner that opens the rooms', async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 400, height: 860 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'he-IL' });
    const page = await ctx.newPage();
    await noIntro(page);
    await page.goto('/tour/?skip=1');
    await atRest(page);
    const win = (await page.locator('.tour-win').boundingBox())!;
    expect(Math.round(win.width)).toBe(400);
    expect(Math.round(win.height)).toBe(225);
    const next = (await page.locator('#route-next').boundingBox())!;
    const fold = (await page.locator('#tour-fold').boundingBox())!;
    // within the thumb's reach: the lower 120 px, the corner
    for (const b of [next, fold]) expect(b.y + b.height).toBeGreaterThan(860 - 120);
    expect(fold.x).toBeLessThan(40);
    expect(Math.abs(next.y + next.height / 2 - (fold.y + fold.height / 2))).toBeLessThan(4);
    await expect(page.locator('.route-rail')).toBeHidden();
    await page.locator('#tour-fold').tap();
    await expect(page.locator('#tour-more')).toBeVisible();
    await expect(page.locator('#tour-more .tour-rooms button')).toHaveCount(8);
    await ctx.close();
  });

  test('the opening: the night from the first frame, the door fades in, the scroll cue after the logo', async ({ page }) => {
    await page.goto('/tour/');
    // the stage is the night at once (never the paper look first)
    const bg = await page.evaluate(() => getComputedStyle(document.querySelector('.tour')!).backgroundColor);
    expect(bg).toBe('rgb(18, 17, 15)');
    await page.waitForFunction(() => window.__hdIntro === 'done', undefined, { timeout: 30_000 });
    await expect(page.locator('.tour-door-img')).toHaveAttribute('data-loaded', '');
    await warm(page);
    await expect(page.locator('.tour-cue')).toHaveCSS('opacity', '1', { timeout: 5000 });
    await expect(page.locator('.tour-cue')).toContainText('או גללו');
  });
});

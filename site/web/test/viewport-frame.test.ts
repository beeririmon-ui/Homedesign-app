import { describe, expect, it } from 'vitest';
import { frameStyle, visibleFrame } from '../src/components/viewport-frame';

// QA S6–S7 ת7: the wheel's frame is the stage clipped to what is on the glass, never the stage's scroll coordinates
describe('the wheel frame (visual viewport)', () => {
  const layout = { width: 400, height: 860 };
  it('is the stage when the stage is wholly on screen', () => {
    expect(visibleFrame({ left: 0, top: 60, width: 400, height: 800 }, null, layout)).toEqual({ left: 0, top: 60, width: 400, height: 800 });
  });
  it('is clipped to the visual viewport: a page scrolled down, a pinch zoom', () => {
    // the page scrolled 200 px: the stage's top is under the glass's top
    expect(visibleFrame({ left: 0, top: -140, width: 400, height: 800 }, { offsetLeft: 0, offsetTop: 0, width: 400, height: 860 }, layout)).toEqual({
      left: 0,
      top: 0,
      width: 400,
      height: 660,
    });
    // pinch-zoomed ×2 into the right half
    expect(visibleFrame({ left: 0, top: 60, width: 400, height: 800 }, { offsetLeft: 200, offsetTop: 100, width: 200, height: 430 }, layout)).toEqual({
      left: 200,
      top: 100,
      width: 200,
      height: 430,
    });
  });
  it('takes the visible glass when too little of the stage shows', () => {
    // the stage scrolled 362 px sideways off the screen (the black screen of ת7)
    expect(visibleFrame({ left: 362, top: 60, width: 400, height: 800 }, { offsetLeft: 0, offsetTop: 0, width: 400, height: 860 }, layout)).toEqual({
      left: 0,
      top: 0,
      width: 400,
      height: 860,
    });
  });
  it('becomes fixed-position style in whole pixels', () => {
    expect(frameStyle({ left: 0.4, top: 59.6, width: 400, height: 800.2 })).toEqual({
      position: 'fixed',
      inset: 'auto',
      left: '0px',
      top: '60px',
      width: '400px',
      height: '800px',
    });
  });
});

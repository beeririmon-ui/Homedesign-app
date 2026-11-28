/**
 * MOCK12 (2026-11-28, briefs/site-mock12-wheels-studio-2026-11-28.md): the fixture frame of two wheels, until
 * render-agent's first real frames with several wheels land (plan wm-wheels 7.2). Numbered swatches on a plain wall,
 * said to be a demo ("הדגמה טכנית"), never a product and never a price (tools/make-fixture-wheels.ts builds it like any
 * frame, through tools/make-tour-room.ts). It opens only with `?skip=1&fixture=wheels2` in a build that is not the
 * Artifact (TourPage), as a frame of the work room, and the e2e test (e2e/mock12.spec.ts) composes its two wheels.
 */
import json from '@generated/tour.fixture-wheels2.warm-modern.json';
import { ROOMS, ROOM_HE, type RoomId, type TourData } from './data';

export const FIXTURE_FRAME = 'fixture-wheels2' as RoomId;
/** the frame joins the tour's frames (a frame of the work room), and the page may go to it */
export function registerFixtureFrame(): RoomId {
  (ROOMS as Record<string, TourData>)[FIXTURE_FRAME] = json as unknown as TourData;
  (ROOM_HE as Record<string, string>)[FIXTURE_FRAME] = 'הדגמה טכנית';
  return FIXTURE_FRAME;
}

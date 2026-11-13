/** MOCK1: the tour's engine and effects, one chunk, loaded after the door is painted (tour/TourPage.tsx) */
export { LEGACY, TourEngine } from './engine';
export { collect, doorPush, enter, leave, reveal, style, swap } from './fx';
/** MOCK2: the counters of every effect, which the tests and the evidence read (tour/metrics.ts) */
export { metrics } from './metrics';

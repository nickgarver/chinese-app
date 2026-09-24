/**
 * SM-2 variant with the three buttons the UI exposes:
 *   'again' — didn't know it. Resets the interval and requeues inside the session.
 *   'hard'  — knew it shakily. Short interval, requeued later in the session.
 *   'good'  — knew it. Graduates and moves out further each time.
 *
 * Card state is intentionally small and JSON-safe so it can sync as-is:
 *   { ease, interval, due, reps, lapses, seen }
 * `interval` is whole days, `due` is an epoch millisecond timestamp.
 *
 * If you later want better scheduling, swap this file for ts-fsrs. The rest of
 * the app only calls newCard / review / isDue / sortByPriority.
 */

const DAY = 86_400_000;
const MIN_EASE = 1.3;
const START_EASE = 2.5;

export function newCard() {
  return { ease: START_EASE, interval: 0, due: 0, reps: 0, lapses: 0, seen: 0 };
}

/**
 * Grade a card.
 *
 * `weight` scales how much the review counts. A vocab flashcard is 1. A
 * multiple-choice recognition round (clips, sentences) is RECOGNITION_WEIGHT,
 * because picking the right option from four is weaker evidence than recalling
 * the word cold, and one in four correct answers is a lucky guess.
 *
 * Everything scales through the same weight so the two stay consistent:
 *   - interval growth is ease^weight, so three third-weight reviews multiply
 *     the interval by exactly the same amount as one full review. Splitting
 *     the multiplier linearly instead would compound: 1.5^3 is 3.4, not 2.5.
 *   - the ease adjustment is scaled
 *   - reps accrues fractionally, so three recognition hits ≈ one review
 *   - a failure shrinks the interval by `weight` of the way to zero rather
 *     than wiping it, so a wrong guess can't erase a card you know
 */
export function review(card, rating, options = {}) {
  const { weight = 1, now = Date.now() } = typeof options === 'number'
    ? { now: options }        // tolerate the old review(card, rating, now) form
    : options;

  const w = Math.min(Math.max(weight, 0), 1);
  const c = { ...(card ?? newCard()) };
  c.reps = round2(c.reps + w);
  c.seen = now;

  if (rating === 'again') {
    c.lapses = round2(c.lapses + w);
    c.ease = Math.max(MIN_EASE, c.ease - 0.2 * w);
    c.interval = w >= 1 ? 0 : round2(c.interval * (1 - w));
    // only a full-weight miss goes back into the session queue
    c.due = w >= 1 ? now : now + c.interval * DAY;
    return c;
  }

  if (rating === 'hard') {
    c.ease = Math.max(MIN_EASE, c.ease - 0.15 * w);
    c.interval = c.interval <= 0 ? w : c.interval * Math.pow(1.2, w);
  } else {
    // good
    c.ease = Math.min(3.0, c.ease + 0.1 * w);
    // a first review at partial weight earns a partial day, not a whole one;
    // the test is <= 0 so a fractional interval keeps growing instead of
    // being re-floored every time
    if (c.interval <= 0) c.interval = w;
    else if (c.interval === 1 && w >= 1) c.interval = 3; // the classic second step
    else c.interval = c.interval * Math.pow(c.ease, w);
  }

  // kept fractional so partial reviews accumulate instead of rounding away:
  // at weight 1/3 a whole-day step would leave 1 * 1.36 rounding back to 1
  c.interval = round2(Math.min(c.interval, 365));
  c.due = now + c.interval * DAY;
  return c;
}

function round2(n) {
  return Math.round(n * 100) / 100;
}

/** A clip or sentence round counts for a third of a vocab card. */
export const RECOGNITION_WEIGHT = 1 / 3;

/** Card state for a word the user has declared they already know. */
export function knownCard(now = Date.now()) {
  return {
    ease: START_EASE,
    interval: 30,
    due: now + 30 * DAY,
    reps: 3,
    lapses: 0,
    seen: now
  };
}

export function isDue(card, now = Date.now()) {
  return !card || card.reps === 0 || card.due <= now;
}

/** A word counts as known once it has survived a few reviews at a real interval. */
export function isKnown(card) {
  return !!card && card.interval >= 7 && card.reps >= 3;
}

/**
 * Session ordering: overdue cards first, then brand new, then the rest.
 * Ties are broken randomly so you don't see the same run every day.
 */
export function sortByPriority(words, progress, now = Date.now()) {
  return words
    .map((w) => {
      const card = progress[w.w];
      let bucket;
      if (!card || card.reps === 0) bucket = 1; // new
      else if (card.due <= now) bucket = 0; // due
      else bucket = 2; // ahead of schedule
      return { w, bucket, due: card?.due ?? 0, r: Math.random() };
    })
    .sort((a, b) => a.bucket - b.bucket || a.due - b.due || a.r - b.r)
    .map((x) => x.w);
}

/** One label per card, used by the search filter and the word page. */
export function cardStatus(card, now = Date.now()) {
  if (!card || card.reps === 0) return 'new';
  return isKnown(card) ? 'known' : 'learning';
}

/** True only for cards already in rotation that have come round again. */
export function isOverdue(card, now = Date.now()) {
  return !!card && card.reps > 0 && card.due <= now;
}

export function summarise(progress, words) {
  let known = 0, learning = 0, due = 0;
  const now = Date.now();
  for (const v of words) {
    const card = progress[v.w];
    if (!card || card.reps === 0) continue;
    if (isKnown(card)) known++;
    else learning++;
    if (card.due <= now) due++;
  }
  const total = words.length;
  // partial credit for words in progress, since they are half-remembered
  const comprehension = total ? ((known + learning / 2) / total) * 100 : 0;
  return { known, learning, due, total, comprehension };
}

/**
 * Ten bands, one per 10% of comprehension. Purely cosmetic.
 */
const RANKS = [
  { name: 'Iron', color: '#7a7a85' },
  { name: 'Bronze', color: '#a1703f' },
  { name: 'Silver', color: '#9aa3ad' },
  { name: 'Gold', color: '#c9a227' },
  { name: 'Platinum', color: '#4fa8a8' },
  { name: 'Emerald', color: '#3f9e63' },
  { name: 'Diamond', color: '#5b8fd6' },
  { name: 'Ascendant', color: '#2f8f5b' },
  { name: 'Immortal', color: '#b33c5e' },
  { name: 'Radiant', color: '#d9a441' }
];

export function rankFor(percent) {
  const i = Math.min(RANKS.length - 1, Math.max(0, Math.floor(percent / 10)));
  return { ...RANKS[i], tier: i + 1 };
}

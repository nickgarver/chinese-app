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

export function review(card, rating, now = Date.now()) {
  const c = { ...(card ?? newCard()) };
  c.reps += 1;
  c.seen = now;

  if (rating === 'again') {
    c.lapses += 1;
    c.ease = Math.max(MIN_EASE, c.ease - 0.2);
    c.interval = 0;
    c.due = now; // straight back into the queue
    return c;
  }

  if (rating === 'hard') {
    c.ease = Math.max(MIN_EASE, c.ease - 0.15);
    c.interval = c.interval < 1 ? 1 : Math.max(1, Math.round(c.interval * 1.2));
  } else {
    // good
    c.ease = Math.min(3.0, c.ease + 0.1);
    if (c.interval < 1) c.interval = 1;
    else if (c.interval === 1) c.interval = 3;
    else c.interval = Math.round(c.interval * c.ease);
  }

  c.interval = Math.min(c.interval, 365);
  c.due = now + c.interval * DAY;
  return c;
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
  return { known, learning, due, total: words.length };
}

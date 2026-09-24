import { sortByPriority } from './srs.js';
import { sentencePool, clipPool, allClips, shuffle } from './data.js';

/**
 * Practice and Class live on separate routes, so their components unmount
 * whenever you tap another tab. Keeping both the filter selections and the
 * in-flight session here means switching away and back resumes exactly where
 * you were, mid-card and mid-tally.
 *
 * State is per scope ('hsk' | 'class') and deliberately not persisted to disk:
 * it survives navigation, not a page reload.
 */

function blankSetup(scope) {
  return {
    mode: scope === 'watch' ? 'clips' : 'vocab',
    levels: [],
    cats: [],
    classes: [],
    count: scope === 'class' ? 'all' : 10,
    front: 'zh'
  };
}

let store = $state({
  hsk: { setup: blankSetup('hsk'), run: null },
  class: { setup: blankSetup('class'), run: null },
  watch: { setup: blankSetup('watch'), run: null }
});

function startVocab(config, cards) {
  const queue = sortByPriority(config.pool, cards).slice(0, config.count);
  return {
    mode: 'vocab',
    config,
    queue,
    startedWith: queue.length,
    revealed: false,
    exampleAt: 0,
    tally: { good: 0, hard: 0, again: 0 }
  };
}

/** Distractors: same-ish length, different item, from the same pool. */
function buildRound(item, pool, key = 'zh') {
  const others = shuffle(
    pool.filter((p) => p.id !== item.id && Math.abs(p[key].length - item[key].length) <= 6)
  ).slice(0, 3);

  while (others.length < 3 && pool.length > others.length + 1) {
    const fill = pool[Math.floor(Math.random() * pool.length)];
    if (fill.id !== item.id && !others.some((o) => o.id === fill.id)) others.push(fill);
  }
  return { item, options: shuffle([item, ...others]) };
}

/**
 * Distractors for a clip. Drawn from every clip in the set rather than the
 * filtered selection, and deduped on the English text, so a narrow filter
 * doesn't recycle the same handful of wrong answers. Prefers similar-length
 * options; falls back to any other clip when there aren't enough.
 */
function buildClipRound(item, pool) {
  const seen = new Set([item.en.trim().toLowerCase()]);
  const options = [];

  const consider = (candidate) => {
    if (options.length >= 3 || candidate.id === item.id) return;
    const key = candidate.en.trim().toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    options.push(candidate);
  };

  const gap = (c) => Math.abs(c.en.length - item.en.length);
  for (const c of shuffle(pool.filter((c) => gap(c) <= 12))) consider(c);
  if (options.length < 3) for (const c of shuffle(pool)) consider(c);

  return { item, options: shuffle([item, ...options]) };
}

function startClips(config, clipData) {
  const pool = clipPool(clipData, config.pool);
  const everything = allClips(clipData);
  const chosen = shuffle(pool.slice(0, Math.max(config.count * 4, 40))).slice(0, config.count);
  return {
    mode: 'clips',
    config,
    rounds: chosen.map((c) => buildClipRound(c, everything)),
    at: 0,
    picked: null,
    score: 0,
    done: false,
    plays: 0
  };
}

function startSentences(config, data) {
  const pool = sentencePool(data, config.pool);
  const chosen = shuffle(pool.slice(0, Math.max(config.count * 4, 40))).slice(0, config.count);
  return {
    mode: 'sentences',
    config,
    rounds: chosen.map((s) => buildRound(s, pool)),
    at: 0,
    picked: null,
    score: 0,
    done: false,
    spoken: -1 // index of the round whose audio has already played
  };
}

export const session = {
  /** True while any tab has a session in flight — used to hide chrome. */
  anyRunning() {
    return Object.values(store).some((s) => s.run !== null);
  },

  setup(scope) {
    return store[scope].setup;
  },

  run(scope) {
    return store[scope].run;
  },

  start(scope, config, { cards, data, clipData }) {
    if (config.mode === 'vocab') store[scope].run = startVocab(config, cards);
    else if (config.mode === 'clips') store[scope].run = startClips(config, clipData);
    else store[scope].run = startSentences(config, data);
  },

  /** Back to the setup screen, keeping the filter selections. */
  exit(scope) {
    store[scope].run = null;
  },

  reset(scope) {
    store[scope] = { setup: blankSetup(scope), run: null };
  }
};

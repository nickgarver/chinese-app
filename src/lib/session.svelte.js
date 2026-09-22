import { sortByPriority } from './srs.js';
import { sentencePool, shuffle } from './data.js';

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
    mode: 'vocab',
    levels: [],
    cats: [],
    classes: [],
    count: scope === 'class' ? 'all' : 10,
    front: 'zh'
  };
}

let store = $state({
  hsk: { setup: blankSetup('hsk'), run: null },
  class: { setup: blankSetup('class'), run: null }
});

function startVocab(config, cards) {
  const queue = sortByPriority(config.pool, cards).slice(0, config.count);
  return {
    mode: 'vocab',
    config,
    queue,
    startedWith: queue.length,
    revealed: false,
    showExample: false,
    tally: { good: 0, hard: 0, again: 0 }
  };
}

/** Distractors: same-ish length, different sentence, from the same pool. */
function buildRound(item, pool) {
  const others = shuffle(
    pool.filter((p) => p.id !== item.id && Math.abs(p.zh.length - item.zh.length) <= 6)
  ).slice(0, 3);

  while (others.length < 3 && pool.length > others.length + 1) {
    const fill = pool[Math.floor(Math.random() * pool.length)];
    if (fill.id !== item.id && !others.some((o) => o.id === fill.id)) others.push(fill);
  }
  return { item, options: shuffle([item, ...others]) };
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
  setup(scope) {
    return store[scope].setup;
  },

  run(scope) {
    return store[scope].run;
  },

  start(scope, config, { cards, data }) {
    store[scope].run =
      config.mode === 'vocab' ? startVocab(config, cards) : startSentences(config, data);
  },

  /** Back to the setup screen, keeping the filter selections. */
  exit(scope) {
    store[scope].run = null;
  },

  reset(scope) {
    store[scope] = { setup: blankSetup(scope), run: null };
  }
};

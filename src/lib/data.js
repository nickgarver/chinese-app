import { base } from '$app/paths';

let cache = null;

/** Loads vocab + sentences + meta once, then serves from memory. */
export async function loadData() {
  if (cache) return cache;
  const [vocab, sentences, meta] = await Promise.all([
    fetch(`${base}/data/vocab.json`).then((r) => r.json()),
    fetch(`${base}/data/sentences.json`).then((r) => r.json()),
    fetch(`${base}/data/meta.json`).then((r) => r.json())
  ]);

  const byWord = new Map(vocab.map((v) => [v.w, v]));
  cache = { vocab, sentences: sentences.s, sentenceIndex: sentences.byWord, meta, byWord };
  return cache;
}

/**
 * Words matching the current selection.
 *
 * `classes` is a list of chapter refs like "1-5" (year 1, chapter 5). It is an
 * exclusive axis: when any chapter is picked, levels and categories are ignored
 * entirely. Chapters hold roughly ten words each, so intersecting them with an
 * HSK level or a topic would usually leave nothing.
 *
 * Otherwise, empty `levels` means every level and empty `cats` means every word.
 */
export function filterWords(vocab, { levels = [], cats = [], classes = [] } = {}) {
  if (classes.length) {
    return vocab.filter((v) => v.c.some((ref) => classes.includes(ref)));
  }
  return vocab.filter((v) => {
    if (levels.length && !levels.includes(v.l)) return false;
    if (cats.length && !v.t.some((t) => cats.includes(t))) return false;
    return true;
  });
}

/** Human label for a word's origin, e.g. "HSK 2 · Y1 C5" or "Class only · Y2 C11". */
export function originLabel(word) {
  const parts = [word.l ? `HSK ${word.l}` : 'Class only'];
  for (const ref of word.c) {
    const [year, chapter] = ref.split('-');
    parts.push(`Y${year} C${chapter}`);
  }
  return parts.join(' · ');
}

/**
 * Sentence records for one word, shortest first.
 * Raw rows are [zh, en, level, unknownCount, pinyin]; this hands back objects
 * so call sites read clearly.
 */
export function sentencesFor(data, word) {
  const ids = data.sentenceIndex[word] || [];
  return ids.map((i) => {
    const [zh, en, level, unknown, py] = data.sentences[i];
    return { id: i, zh, en, level, unknown, py };
  });
}

/**
 * Sentences for a whole selection, deduped, each tagged with the word it came from.
 * Sorted so lower-level and shorter sentences come first.
 */
export function sentencePool(data, words) {
  const seen = new Set();
  const pool = [];
  for (const v of words) {
    for (const id of data.sentenceIndex[v.w] || []) {
      if (seen.has(id)) continue;
      seen.add(id);
      const [zh, en, level, , py] = data.sentences[id];
      pool.push({ id, zh, en, level, py, word: v.w });
    }
  }
  pool.sort((a, b) => a.level - b.level || a.zh.length - b.zh.length);
  return pool;
}

export function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** Splits "yī fu" into syllables so pinyin can sit above characters. */
export function syllables(pinyin) {
  return pinyin.trim().split(/\s+/);
}

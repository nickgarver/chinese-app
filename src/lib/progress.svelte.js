import { browser } from '$app/environment';
import { review as gradeCard } from './srs.js';
import { currentUser, fetchProgress, saveProgress, resumeSession, pb } from './pb.js';

const LS_CARDS = 'hsk.cards';
const LS_ACCOUNT = 'hsk.account';

let cards = $state({});
let user = $state(null);
let status = $state('idle'); // idle | syncing | saved | offline | error
let loaded = $state(false);

let timer = null;

function readLocal(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeLocal(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* private mode or quota — local persistence is best-effort */
  }
}

/** Newer timestamp wins per card, so two devices merge instead of clobbering. */
function merge(a, b) {
  const out = { ...a };
  for (const [word, card] of Object.entries(b)) {
    const mine = out[word];
    if (!mine || (card.seen ?? 0) > (mine.seen ?? 0)) out[word] = card;
  }
  return out;
}

function queueSync() {
  if (!currentUser()) return;
  clearTimeout(timer);
  timer = setTimeout(async () => {
    status = 'syncing';
    try {
      await saveProgress($state.snapshot(cards));
      status = 'saved';
    } catch {
      status = 'offline';
    }
  }, 2500);
}

export const progress = {
  get cards() { return cards; },
  get user() { return user; },
  get status() { return status; },
  get loaded() { return loaded; },
  get signedIn() { return !!user; },

  /** Call once from the root layout. */
  async init() {
    if (!browser || loaded) return;
    cards = readLocal(LS_CARDS, {});

    const saved = readLocal(LS_ACCOUNT, null);
    if (saved?.username && pb && !pb.authStore.isValid) {
      try {
        await resumeSession(saved.username);
      } catch {
        /* server down or ID revoked — carry on offline */
      }
    }

    user = currentUser();
    if (user) {
      try {
        cards = merge(cards, await fetchProgress());
        writeLocal(LS_CARDS, $state.snapshot(cards));
        status = 'saved';
      } catch {
        status = 'offline';
      }
    }
    loaded = true;
  },

  rememberAccount(account) {
    writeLocal(LS_ACCOUNT, account);
    user = currentUser();
  },

  async adoptRemote() {
    try {
      cards = merge(cards, await fetchProgress());
      writeLocal(LS_CARDS, $state.snapshot(cards));
      user = currentUser();
      status = 'saved';
    } catch {
      status = 'offline';
    }
  },

  forgetAccount() {
    user = null;
    status = 'idle';
    try { localStorage.removeItem(LS_ACCOUNT); } catch { /* ignore */ }
  },

  /** Record one answer. Safe to call when signed out — it just stays local. */
  grade(word, rating) {
    const next = gradeCard(cards[word], rating);
    cards = { ...cards, [word]: next };
    writeLocal(LS_CARDS, $state.snapshot(cards));
    queueSync();
    return next;
  },

  card(word) {
    return cards[word];
  },

  reset() {
    cards = {};
    writeLocal(LS_CARDS, {});
    queueSync();
  },

  export() {
    return JSON.stringify({ version: 1, cards: $state.snapshot(cards) }, null, 2);
  },

  import(json) {
    const parsed = JSON.parse(json);
    const incoming = parsed.cards ?? parsed;
    cards = merge(cards, incoming);
    writeLocal(LS_CARDS, $state.snapshot(cards));
    queueSync();
  }
};

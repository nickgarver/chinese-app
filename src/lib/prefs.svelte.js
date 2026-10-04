import { browser } from '$app/environment';

/**
 * Small user preferences, persisted together under one key. Reads once at
 * import, so nothing needs initialising from the layout.
 *
 *   highlight         colour the practised word inside sentences
 *   hideClipChoices   keep clip options hidden until the clip has started
 */
const KEY = 'hsk.prefs';
const DEFAULTS = { highlight: true, hideClipChoices: false };

function load() {
  if (!browser) return { ...DEFAULTS };
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || '{}') };
  } catch {
    return { ...DEFAULTS };
  }
}

let state = $state(load());

export const prefs = {
  get highlight() { return state.highlight; },
  get hideClipChoices() { return state.hideClipChoices; },

  set(name, value) {
    state[name] = value;
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* ignore */ }
  }
};

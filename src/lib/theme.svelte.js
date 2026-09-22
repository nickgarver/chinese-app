import { browser } from '$app/environment';

const KEY = 'hsk.theme';

/** 'system' follows the OS; 'light' and 'dark' override it. */
let mode = $state('system');

function apply(value) {
  if (!browser) return;
  const root = document.documentElement;
  if (value === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', value);
}

export const theme = {
  get mode() { return mode; },

  init() {
    if (!browser) return;
    try {
      const saved = localStorage.getItem(KEY);
      if (saved === 'light' || saved === 'dark' || saved === 'system') mode = saved;
    } catch {
      /* private mode — fall back to following the OS */
    }
    apply(mode);
  },

  set(value) {
    mode = value;
    apply(value);
    try { localStorage.setItem(KEY, value); } catch { /* ignore */ }
  }
};

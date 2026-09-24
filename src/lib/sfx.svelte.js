import { browser } from '$app/environment';
import correctUrl from '$lib/assets/audio/correct.mp3';
import wrongUrl from '$lib/assets/audio/incorrect.mp3';

const KEY = 'hsk.sfx';

let enabled = $state(true);
let volume = $state(0.5);

/**
 * One Audio element per sound, created once and rewound before each play.
 * Making a new Audio on every answer would stutter on the first play of a
 * session while the file is fetched, and leak elements over a long run.
 */
const clips = {};

function element(name, url) {
  if (!browser) return null;
  if (!clips[name]) {
    const a = new Audio(url);
    a.preload = 'auto';
    clips[name] = a;
  }
  return clips[name];
}

export const sfx = {
  get enabled() { return enabled; },

  init() {
    if (!browser) return;
    try {
      const saved = localStorage.getItem(KEY);
      if (saved !== null) enabled = saved === 'on';
    } catch {
      /* private mode — default to on */
    }
    // warm both files so the first answer doesn't wait on the network
    element('correct', correctUrl);
    element('wrong', wrongUrl);
  },

  set(value) {
    enabled = value;
    try { localStorage.setItem(KEY, value ? 'on' : 'off'); } catch { /* ignore */ }
    if (value) this.play('correct');
  },

  toggle() {
    this.set(!enabled);
  },

  /** name is 'correct' or 'wrong'. Silently does nothing when muted. */
  play(name) {
    if (!enabled || !browser) return;
    const audio = element(name, name === 'correct' ? correctUrl : wrongUrl);
    if (!audio) return;
    try {
      audio.currentTime = 0;
      audio.volume = volume;
      // autoplay can still be refused before the first interaction; these
      // only fire from a click, but swallow the rejection either way
      audio.play()?.catch(() => {});
    } catch {
      /* nothing worth doing if the browser refuses */
    }
  }
};

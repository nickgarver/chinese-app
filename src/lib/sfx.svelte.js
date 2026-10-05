import { browser } from '$app/environment';
import correctUrl from '$lib/assets/audio/correct.mp3';
import wrongUrl from '$lib/assets/audio/incorrect.mp3';

const KEY = 'hsk.sfx';
const VOLUME = 0.5;
const URLS = { correct: correctUrl, wrong: wrongUrl };

let enabled = $state(true);

/**
 * Sound effects through the Web Audio API rather than <audio> elements.
 *
 * <audio> on iPhone is slow to start: Safari ignores preloading on iOS to save
 * data, and even once loaded there's a noticeable gap between play() and
 * sound. Web Audio decodes each file into memory once, after which playing it
 * is just starting a buffer — effectively instant, and the usual approach for
 * app and game sound effects.
 *
 * iOS keeps a new AudioContext suspended until the user touches the page, so
 * the first touch anywhere resumes it. That way the very first answer sound
 * isn't the one paying for the wake-up.
 */
let ctx = null;
let gain = null;
const buffers = {};
let loading = null;

function context() {
  if (!ctx) {
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
    gain = ctx.createGain();
    gain.gain.value = VOLUME;
    gain.connect(ctx.destination);
  }
  return ctx;
}

function load() {
  if (loading) return loading;
  const c = context();
  if (!c) return Promise.resolve();
  loading = Promise.all(
    Object.entries(URLS).map(async ([name, url]) => {
      try {
        const data = await (await fetch(url)).arrayBuffer();
        buffers[name] = await c.decodeAudioData(data);
      } catch {
        /* a sound that fails to load just stays silent */
      }
    })
  );
  return loading;
}

function unlockOnFirstTouch() {
  const resume = () => {
    if (ctx && ctx.state !== 'running') ctx.resume().catch(() => {});
  };
  window.addEventListener('pointerdown', resume, { once: true, capture: true });
  window.addEventListener('keydown', resume, { once: true, capture: true });
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
    // decoding works while the context is still suspended, so do it up front
    load();
    unlockOnFirstTouch();
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
    const c = context();
    if (!c) return;
    if (c.state !== 'running') c.resume().catch(() => {});

    const buffer = buffers[name];
    if (!buffer) {
      load(); // not decoded yet; it'll be ready next time
      return;
    }

    // a fresh source per play: they're single-use and cheap by design
    const source = c.createBufferSource();
    source.buffer = buffer;
    source.connect(gain);
    source.start();
  }
};
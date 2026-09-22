/**
 * Client-side speech via the Web Speech API.
 *
 * Known limits, kept here so they're not a surprise later:
 *  - getVoices() returns [] on the first call in Safari; you have to wait for
 *    the voiceschanged event.
 *  - Android needs the Chinese pack installed. Many devices don't have it.
 *  - Some Windows voices are network-backed, so they go silent offline.
 *  - Rates below ~0.7 sound mangled on most engines, so "slow" stops at 0.6.
 *
 * If audio quality becomes a problem, replace speak() with playback of
 * pre-generated files and keep this as the fallback.
 */

let voices = [];
let chosen = null;
let ready = false;

const supported = () =>
  typeof window !== 'undefined' && 'speechSynthesis' in window;

function pickVoice() {
  const zh = voices.filter((v) => /^zh([-_]|$)/i.test(v.lang));
  if (!zh.length) return null;
  const mainland = zh.filter((v) => /zh[-_]?(CN|Hans|SG)/i.test(v.lang));
  const pool = mainland.length ? mainland : zh;
  // a locally installed voice keeps working offline
  return pool.find((v) => v.localService) ?? pool[0];
}

export function initVoices() {
  if (!supported() || ready) return Promise.resolve(chosen);
  return new Promise((resolve) => {
    const load = () => {
      voices = window.speechSynthesis.getVoices();
      if (voices.length) {
        chosen = pickVoice();
        ready = true;
        resolve(chosen);
      }
    };
    load();
    if (!ready) {
      window.speechSynthesis.addEventListener('voiceschanged', load, { once: true });
      // some browsers never fire the event; don't hang forever
      setTimeout(() => { load(); resolve(chosen); }, 1200);
    }
  });
}

export function hasVoice() {
  return !!chosen;
}

export function voiceName() {
  return chosen ? `${chosen.name} (${chosen.lang})` : 'none found';
}

export function speak(text, { slow = false } = {}) {
  if (!supported() || !text) return false;
  const synth = window.speechSynthesis;
  synth.cancel(); // stop whatever is mid-sentence
  const u = new SpeechSynthesisUtterance(text);
  if (chosen) u.voice = chosen;
  u.lang = chosen?.lang ?? 'zh-CN';
  u.rate = slow ? 0.6 : 0.95;
  u.pitch = 1;
  synth.speak(u);
  return true;
}

export function stop() {
  if (supported()) window.speechSynthesis.cancel();
}

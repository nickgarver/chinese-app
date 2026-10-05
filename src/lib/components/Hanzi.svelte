<script>
  import { prefs } from '$lib/prefs.svelte.js';

  /**
   * Chinese text with each character's pinyin directly underneath it, and the
   * practiced word coloured (character and pinyin both) when highlighting is
   * on in settings.
   *
   *   text        the Chinese
   *   py          space-separated pinyin, one syllable per Chinese character;
   *               punctuation has no syllable
   *   word        the word to highlight, if any
   *   showPinyin  false keeps the pinyin invisible but still taking up its
   *               space, so the characters don't move when it's revealed
   *
   * If the syllables don't line up one-to-one with the characters, it falls
   * back to the text with the pinyin as a separate line underneath.
   */
  let { text, py = '', word = '', showPinyin = true } = $props();

  const HAN = /[\u4e00-\u9fff\u3400-\u4dbf]/;

  const layout = $derived.by(() => {
    const chars = [...text];
    const syllables = py.trim() ? py.trim().split(/\s+/) : [];
    const aligned = syllables.length === chars.filter((c) => HAN.test(c)).length;

    // which characters fall inside an occurrence of the practiced word
    const marked = new Array(chars.length).fill(false);
    if (word && prefs.highlight) {
      const w = [...word];
      for (let i = 0; i + w.length <= chars.length; i++) {
        if (w.every((c, k) => chars[i + k] === c)) {
          for (let k = 0; k < w.length; k++) marked[i + k] = true;
          i += w.length - 1;
        }
      }
    }

    let next = 0;
    const units = chars.map((ch, i) => ({
      ch,
      key: marked[i],
      py: aligned && HAN.test(ch) ? syllables[next++] : ''
    }));
    return { aligned, units };
  });
</script>

{#if layout.aligned && py}
  <span class="hz-line" class:hz-hidden={!showPinyin}>{#each layout.units as u}<span class="hz" class:key={u.key}><span class="hz-c">{u.ch}</span><span class="hz-p">{u.py || '\u00a0'}</span></span>{/each}</span>
{:else}
  <span>{#each layout.units as u}{#if u.key}<mark class="key">{u.ch}</mark>{:else}{u.ch}{/if}{/each}</span>
  {#if py && showPinyin}<span class="hz-fallback">{py}</span>{/if}
{/if}

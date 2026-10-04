<script>
  import { prefs } from '$lib/prefs.svelte.js';

  /**
   * Renders a Chinese line with the practised word marked wherever it occurs.
   * Plain text when highlighting is switched off in settings.
   */
  let { text, word } = $props();

  const pieces = $derived.by(() => {
    if (!word || !prefs.highlight) return [{ text, hit: false }];
    const out = [];
    let i = 0;
    while (i < text.length) {
      const at = text.indexOf(word, i);
      if (at === -1) {
        out.push({ text: text.slice(i), hit: false });
        break;
      }
      if (at > i) out.push({ text: text.slice(i, at), hit: false });
      out.push({ text: word, hit: true });
      i = at + word.length;
    }
    return out;
  });
</script>

{#each pieces as piece}{#if piece.hit}<mark class="key">{piece.text}</mark>{:else}{piece.text}{/if}{/each}

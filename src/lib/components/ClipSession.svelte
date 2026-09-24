<script>
  import { base } from '$app/paths';
  import { session } from '$lib/session.svelte.js';
  import { progress } from '$lib/progress.svelte.js';
  import { RECOGNITION_WEIGHT } from '$lib/srs.js';
  import { sfx } from '$lib/sfx.svelte.js';
  import { speak } from '$lib/tts.js';

  let { scope, onexit } = $props();

  const run = $derived(session.run(scope));
  const round = $derived(run.rounds[run.at] ?? null);

  /**
   * Plays from YouTube rather than any downloaded copy, so the channel keeps
   * the view. controls=0 hides the scrubber; cc_load_policy=0 keeps YouTube's
   * own caption track off, which would otherwise show the answer.
   *
   * plays=0 renders the poster frame with no autoplay. Tapping Play bumps the
   * counter, which remounts the iframe with autoplay=1 — and because that
   * happens inside a user gesture, the browser lets it play with sound.
   *
   * None of those parameters touch subtitles burned into the picture, which
   * are pixels rather than a caption track. The mask covers those, and lifts
   * once you have answered.
   */
  const src = $derived(
    round
      ? `https://www.youtube-nocookie.com/embed/${round.item.video}` +
        `?start=${Math.floor(round.item.start)}&end=${Math.ceil(round.item.end)}` +
        `&autoplay=${run.plays > 0 ? 1 : 0}` +
        `&controls=0&rel=0&iv_load_policy=3&disablekb=1&fs=0&playsinline=1` +
        `&modestbranding=1&cc_load_policy=0&cc_lang_pref=`
      : ''
  );

  /** Splits the line so the word being practised can be marked in place. */
  function highlight(text, word) {
    if (!word) return [{ text, hit: false }];
    const parts = [];
    let i = 0;
    while (i < text.length) {
      const at = text.indexOf(word, i);
      if (at === -1) {
        parts.push({ text: text.slice(i), hit: false });
        break;
      }
      if (at > i) parts.push({ text: text.slice(i, at), hit: false });
      parts.push({ text: word, hit: true });
      i = at + word.length;
    }
    return parts;
  }

  const pieces = $derived(round ? highlight(round.item.text, round.item.word) : []);

  /**
   * Options share a fixed row height with the video, so a long caption has to
   * shrink rather than overflow. Buckets by character count instead of
   * measuring: no layout thrash, and the thresholds are easy to retune.
   */
  function fit(text) {
    const n = text.length;
    if (n > 85) return 'fit-xs';
    if (n > 58) return 'fit-sm';
    if (n > 36) return 'fit-md';
    return '';
  }

  function play() {
    run.plays += 1;
  }

  function choose(option) {
    if (run.picked) return;
    run.picked = option;
    const right = option.id === round.item.id;
    if (right) run.score += 1;
    sfx.play(right ? 'correct' : 'wrong');
    // Only the word this round was built around, not every word in the line —
    // otherwise one clip would bump eight cards at once. Recognition counts
    // for a third of a vocab review either way.
    progress.grade(round.item.word, right ? 'good' : 'again', RECOGNITION_WEIGHT);
  }

  function next() {
    run.picked = null;
    run.plays = 0;
    if (run.at + 1 >= run.rounds.length) run.done = true;
    else run.at += 1;
  }
  import PageHeader from '$lib/components/PageHeader.svelte';
</script>

{#if !run.done && round}
  <div class="page">
    <div class="session-head">
      <div class="bar grow"><i style="width:{(run.at / run.rounds.length) * 100}%"></i></div>
      <span class="muted">{run.at + 1}/{run.rounds.length}</span>
      <button class="btn ghost sm auto" onclick={onexit}>Exit</button>
    </div>

    <!-- row 1: video beside the options, matched heights -->
    <div class="clip-row main">
      <div class="clip-media">
        {#key `${round.item.id}-${run.plays}`}
          <iframe
            {src}
            title="Clip"
            allow="accelerometer; autoplay; encrypted-media; picture-in-picture"
            allowfullscreen
          ></iframe>
        {/key}
        <div class="clip-mask" class:lifted={run.picked}></div>
      </div>

      <div class="clip-answers">
        {#if run.plays === 0}
          <p class="note center">Play the clip to see the options.</p>
        {:else}
          {#each round.options as opt}
            {@const isRight = opt.id === round.item.id}
            {@const chose = run.picked?.id === opt.id}
            <button
              class="btn choice {fit(opt.en)}"
              class:good={run.picked && isRight}
              class:bad={chose && !isRight}
              class:faded={run.picked && !isRight && !chose}
              disabled={!!run.picked}
              onclick={() => choose(opt)}
            >
              {opt.en}
            </button>
          {/each}
        {/if}
      </div>
    </div>

    <!-- row 2: transport controls, always both so nothing shifts -->
    <div class="clip-row controls">
      <button class="btn ghost" onclick={play}>
        {run.plays > 0 ? 'Replay' : '▶ Play clip'}
      </button>
      <button class="btn primary" disabled={!run.picked} onclick={next}>
        {run.at + 1 >= run.rounds.length ? 'Finish' : 'Next'}
      </button>
    </div>

    <!-- row 3: the line, plus the word it was chosen for -->
    {#if run.picked}
      <div class="clip-row reveal">
        <div class="card tint">
          <div class="example">
            <div class="body">
              <p class="zh example-zh">
                {#each pieces as piece}{#if piece.hit}<mark class="key">{piece.text}</mark>{:else}{piece.text}{/if}{/each}
              </p>
              <p class="example-py">{round.item.py}</p>
              <p class="example-en">{round.item.en}</p>
            </div>
            <button class="speak" aria-label="Hear it" onclick={() => speak(round.item.text)}>♪</button>
          </div>
        </div>

        <!-- opens the word's page; the session is kept in the store, so
             coming back to Watch resumes this same clip -->
        <a class="card tint uses" href="{base}/word/{encodeURIComponent(round.item.word)}">
          <p class="label">Uses</p>
          <p class="zh uses-word">{round.item.word}</p>
          <p class="uses-go">View word →</p>
        </a>
      </div>
    {/if}
  </div>
{:else}
  <PageHeader title="Session done" account={false} />

  <div class="page">
    <div class="card pop center">
      <div class="score">{run.score}/{run.rounds.length}</div>
      <p class="note tight">Clip rounds are not tracked.</p>
    </div>
    <button class="btn primary" onclick={onexit}>Practice again</button>
  </div>
{/if}

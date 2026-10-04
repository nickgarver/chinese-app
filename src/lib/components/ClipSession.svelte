<script>
  import { session } from '$lib/session.svelte.js';
  import { progress } from '$lib/progress.svelte.js';
  import { prefs } from '$lib/prefs.svelte.js';
  import { RECOGNITION_WEIGHT } from '$lib/srs.js';
  import { sfx } from '$lib/sfx.svelte.js';
  import { speak } from '$lib/tts.js';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import KeyText from '$lib/components/KeyText.svelte';
  import UsesBox from '$lib/components/UsesBox.svelte';

  let { scope, onexit } = $props();

  const run = $derived(session.run(scope));
  const round = $derived(run.rounds[run.at] ?? null);

  /**
   * Plays from YouTube rather than any downloaded copy, so the channel keeps
   * the view. controls=0 hides the scrubber; cc_load_policy=0 keeps YouTube's
   * own caption track off, which would otherwise show the answer.
   *
   * Two separate pieces of state:
   *   plays    bumped only by the Play/Replay button. It's part of the iframe's
   *            key, so bumping it remounts the player with autoplay on — the
   *            tap is a user gesture, so the browser lets it play with sound.
   *   started  set by the button OR by clicking the video itself. It hides the
   *            play icon and reveals the options, without remounting anything,
   *            so a video started by clicking it keeps playing.
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

  const showChoices = $derived(!prefs.hideClipChoices || run.started);

  /**
   * The video is a cross-origin iframe, so its clicks never reach this page.
   * What does reach it: clicking into an iframe moves focus there, the window
   * fires `blur`, and the iframe becomes document.activeElement. That's enough
   * to know the video was clicked. Reliable on desktop browsers; some mobile
   * browsers don't move focus on a tap, where the Play button still works.
   */
  $effect(() => {
    const onBlur = () =>
      setTimeout(() => {
        const el = document.activeElement;
        if (el?.tagName === 'IFRAME' && el.closest('.clip-media')) run.started = true;
      }, 0);
    window.addEventListener('blur', onBlur);
    return () => window.removeEventListener('blur', onBlur);
  });

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
    run.started = true;
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
    run.started = false;
    if (run.at + 1 >= run.rounds.length) run.done = true;
    else run.at += 1;
  }
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

        <!-- a cue only: pointer-events are off, so clicks go to the video -->
        {#if !run.started}
          <div class="clip-play" aria-hidden="true">
            <svg viewBox="0 0 64 64"><circle cx="32" cy="32" r="31" /><path d="M26 20 L46 32 L26 44 Z" /></svg>
          </div>
        {/if}
      </div>

      <div class="clip-answers">
        {#if !showChoices}
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
        {run.started ? 'Replay' : '▶ Play clip'}
      </button>
      <button class="btn primary" disabled={!run.picked} onclick={next}>
        {run.at + 1 >= run.rounds.length ? 'Finish' : 'Next'}
      </button>
    </div>

    <!-- row 3: the line, plus the word it was chosen for -->
    {#if run.picked}
      <div class="reveal-row">
        <div class="card tint">
          <div class="example">
            <div class="body">
              <p class="zh example-zh"><KeyText text={round.item.text} word={round.item.word} /></p>
              <p class="example-py">{round.item.py}</p>
              <p class="example-en">{round.item.en}</p>
            </div>
            <button class="speak" aria-label="Hear it" onclick={() => speak(round.item.text)}>♪</button>
          </div>
        </div>
        <UsesBox word={round.item.word} />
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

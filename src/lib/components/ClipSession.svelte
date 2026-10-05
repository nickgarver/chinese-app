<script>
  import ExitButton from '$lib/components/ExitButton.svelte';
  import { AudioLines } from '@lucide/svelte';
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
   *   started  switches the icon from play to replay and reveals the options
   *            when they're set to stay hidden until the clip has played.
   */
  const src = $derived(
    round
      ? `https://www.youtube-nocookie.com/embed/${round.item.video}` +
        `?start=${Math.floor(round.item.start)}&end=${Math.ceil(round.item.end)}` +
        `&autoplay=${run.plays > 0 ? 1 : 0}` +
        `&controls=0&rel=0&iv_load_policy=3&disablekb=1&fs=0&playsinline=1` +
        `&modestbranding=1&cc_load_policy=0&cc_lang_pref=` +
        `&enablejsapi=1&origin=${encodeURIComponent(location.origin)}`
      : ''
  );

  /**
   * Whether the clip is playing right now, which decides whether the play or
   * replay icon shows over the video.
   *
   * YouTube reports its state to the page over postMessage once the embed has
   * enablejsapi=1 and the page says it's listening. That's the same channel
   * the official iframe API uses, without loading its script. If those
   * messages never arrive, a timer based on the clip's length brings the
   * replay icon back instead, and a later hard timer always does.
   */
  let playing = $state(false);
  let heardFromPlayer = false;
  let softTimer;
  let hardTimer;

  const clipSeconds = $derived(round ? Math.max(1, round.item.end - round.item.start) : 0);

  function stopTimers() {
    clearTimeout(softTimer);
    clearTimeout(hardTimer);
  }

  function announce(frame) {
    try {
      frame.contentWindow?.postMessage(
        JSON.stringify({ event: 'listening', id: 'clip', channel: 'widget' }), '*');
    } catch {
      /* the player will still work; the timers cover the icon */
    }
  }

  $effect(() => {
    const onMessage = (e) => {
      if (!/^https:\/\/www\.youtube(-nocookie)?\.com$/.test(e.origin)) return;
      let msg;
      try { msg = typeof e.data === 'string' ? JSON.parse(e.data) : e.data; } catch { return; }
      const state = msg?.event === 'onStateChange' ? msg.info : msg?.info?.playerState;
      if (typeof state !== 'number') return;
      heardFromPlayer = true;
      if (state === 1 || state === 3) playing = true;        // playing, buffering
      else if (state === 0 || state === 2) playing = false;  // ended, paused
    };
    window.addEventListener('message', onMessage);
    return () => {
      window.removeEventListener('message', onMessage);
      stopTimers();
    };
  });

  const showChoices = $derived(!prefs.hideClipChoices || run.started);


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

  /**
   * The single way a clip plays. The button under the video and the overlay
   * on top of it both call this, so they behave identically: always from the
   * clip's start, never from the start of the whole video.
   */
  function play() {
    run.plays += 1;
    run.started = true;
    playing = true;
    heardFromPlayer = false;
    stopTimers();
    softTimer = setTimeout(() => { if (!heardFromPlayer) playing = false; },
      (clipSeconds + 2.5) * 1000);
    hardTimer = setTimeout(() => { playing = false; }, (clipSeconds + 10) * 1000);
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
    playing = false;
    stopTimers();
    if (run.at + 1 >= run.rounds.length) run.done = true;
    else run.at += 1;
  }
</script>

{#if !run.done && round}
  <div class="page">
    <div class="session-head">
      <ExitButton {onexit} />
      <div class="bar grow"><i style="width:{(run.at / run.rounds.length) * 100}%"></i></div>
      <span class="muted">{run.at + 1}/{run.rounds.length}</span>
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
            onload={(e) => announce(e.currentTarget)}
          ></iframe>
        {/key}
        <div class="clip-mask" class:lifted={run.picked}></div>

        <!--
          Permanently covers the video, so YouTube never receives a click and
          can't restart from the beginning of the full video. Clicking it does
          exactly what the button below does. The icon shows only while the
          clip isn't playing: play before the first run, replay afterwards.
        -->
        <button
          class="clip-play"
          class:idle={!playing}
          aria-label={run.started ? 'Replay clip' : 'Play clip'}
          onclick={play}
        >
          {#if !run.started}
            <svg viewBox="0 0 64 64" aria-hidden="true">
              <circle cx="32" cy="32" r="31" />
              <path class="glyph" d="M26 20 L46 32 L26 44 Z" />
            </svg>
          {:else}
            <svg viewBox="0 0 64 64" aria-hidden="true">
              <circle cx="32" cy="32" r="31" />
              <path class="ring" d="M38 21.6 A12 12 0 1 1 26 21.6" />
              <path class="glyph" d="M29.9 19.35 L27.1 25.6 L23.1 18.6 Z" />
            </svg>
          {/if}
        </button>
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
            <button class="speak" aria-label="Hear it" onclick={() => speak(round.item.text)}><AudioLines size={20} strokeWidth={2.25} aria-hidden="true" /></button>
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

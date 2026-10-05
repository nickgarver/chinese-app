<script>
  import Hanzi from '$lib/components/Hanzi.svelte';
  import ExitButton from '$lib/components/ExitButton.svelte';
  import { AudioLines } from '@lucide/svelte';
  import { session } from '$lib/session.svelte.js';
  import { progress } from '$lib/progress.svelte.js';
  import { prefs } from '$lib/prefs.svelte.js';
  import { RECOGNITION_WEIGHT } from '$lib/srs.js';
  import { sfx } from '$lib/sfx.svelte.js';
  import { speak } from '$lib/tts.js';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import UsesBox from '$lib/components/UsesBox.svelte';

  let { scope, onexit } = $props();

  const run = $derived(session.run(scope));
  const round = $derived(run.rounds[run.at] ?? null);

  /**
   * One YouTube player for the whole session, controlled by sending it
   * commands, rather than reloading it for every play.
   *
   * Reloading with autoplay worked on desktop, where a tap anywhere on the
   * page counts as permission to play with sound. iPhone only allows that if
   * the tap lands on the player itself, and the overlay was covering it, so
   * nothing could start the video. So now:
   *
   *   - Until the player has played once (`activated`), the overlay lets taps
   *     through, and the first tap goes to YouTube directly. That's what
   *     iPhone requires.
   *   - After that the overlay catches every tap, and both it and the button
   *     below seek to the clip's start and play. iPhone allows commands like
   *     that once the player has been tapped.
   *   - Each new round loads its clip into the same player, so that first-tap
   *     permission carries over for the rest of the session.
   *
   * YouTube stops at `end` on its own for the first play; replays after a
   * seek are stopped by a timer that starts when playback actually begins.
   *
   * controls=0 hides the scrubber; cc_load_policy=0 keeps YouTube's own
   * caption track off, which would otherwise show the answer.
   */
  const first = run.rounds[run.at]?.item;
  const src = first
    ? `https://www.youtube-nocookie.com/embed/${first.video}` +
      `?start=${Math.floor(first.start)}&end=${Math.ceil(first.end)}` +
      `&autoplay=0&controls=0&rel=0&iv_load_policy=3&disablekb=1&fs=0&playsinline=1` +
      `&modestbranding=1&cc_load_policy=0&cc_lang_pref=` +
      `&enablejsapi=1&origin=${encodeURIComponent(location.origin)}`
    : '';

  let frame = $state(null);
  let playing = $state(false);
  let activated = $state(false);   // the player has played at least once
  let tapHint = $state(false);     // shown if a play command didn't take

  let heardFromPlayer = false;
  let lastState = -1;
  let cuedId = first?.id;
  let softTimer, hardTimer, stopTimer, hintTimer;

  const clipSeconds = $derived(round ? Math.max(1, round.item.end - round.item.start) : 0);

  function stopTimers() {
    clearTimeout(softTimer);
    clearTimeout(hardTimer);
    clearTimeout(stopTimer);
    clearTimeout(hintTimer);
  }

  function command(func, args = []) {
    try {
      frame?.contentWindow?.postMessage(JSON.stringify({ event: 'command', func, args }), '*');
    } catch {
      /* the player may not be ready yet */
    }
  }

  function announce() {
    try {
      frame?.contentWindow?.postMessage(
        JSON.stringify({ event: 'listening', id: 'clip', channel: 'widget' }), '*');
    } catch {
      /* the timers still cover the icon */
    }
  }

  // stop a replay at the clip's end; starts when playback actually begins
  function scheduleStop() {
    clearTimeout(stopTimer);
    stopTimer = setTimeout(() => command('pauseVideo'), (clipSeconds + 0.3) * 1000);
  }

  // load each new round's clip into the same player
  $effect(() => {
    const item = round?.item;
    if (!item || item.id === cuedId) return;
    cuedId = item.id;
    playing = false;
    tapHint = false;
    lastState = -1;
    stopTimers();
    command('cueVideoById', [{
      videoId: item.video,
      startSeconds: Math.floor(item.start),
      endSeconds: Math.ceil(item.end)
    }]);
  });

  $effect(() => {
    const onMessage = (e) => {
      if (!/^https:\/\/www\.youtube(-nocookie)?\.com$/.test(e.origin)) return;
      let msg;
      try { msg = typeof e.data === 'string' ? JSON.parse(e.data) : e.data; } catch { return; }
      const state = msg?.event === 'onStateChange' ? msg.info : msg?.info?.playerState;
      if (typeof state !== 'number') return;
      heardFromPlayer = true;

      if (state === 1) {                     // playing
        if (lastState !== 1) scheduleStop();
        activated = true;
        run.started = true;
        tapHint = false;
        clearTimeout(hintTimer);
        playing = true;
      } else if (state === 3) {              // buffering
        playing = true;
      } else if (state === 0 || state === 2) {   // ended, paused
        playing = false;
        clearTimeout(stopTimer);
      }
      lastState = state;
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
    const item = round.item;
    tapHint = false;
    command('seekTo', [Math.floor(item.start), true]);
    command('playVideo');

    playing = true;
    heardFromPlayer = false;
    clearTimeout(softTimer);
    clearTimeout(hardTimer);
    softTimer = setTimeout(() => { if (!heardFromPlayer) playing = false; },
      (clipSeconds + 2.5) * 1000);
    hardTimer = setTimeout(() => { playing = false; }, (clipSeconds + 10) * 1000);

    if (activated) {
      run.started = true;
    } else {
      // Before the first play, iPhone ignores commands from outside the
      // player. If nothing starts, say to tap the video itself.
      clearTimeout(hintTimer);
      hintTimer = setTimeout(() => {
        if (!activated) {
          playing = false;
          tapHint = true;
        }
      }, 1500);
    }
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
    run.started = false;
    playing = false;
    tapHint = false;
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
        <iframe
          bind:this={frame}
          {src}
          title="Clip"
          allow="accelerometer; autoplay; encrypted-media; picture-in-picture"
          allowfullscreen
          onload={announce}
        ></iframe>
        <div class="clip-mask" class:lifted={run.picked}></div>

        <!--
          Until the player has played once, taps pass straight through to
          YouTube, because iPhone only lets a video start with sound from a tap
          on the player itself. After that it catches every tap and does
          exactly what the button below does.
        -->
        <button
          class="clip-play"
          class:idle={!playing}
          class:passthrough={!activated}
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

    {#if tapHint}
      <p class="note center">Tap the video itself to start the first clip.</p>
    {/if}

    <!-- row 3: the line, plus the word it was chosen for -->
    {#if run.picked}
      <div class="reveal-row">
        <div class="card tint">
          <div class="example">
            <div class="example-tools">
              <button class="speak" aria-label="Hear it" onclick={() => speak(round.item.text)}><AudioLines size={20} strokeWidth={2.25} aria-hidden="true" /></button>
            </div>
            <div class="body">
              <p class="zh example-zh"><Hanzi text={round.item.text} py={round.item.py} word={round.item.word} /></p>
              <p class="example-en">{round.item.en}</p>
            </div>
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

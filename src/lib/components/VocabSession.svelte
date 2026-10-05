<script>
  import { tick } from 'svelte';
  import Hanzi from '$lib/components/Hanzi.svelte';
  import ExitButton from '$lib/components/ExitButton.svelte';
  import { RefreshCw, AudioLines } from '@lucide/svelte';
  import { base } from '$app/paths';
  import { sentencesFor, originLabel } from '$lib/data.js';
  import { progress } from '$lib/progress.svelte.js';
  import { session } from '$lib/session.svelte.js';
  import { speak } from '$lib/tts.js';
  import { sfx } from '$lib/sfx.svelte.js';

  let { data, scope, onexit } = $props();

  // lives in the store, so switching tabs mid-session resumes where you left off
  const run = $derived(session.run(scope));
  const current = $derived(run.queue[0] ?? null);
  const front = $derived(run.config.front === 'zh');

  const examples = $derived(current ? sentencesFor(data, current.w) : []);
  const example = $derived(examples.length ? examples[run.exampleAt % examples.length] : null);

  /**
   * Reveal the answer and slide the word to its new spot.
   *
   * Before the reveal the word is centred on its own; after it, the word and
   * the answer are centred together, so the word ends up higher. Layout
   * changes can't be animated directly, so this measures the word before and
   * after, then plays a short slide between the two positions.
   */
  let anchor = $state(null);

  async function reveal() {
    const before = anchor?.getBoundingClientRect().top;
    run.revealed = true;
    await tick();
    const after = anchor?.getBoundingClientRect().top;
    if (before == null || after == null) return;
    const shift = before - after;
    if (Math.abs(shift) < 1) return;
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    anchor.animate(
      [{ transform: `translateY(${shift}px)` }, { transform: 'none' }],
      { duration: 200, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' }
    );
  }

  function grade(rating) {
    const word = current;
    if (!word) return;
    progress.grade(word.w, rating);
    run.tally[rating] += 1;
    sfx.play(rating === 'again' ? 'wrong' : 'correct');

    const rest = run.queue.slice(1);
    if (rating === 'again') rest.splice(Math.min(2, rest.length), 0, word);
    else if (rating === 'hard') rest.push(word);

    run.queue = rest;
    run.revealed = false;
    run.exampleAt = 0;
  }
  import PageHeader from '$lib/components/PageHeader.svelte';
</script>

{#if current}
  <div class="page">
    <div class="session-head">
      <ExitButton {onexit} />
      <div class="bar grow">
        <i style="width:{((run.startedWith - run.queue.length) / run.startedWith) * 100}%"></i>
      </div>
      <span class="muted">{run.queue.length} left</span>
    </div>

    <!-- fixed height so revealing an answer never shifts the card -->
    <p class="origin">{originLabel(current)}</p>

    <div class="card pop flash" class:revealed={run.revealed}>
      <!-- the middle row holds what's shown first, so it stays centred; the
           answer appears in the row below without pushing it -->
      <!-- Centred on its own first; once revealed, the word and the answer are
           centred together, and reveal() slides the word up into place. -->
      {#if front}
        <div class="flash-main zh flash-zh with-py">
          <span class="flash-anchor" bind:this={anchor}><Hanzi text={current.w} py={current.p} showPinyin={run.revealed} /></span>
        </div>
        {#if run.revealed}
          <div class="flash-more"><div class="flash-en">{current.d}</div></div>
        {/if}
      {:else}
        <div class="flash-main flash-prompt">
          <span class="flash-anchor" bind:this={anchor}>{current.d}</span>
        </div>
        {#if run.revealed}
          <div class="flash-more"><div class="zh flash-zh"><Hanzi text={current.w} py={current.p} /></div></div>
        {/if}
      {/if}

      {#if run.revealed || front}
        <button class="speak" aria-label="Play audio" onclick={() => speak(current.w)}><AudioLines size={20} strokeWidth={2.25} aria-hidden="true" /></button>
      {/if}

      <!-- after the reveal only, since the word page would give the answer away.
           The session is kept in the store, so coming back resumes this card. -->
      {#if run.revealed}
        <a class="flash-link" href="{base}/word/{encodeURIComponent(current.w)}">View word →</a>
      {/if}
    </div>

    {#if run.revealed && example}
      <div class="card">
        <div class="example">
          <div class="example-tools">
            <button class="speak" aria-label="Play sentence" onclick={() => speak(example.zh)}><AudioLines size={20} strokeWidth={2.25} aria-hidden="true" /></button>
            {#if examples.length > 1}
              <button
                class="speak"
                aria-label="Another sentence"
                title="{(run.exampleAt % examples.length) + 1} of {examples.length}"
                onclick={() => (run.exampleAt += 1)}
              ><RefreshCw size={18} strokeWidth={2.25} aria-hidden="true" /></button>
            {/if}
          </div>
          <div class="body">
            <p class="zh example-zh"><Hanzi text={example.zh} py={example.py} word={current.w} /></p>
            <p class="example-en">{example.en}</p>
          </div>
        </div>
      </div>
    {/if}

    {#if !run.revealed}
      <button class="btn primary" onclick={reveal}>Show answer</button>
    {:else}
      <div class="stack grade">
        <div class="row">
          <button class="btn bad" onclick={() => grade('again')}>Don't know</button>
          <button class="btn warn" onclick={() => grade('hard')}>Do again</button>
        </div>
        <button class="btn good" onclick={() => grade('good')}>Know it</button>
      </div>
    {/if}
  </div>
{:else}
  <PageHeader title="Session done" account={false} />

  <div class="page">
    <div class="card pop">
      <div class="stats">
        <div>
          <div class="stat-num sm good">{run.tally.good}</div>
          <p class="label">Knew</p>
        </div>
        <div>
          <div class="stat-num sm warn">{run.tally.hard}</div>
          <p class="label">Shaky</p>
        </div>
        <div>
          <div class="stat-num sm bad">{run.tally.again}</div>
          <p class="label">Missed</p>
        </div>
      </div>
    </div>
    {#if progress.syncEnabled && !progress.signedIn}
      <p class="muted">Saved on this device. Create an ID on the Account tab to sync it.</p>
    {/if}
    <button class="btn primary" onclick={onexit}>Practice again</button>
  </div>
{/if}

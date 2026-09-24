<script>
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
      <div class="bar grow">
        <i style="width:{((run.startedWith - run.queue.length) / run.startedWith) * 100}%"></i>
      </div>
      <span class="muted">{run.queue.length} left</span>
      <button class="btn ghost sm auto" onclick={onexit}>Exit</button>
    </div>

    <!-- fixed height so revealing an answer never shifts the card -->
    <p class="origin">{originLabel(current)}</p>

    <div class="card pop flash">
      {#if front}
        <div class="zh flash-zh">{current.w}</div>
        {#if run.revealed}
          <div class="flash-py">{current.p}</div>
          <div class="flash-en">{current.d}</div>
        {/if}
      {:else}
        <div class="flash-prompt">{current.d}</div>
        {#if run.revealed}
          <div class="zh flash-zh">{current.w}</div>
          <div class="flash-py">{current.p}</div>
        {/if}
      {/if}

      {#if run.revealed || front}
        <button class="speak" aria-label="Play audio" onclick={() => speak(current.w)}>♪</button>
      {/if}
    </div>

    {#if run.revealed && example}
      <div class="card">
        <div class="example">
          <div class="body">
            <p class="zh example-zh">{example.zh}</p>
            <p class="example-py">{example.py}</p>
            <p class="example-en">{example.en}</p>
          </div>
          <div class="example-tools">
            <button class="speak" aria-label="Play sentence" onclick={() => speak(example.zh)}>♪</button>
            {#if examples.length > 1}
              <button
                class="speak"
                aria-label="Another sentence"
                title="{(run.exampleAt % examples.length) + 1} of {examples.length}"
                onclick={() => (run.exampleAt += 1)}
              >↻</button>
            {/if}
          </div>
        </div>
      </div>
    {/if}

    {#if !run.revealed}
      <button class="btn primary" onclick={() => (run.revealed = true)}>Show answer</button>
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

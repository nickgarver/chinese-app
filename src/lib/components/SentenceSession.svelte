<script>
  import { session } from '$lib/session.svelte.js';
  import { speak } from '$lib/tts.js';

  let { scope, onexit } = $props();

  const run = $derived(session.run(scope));
  const front = $derived(run.config.front);
  const round = $derived(run.rounds[run.at] ?? null);

  // Speak each round once. Tracking the index in the store stops the audio
  // replaying every time you come back to the tab.
  $effect(() => {
    if (run.done || !round) return;
    if (front !== 'zh' || run.spoken === run.at) return;
    run.spoken = run.at;
    const text = round.item.zh;
    const timer = setTimeout(() => speak(text), 250);
    return () => clearTimeout(timer);
  });

  function choose(option) {
    if (run.picked) return;
    run.picked = option;
    if (option.id === round.item.id) run.score += 1;
  }

  function next() {
    run.picked = null;
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

    <div class="card pop">
      {#if front === 'zh'}
        <div class="inline">
          <p class="zh prompt-zh">{round.item.zh}</p>
          <button class="speak" aria-label="Play" onclick={() => speak(round.item.zh)}>♪</button>
        </div>
        <button class="btn ghost sm auto" onclick={() => speak(round.item.zh, { slow: true })}>
          Play slowly
        </button>
      {:else}
        <p class="flash-en">{round.item.en}</p>
      {/if}
      <p class="note">
        Uses <span class="zh">{round.item.word}</span>
        · {round.item.level ? `HSK ${round.item.level}` : 'Class'}
      </p>
    </div>

    <div class="stack">
      {#each round.options as opt}
        {@const isRight = opt.id === round.item.id}
        {@const chose = run.picked?.id === opt.id}
        <button
          class="btn choice"
          class:good={run.picked && isRight}
          class:bad={chose && !isRight}
          class:faded={run.picked && !isRight && !chose}
          disabled={!!run.picked}
          onclick={() => choose(opt)}
        >
          {#if front === 'zh'}{opt.en}{:else}<span class="zh choice-zh">{opt.zh}</span>{/if}
        </button>
      {/each}
    </div>

    {#if run.picked}
      <div class="card tint">
        <p class="zh example-zh">{round.item.zh}</p>
        <p class="example-py">{round.item.py}</p>
        <p class="example-en">{round.item.en}</p>
      </div>
      <button class="btn primary" onclick={next}>
        {run.at + 1 >= run.rounds.length ? 'Finish' : 'Next'}
      </button>
    {/if}
  </div>
{:else}
  <div class="page">
    <h1>Session done</h1>
    <div class="card pop center">
      <div class="score">{run.score}/{run.rounds.length}</div>
      <p class="note tight">Sentence rounds are not tracked.</p>
    </div>
    <button class="btn primary" onclick={onexit}>Practice again</button>
  </div>
{/if}

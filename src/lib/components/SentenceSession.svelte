<script>
  import ExitButton from '$lib/components/ExitButton.svelte';
  import { AudioLines, Turtle } from '@lucide/svelte';
  import { session } from '$lib/session.svelte.js';
  import { progress } from '$lib/progress.svelte.js';
  import { RECOGNITION_WEIGHT } from '$lib/srs.js';
  import { sfx } from '$lib/sfx.svelte.js';
  import { speak } from '$lib/tts.js';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import KeyText from '$lib/components/KeyText.svelte';
  import UsesBox from '$lib/components/UsesBox.svelte';

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
    const right = option.id === round.item.id;
    if (right) run.score += 1;
    sfx.play(right ? 'correct' : 'wrong');
    // Only the word this round was built around, not every word in the line —
    // otherwise one sentence would bump eight cards at once. Recognition counts
    // for a third of a vocab review either way.
    progress.grade(round.item.word, right ? 'good' : 'again', RECOGNITION_WEIGHT);
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
      <ExitButton {onexit} />
      <div class="bar grow"><i style="width:{(run.at / run.rounds.length) * 100}%"></i></div>
      <span class="muted">{run.at + 1}/{run.rounds.length}</span>
    </div>

    <div class="card pop">
      {#if front === 'zh'}
        <div class="inline prompt-row">
          <p class="zh prompt-zh"><KeyText text={round.item.zh} word={round.item.word} /></p>
          <div class="speak-stack">
            <button class="speak" aria-label="Play" onclick={() => speak(round.item.zh)}>
              <AudioLines size={20} strokeWidth={2.25} aria-hidden="true" />
            </button>
            <button class="speak" aria-label="Play slowly" title="Play slowly"
              onclick={() => speak(round.item.zh, { slow: true })}>
              <Turtle size={20} strokeWidth={2.25} aria-hidden="true" />
            </button>
          </div>
        </div>
      {:else}
        <p class="prompt-en">{round.item.en}</p>
      {/if}
      <p class="note">{round.item.level ? `HSK ${round.item.level}` : 'Class'}</p>
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
      <div class="reveal-row">
        <div class="card tint">
          <div class="example">
            <div class="body">
              <p class="zh example-zh"><KeyText text={round.item.zh} word={round.item.word} /></p>
              <p class="example-py">{round.item.py}</p>
              <p class="example-en">{round.item.en}</p>
            </div>
            <button class="speak" aria-label="Hear it" onclick={() => speak(round.item.zh)}><AudioLines size={20} strokeWidth={2.25} aria-hidden="true" /></button>
          </div>
        </div>
        <UsesBox word={round.item.word} />
      </div>
      <button class="btn primary" onclick={next}>
        {run.at + 1 >= run.rounds.length ? 'Finish' : 'Next'}
      </button>
    {/if}
  </div>
{:else}
  <PageHeader title="Session done" account={false} />

  <div class="page">
    <div class="card pop center">
      <div class="score">{run.score}/{run.rounds.length}</div>
      <p class="note tight">Sentence rounds are not tracked.</p>
    </div>
    <button class="btn primary" onclick={onexit}>Practice again</button>
  </div>
{/if}

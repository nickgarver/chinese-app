<script>
  import { base } from '$app/paths';
  import { page } from '$app/stores';
  import { loadData, sentencesFor, originLabel } from '$lib/data.js';
  import { cardStatus, isOverdue } from '$lib/srs.js';
  import { progress } from '$lib/progress.svelte.js';
  import { speak } from '$lib/tts.js';

  const ready = loadData();
  const slug = $derived(decodeURIComponent($page.params.word));

  const STATUS_LABEL = { new: 'Not started', learning: 'Learning', known: 'Known' };

  function nextReview(card) {
    if (!card || card.reps === 0) return null;
    const days = Math.round((card.due - Date.now()) / 86_400_000);
    if (days <= 0) return 'due now';
    if (days === 1) return 'tomorrow';
    return `in ${days} days`;
  }
</script>

{#await ready}
  <div class="page"><p class="muted">Loading…</p></div>
{:then data}
  {@const word = data.byWord.get(slug)}

  {#if !word}
    <div class="page">
      <a class="btn ghost sm auto" href="{base}/search">← Search</a>
      <div class="card"><p><strong>No word called “{slug}”.</strong></p></div>
    </div>
  {:else}
    {@const card = progress.cards[word.w]}
    {@const status = cardStatus(card)}
    {@const examples = sentencesFor(data, word.w)}
    {@const cats = word.t
      .map((key) => data.meta.categories.find((c) => c.key === key))
      .filter(Boolean)}

    <div class="page">
      <a class="btn ghost sm auto" href="{base}/search">← Search</a>

      <!-- word and its progress side by side -->
      <div class="word-top">
        <div class="card pop word-card">
          <div class="zh hero-zh">{word.w}</div>
          <div class="hero-py">{word.p}</div>
          <div class="hero-en">{word.d}</div>
          <button class="speak center" aria-label="Play" onclick={() => speak(word.w)}>♪</button>
        </div>

        <div class="card word-progress">
          <p class="label">Your progress</p>
          <p class="status {status}">{STATUS_LABEL[status]}</p>

          {#if card && card.reps > 0}
            <dl class="facts">
              <div><dt>Reviews</dt><dd>{Math.round(card.reps)}</dd></div>
              <div><dt>Interval</dt><dd>{card.interval}d</dd></div>
              <div><dt>Next</dt><dd>{nextReview(card)}</dd></div>
              {#if card.lapses >= 1}
                <div><dt>Lapses</dt><dd>{Math.round(card.lapses)}</dd></div>
              {/if}
            </dl>
          {:else}
            <p class="note tight">Not practised yet.</p>
          {/if}

          <div class="word-actions">
            {#if status !== 'known'}
              <button class="btn ghost sm" onclick={() => progress.markKnown(word.w)}>
                Mark known
              </button>
            {/if}
            {#if card}
              <button class="btn ghost sm" onclick={() => progress.forget(word.w)}>
                Reset
              </button>
            {/if}
          </div>
        </div>
      </div>

      <div class="card">
        <div class="meta-row">
          <div>
            <p class="label">Where it comes from</p>
            <p class="note tight">{originLabel(word)}</p>
          </div>
          <div>
            <p class="label">Categories</p>
            {#if cats.length}
              <div class="chips spaced">
                {#each cats as c}
                  <span class="chip tight">
                    {#if c.emoji}<span class="emoji">{c.emoji}</span>{/if}{c.label}
                  </span>
                {/each}
              </div>
            {:else}
              <p class="note tight">Not tagged yet.</p>
            {/if}
          </div>
        </div>
      </div>

      <div class="card">
        <p class="label">
          Example sentence{examples.length === 1 ? '' : 's'}
          {#if examples.length}· {examples.length}{/if}
        </p>

        {#if !examples.length}
          <p class="note">No sentence in the corpus uses this word on its own.</p>
        {:else}
          <div class="stack spaced">
            {#each examples as ex}
              <div class="example">
                <div class="body">
                  <p class="zh example-zh">{ex.zh}</p>
                  <p class="example-py">{ex.py}</p>
                  <p class="example-en">{ex.en}</p>
                </div>
                <button class="speak" aria-label="Play sentence" onclick={() => speak(ex.zh)}>♪</button>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}
{/await}

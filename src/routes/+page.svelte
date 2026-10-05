<script>
  import { base } from '$app/paths';
  import { goto } from '$app/navigation';
  import { loadData, filterWords, shuffle } from '$lib/data.js';
  import { summarise, rankFor, isOverdue } from '$lib/srs.js';
  import { progress } from '$lib/progress.svelte.js';
  import { session } from '$lib/session.svelte.js';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import SiteFooter from '$lib/components/SiteFooter.svelte';

  const ready = loadData();

  const MAX_DUE = 50;   // a big backlog shouldn't become one enormous session
  const RANDOM_COUNT = 15;

  /**
   * One-tap practice. Reviews whatever is due; when nothing is, runs a short
   * random set instead, as either vocab or sentences.
   *
   * The random set draws from words you've already studied, so it's review
   * rather than a surprise wall of unknown words. Before you've studied 15,
   * it falls back to HSK 1-2.
   */
  function quickStart(data) {
    const now = Date.now();
    const due = data.vocab.filter((v) => isOverdue(progress.cards[v.w], now));

    let config;
    if (due.length) {
      config = { mode: 'vocab', pool: due, count: Math.min(due.length, MAX_DUE) };
    } else {
      const studied = data.vocab.filter((v) => progress.cards[v.w]?.reps > 0);
      const source = studied.length >= RANDOM_COUNT
        ? studied
        : filterWords(data.vocab, { levels: [1, 2] });
      config = {
        mode: Math.random() < 0.5 ? 'vocab' : 'sentences',
        pool: shuffle(source).slice(0, RANDOM_COUNT),
        count: RANDOM_COUNT
      };
    }

    session.start('hsk', { levels: [], cats: [], classes: [], front: 'zh', ...config },
      { cards: progress.cards, data });
    goto(`${base}/practice`);
  }
</script>

{#await ready}
  <div class="page"><p class="muted">Loading vocabulary…</p></div>
{:then data}
  {@const stats = summarise(progress.cards, data.vocab)}
  {@const rank = rankFor(stats.comprehension)}

  {#snippet rankBadge()}
    <div class="rank" style="--rank: {rank.color}">
      <span class="rank-pct">{stats.comprehension.toFixed(1)}%</span>
      <span class="rank-name">{rank.name}</span>
    </div>
  {/snippet}

  <PageHeader title="小导 Little Tutor" end={rankBadge} />

  <div class="page">

    <div class="card pop">
      <div class="stats">
        <div>
          <div class="stat-num">{stats.known}</div>
          <p class="label">Known</p>
        </div>
        <div>
          <div class="stat-num">{stats.learning}</div>
          <p class="label">Learning</p>
        </div>
        <div>
          <div class="stat-num">{stats.due}</div>
          <p class="label">Due</p>
        </div>
      </div>
      <!-- known words out of the whole list; the bar and the count agree -->
      <div class="bar-row spaced">
        <div class="bar grow"><i style="width:{(stats.known / stats.total) * 100}%"></i></div>
        <span class="bar-count">{stats.known}/{stats.total}</span>
      </div>
    </div>

    <div class="stack">
      <button class="btn primary" onclick={() => quickStart(data)}>
        {stats.due
          ? `Review ${Math.min(stats.due, MAX_DUE)} due card${stats.due === 1 ? '' : 's'}`
          : `Quick practice: ${RANDOM_COUNT} random`}
      </button>
    </div>

    {#if progress.syncEnabled && !progress.signedIn}
      <div class="card callout">
        <p class="note top"><strong>Practicing as a guest.</strong></p>
        <p class="note top">
          Progress is saved on this device only. Create an ID to keep it across devices.
        </p>
        <a class="btn sm auto" href="{base}/account">Create an ID</a>
      </div>
    {/if}
    <SiteFooter />
  </div>

{:catch}
  <div class="page">
    <div class="card">
      <p><strong>Couldn't load the word list.</strong></p>
      <p class="note tight">Run the build script to generate <code>static/data</code>, then reload.</p>
    </div>
  </div>
{/await}

<script>
  import { base } from '$app/paths';
  import { loadData } from '$lib/data.js';
  import { summarise, rankFor } from '$lib/srs.js';
  import { progress } from '$lib/progress.svelte.js';
  import PageHeader from '$lib/components/PageHeader.svelte';

  const ready = loadData();
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

  <PageHeader title="HSK Practice" end={rankBadge} />

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
      <div class="bar spaced"><i style="width:{stats.comprehension}%"></i></div>
      <p class="note tight">
        {stats.total} words loaded, HSK 1–{data.meta.maxLevel}. Comprehension counts
        known words in full and learning words by half.
      </p>
    </div>

    <div class="stack">
      <a class="btn primary" href="{base}/practice">Practice</a>
      <a class="btn" href="{base}/class">Class vocabulary</a>
      <a class="btn" href="{base}/watch">Watch clips</a>
      <a class="btn" href="{base}/search">Browse all words</a>
    </div>

    {#if progress.syncEnabled && !progress.signedIn}
      <div class="card callout">
        <p class="note top"><strong>Practising as a guest.</strong></p>
        <p class="note top">
          Progress is saved on this device only. Create an ID to keep it across devices.
        </p>
        <a class="btn sm auto" href="{base}/account">Create an ID</a>
      </div>
    {/if}
  </div>
{:catch}
  <div class="page">
    <div class="card">
      <p><strong>Couldn't load the word list.</strong></p>
      <p class="note tight">Run the build script to generate <code>static/data</code>, then reload.</p>
    </div>
  </div>
{/await}

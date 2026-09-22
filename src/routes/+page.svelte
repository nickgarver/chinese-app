<script>
  import { base } from '$app/paths';
  import { loadData } from '$lib/data.js';
  import { summarise } from '$lib/srs.js';
  import { progress } from '$lib/progress.svelte.js';

  const ready = loadData();
</script>

<div class="page">
  <h1>HSK Practice</h1>

  {#await ready}
    <p class="muted">Loading vocabulary…</p>
  {:then data}
    {@const stats = summarise(progress.cards, data.vocab)}

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
      <div class="bar spaced"><i style="width:{(stats.known / stats.total) * 100}%"></i></div>
      <p class="note tight">{stats.total} words loaded, HSK 1–{data.meta.maxLevel}.</p>
    </div>

    <div class="stack">
      <a class="btn primary" href="{base}/practice">Practice</a>
      <a class="btn" href="{base}/class">Class vocabulary</a>
      <a class="btn" href="{base}/search">Browse all words</a>
    </div>

    {#if !progress.signedIn}
      <div class="card callout">
        <p class="note top"><strong>Practising as a guest.</strong></p>
        <p class="note top">
          Progress is saved on this device only. Create an ID to keep it across devices.
        </p>
        <a class="btn sm auto" href="{base}/account">Create an ID</a>
      </div>
    {/if}
  {:catch}
    <div class="card">
      <p><strong>Couldn't load the word list.</strong></p>
      <p class="note tight">Run the build script to generate <code>static/data</code>, then reload.</p>
    </div>
  {/await}
</div>

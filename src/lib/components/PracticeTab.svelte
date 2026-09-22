<script>
  import SessionSetup from './SessionSetup.svelte';
  import VocabSession from './VocabSession.svelte';
  import SentenceSession from './SentenceSession.svelte';
  import { loadData } from '$lib/data.js';
  import { session } from '$lib/session.svelte.js';
  import { progress } from '$lib/progress.svelte.js';
  import { onMount } from 'svelte';

  let { title, scope } = $props();

  let data = $state(null);
  let failed = $state(false);

  onMount(async () => {
    try {
      data = await loadData();
    } catch {
      failed = true;
    }
  });

  // survives navigation away and back
  const run = $derived(session.run(scope));

  function begin(config) {
    session.start(scope, config, { cards: progress.cards, data });
  }
</script>

{#if failed}
  <div class="page">
    <div class="card">
      <p><strong>Couldn't load the word list.</strong></p>
      <p class="note tight">Run the build script to generate <code>static/data</code>, then reload.</p>
    </div>
  </div>
{:else if !data}
  <div class="page"><p class="muted">Loading…</p></div>
{:else if !run}
  <SessionSetup {data} {title} {scope} onstart={begin} />
{:else if run.mode === 'vocab'}
  <VocabSession {data} {scope} onexit={() => session.exit(scope)} />
{:else}
  <SentenceSession {scope} onexit={() => session.exit(scope)} />
{/if}

<script>
  import { onMount } from 'svelte';
  import SessionSetup from '$lib/components/SessionSetup.svelte';
  import ClipSession from '$lib/components/ClipSession.svelte';
  import { loadData, loadClips } from '$lib/data.js';
  import { session } from '$lib/session.svelte.js';
  import { progress } from '$lib/progress.svelte.js';

  const scope = 'clips';

  let data = $state(null);
  let clipData = $state(undefined); // undefined = loading, null = not built
  let failed = $state(false);

  onMount(async () => {
    try {
      data = await loadData();
      clipData = await loadClips();
    } catch {
      failed = true;
    }
  });

  const run = $derived(session.run(scope));

  /** Only words that actually have a clip — otherwise the filters lie. */
  const withClips = $derived(
    data && clipData
      ? { ...data, vocab: data.vocab.filter((v) => clipData.index[v.w]?.length) }
      : null
  );

  function begin(config) {
    session.start(scope, config, { cards: progress.cards, data, clipData });
  }
</script>

{#if failed}
  <div class="page">
    <div class="card">
      <p><strong>Couldn't load the word list.</strong></p>
    </div>
  </div>
{:else if !data || clipData === undefined}
  <div class="page"><p class="muted">Loading…</p></div>
{:else if !clipData}
  <div class="page">
    <h1>Clips</h1>
    <div class="card callout">
      <p class="note top"><strong>No clips built yet.</strong></p>
      <p class="note top">
        Add channels to <code>scripts/channels.csv</code>, then run
        <code>npm run clips:fetch</code> followed by <code>npm run clips:build</code>.
      </p>
    </div>
  </div>
{:else if !withClips.vocab.length}
  <div class="page">
    <h1>Clips</h1>
    <div class="card callout">
      <p class="note top"><strong>Clips built, but none match your vocabulary.</strong></p>
      <p class="note top">Try channels that publish real Chinese subtitles.</p>
    </div>
  </div>
{:else if !run}
  <SessionSetup data={withClips} title="Clips" scope="clips" modes={['clips']} onstart={begin} />
{:else}
  <ClipSession {scope} onexit={() => session.exit(scope)} />
{/if}

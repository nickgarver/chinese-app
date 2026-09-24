<script>
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { loadData } from '$lib/data.js';
  import { cardStatus, isOverdue } from '$lib/srs.js';
  import { progress } from '$lib/progress.svelte.js';

  const FILTERS = [
    ['all', 'All'],
    ['known', 'Known'],
    ['learning', 'Learning'],
    ['due', 'Due']
  ];

  /** Below this many results, open everything — collapsing 6 rows helps nobody. */
  const AUTO_OPEN_UNDER = 60;

  let data = $state(null);
  let failed = $state(false);
  let filter = $state('all');
  let query = $state('');
  let opened = $state({}); // level -> bool, only consulted when not auto-opening

  onMount(async () => {
    try {
      data = await loadData();
    } catch {
      failed = true;
    }
  });

  /** "yī fu" -> "yi fu", so pinyin sorts and searches without tone marks. */
  function plain(text) {
    return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  let indexCache = null;

  /**
   * Built once per dataset, not per keystroke — normalize() over 2,500 words
   * on every character would be noticeable on a phone.
   * `tight` is the pinyin with spaces removed so "yifu" finds "yī fu".
   */
  function buildIndex(vocab) {
    if (indexCache?.src === vocab) return indexCache.entries;
    const entries = vocab.map((word) => {
      const py = plain(word.p);
      return { word, py, tight: py.replace(/\s+/g, ''), en: word.d.toLowerCase() };
    });
    indexCache = { src: vocab, entries };
    return entries;
  }

  function passes(entry, card, needle, tightNeedle) {
    if (filter === 'known' && cardStatus(card) !== 'known') return false;
    if (filter === 'learning' && cardStatus(card) !== 'learning') return false;
    if (filter === 'due' && !isOverdue(card)) return false;
    if (!needle) return true;
    return (
      entry.word.w.includes(needle) ||
      entry.py.includes(needle) ||
      entry.tight.includes(tightNeedle) ||
      entry.en.includes(needle)
    );
  }

  const groups = $derived.by(() => {
    if (!data) return [];
    const needle = plain(query.trim());
    const tightNeedle = needle.replace(/\s+/g, '');
    const buckets = new Map();

    for (const entry of buildIndex(data.vocab)) {
      if (!passes(entry, progress.cards[entry.word.w], needle, tightNeedle)) continue;
      const key = entry.word.l || 0;
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(entry);
    }

    return [...buckets.entries()]
      .sort((a, b) => (a[0] || 99) - (b[0] || 99)) // class-only last
      .map(([level, entries]) => {
        const words = entries
          .sort((a, b) => a.py.localeCompare(b.py))
          .map((e) => e.word);
        return {
          level,
          label: level ? `HSK ${level}` : 'Class only',
          words,
          known: words.filter((w) => cardStatus(progress.cards[w.w]) === 'known').length
        };
      });
  });

  const total = $derived(groups.reduce((n, g) => n + g.words.length, 0));

  // A search or a narrow filter should show its results without extra taps.
  const autoOpen = $derived(query.trim().length > 0 || (total > 0 && total <= AUTO_OPEN_UNDER));

  const isOpen = (level) => autoOpen || !!opened[level];
  const allOpen = $derived(groups.length > 0 && groups.every((g) => isOpen(g.level)));

  function toggle(level) {
    opened = { ...opened, [level]: !isOpen(level) };
  }

  function toggleAll() {
    const next = {};
    if (!allOpen) for (const g of groups) next[g.level] = true;
    opened = next;
  }
  import PageHeader from '$lib/components/PageHeader.svelte';
</script>

<PageHeader title="Search" />

<div class="page">

  <input
    class="field"
    type="search"
    placeholder="Chinese, pinyin or English"
    bind:value={query}
    autocapitalize="none"
    autocorrect="off"
  />

  <div class="chips">
    {#each FILTERS as [key, label]}
      <button class="chip" class:on={filter === key} onclick={() => (filter = key)}>
        {label}
      </button>
    {/each}
  </div>

  {#if failed}
    <div class="card">
      <p><strong>Couldn't load the word list.</strong></p>
      <p class="note tight">
        Run the build script to generate <code>static/data</code>, then reload.
      </p>
    </div>
  {:else if !data}
    <p class="muted">Loading…</p>
  {:else}
    <div class="between">
      <span class="muted">{total} word{total === 1 ? '' : 's'}</span>
      {#if groups.length > 1 && !autoOpen}
        <button class="btn ghost sm auto" onclick={toggleAll}>
          {allOpen ? 'Collapse all' : 'Expand all'}
        </button>
      {/if}
    </div>

    {#each groups as g (g.level)}
      {@const open = isOpen(g.level)}
      <section>
        <button class="drawer" onclick={() => toggle(g.level)} aria-expanded={open}>
          <span class="chev" class:open>›</span>
          <span class="name">{g.label}</span>
          <span class="bar"><i style="width:{(g.known / g.words.length) * 100}%"></i></span>
          <span class="muted tally">{g.known}/{g.words.length}</span>
        </button>

        {#if open}
          <div class="card flush list">
            {#each g.words as word (word.w)}
              {@const status = cardStatus(progress.cards[word.w])}
              <a class="row-item" href="{base}/word/{encodeURIComponent(word.w)}">
                <span class="dot {status}" class:due={isOverdue(progress.cards[word.w])}></span>
                <span class="zh word">{word.w}</span>
                <span class="meta">
                  <span class="py">{word.p}</span>
                  <span class="muted en">{word.d}</span>
                </span>
              </a>
            {/each}
          </div>
        {/if}
      </section>
    {/each}

    {#if !total}
      <div class="card">
        <p><strong>Nothing matches.</strong></p>
        <p class="note tight">
          {filter === 'all' ? 'Try a different search.' : 'Try the All filter.'}
        </p>
      </div>
    {/if}
  {/if}
</div>

<script>
  import { filterWords } from '$lib/data.js';
  import { session } from '$lib/session.svelte.js';

  /**
   * scope: 'hsk'   -> HSK level + category filters
   *        'class' -> year + chapter filters
   */
  let { data, title, scope = 'hsk', onstart } = $props();

  const COUNTS = [5, 10, 20, 25, 50, 100];

  // selections live in the store so they survive a tab switch
  const s = $derived(session.setup(scope));

  const classPool = $derived(data.vocab.filter((v) => v.c.length > 0));

  const pool = $derived(
    scope === 'class'
      ? (s.classes.length ? filterWords(data.vocab, { classes: s.classes }) : classPool)
      : filterWords(data.vocab, { levels: s.levels, cats: s.cats })
  );

  const available = $derived(pool.length);
  const effective = $derived(s.count === 'all' ? available : Math.min(s.count, available));

  const frontLabels = $derived(
    s.mode === 'vocab'
      ? { zh: 'Chinese first', en: 'English first' }
      : { zh: 'Hear Chinese, pick English', en: 'Read English, pick Chinese' }
  );

  function toggle(list, value) {
    return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
  }

  function pickYear(year) {
    const refs = data.meta.class.find((y) => y.year === year).chapters.map((c) => c.ref);
    s.classes = refs.every((r) => s.classes.includes(r))
      ? s.classes.filter((r) => !refs.includes(r))
      : [...new Set([...s.classes, ...refs])];
  }

  function start() {
    if (!available) return;
    onstart({ ...$state.snapshot(s), count: effective, pool });
  }
</script>

<div class="page">
  <h1>{title}</h1>

  <div class="card">
    <p class="label">Practice</p>
    <div class="chips spaced">
      <button class="chip" class:on={s.mode === 'vocab'} onclick={() => (s.mode = 'vocab')}>
        <span class="emoji">🀄</span>Vocabulary
      </button>
      <button class="chip" class:on={s.mode === 'sentences'} onclick={() => (s.mode = 'sentences')}>
        <span class="emoji">💬</span>Sentences
      </button>
    </div>
  </div>

  {#if scope === 'class'}
    <div class="card">
      <div class="between">
        <p class="label">Chapters</p>
        {#if s.classes.length}
          <button class="btn ghost sm auto" onclick={() => (s.classes = [])}>Clear</button>
        {/if}
      </div>

      {#each data.meta.class as year}
        <div class="spaced">
          <button
            class="chip"
            class:on={year.chapters.every((c) => s.classes.includes(c.ref))}
            onclick={() => pickYear(year.year)}
          >Year {year.year} · all {year.count}</button>

          <div class="chips spaced">
            {#each year.chapters as c}
              <button
                class="chip tight"
                class:on={s.classes.includes(c.ref)}
                onclick={() => (s.classes = toggle(s.classes, c.ref))}
                title="{c.count} words"
              >Ch {c.chapter}</button>
            {/each}
          </div>
        </div>
      {/each}

      {#if !s.classes.length}
        <p class="note">Nothing picked — all {classPool.length} class words are in play.</p>
      {/if}
    </div>
  {:else}
    <div class="card stack">
      <div>
        <p class="label">HSK level</p>
        <div class="chips spaced">
          {#each Array(data.meta.maxLevel) as _, i}
            {@const lv = i + 1}
            <button class="chip" class:on={s.levels.includes(lv)}
              onclick={() => (s.levels = toggle(s.levels, lv))}>HSK {lv}</button>
          {/each}
        </div>
      </div>

      <div>
        <p class="label">Category</p>
        <div class="chips spaced">
          {#each data.meta.categories as c}
            <button class="chip" class:on={s.cats.includes(c.key)}
              onclick={() => (s.cats = toggle(s.cats, c.key))}>
              {#if c.emoji}<span class="emoji">{c.emoji}</span>{/if}{c.label}
            </button>
          {/each}
        </div>
      </div>

      {#if !s.levels.length && !s.cats.length}
        <p class="note top">Nothing picked — all {data.meta.wordCount} words are in play.</p>
      {/if}
    </div>
  {/if}

  <div class="card">
    <p class="label">How many</p>
    <div class="chips spaced">
      {#each COUNTS as n}
        <button class="chip" class:on={s.count === n} disabled={n > available}
          onclick={() => (s.count = n)}>{n}</button>
      {/each}
      <button class="chip" class:on={s.count === 'all'} onclick={() => (s.count = 'all')}>
        All{available ? ` (${available})` : ''}
      </button>
    </div>
    <p class="note">{available} word{available === 1 ? '' : 's'} match.</p>
  </div>

  <div class="card">
    <p class="label">Show first</p>
    <div class="chips spaced">
      <button class="chip" class:on={s.front === 'zh'} onclick={() => (s.front = 'zh')}>
        {frontLabels.zh}
      </button>
      <button class="chip" class:on={s.front === 'en'} onclick={() => (s.front = 'en')}>
        {frontLabels.en}
      </button>
    </div>
  </div>

  <button class="btn primary" disabled={!available} onclick={start}>
    {available ? `Start ${effective} ${s.mode === 'vocab' ? 'cards' : 'sentences'}` : 'Nothing matches'}
  </button>
</div>

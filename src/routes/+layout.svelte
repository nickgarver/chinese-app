<script>
  import '../app.css';
  // Imported rather than referenced from static/: Vite fingerprints the file,
  // so a changed icon can't be served from cache, the URL carries the base
  // path automatically, and a wrong path is a build error not a silent 404.
  import favicon from '$lib/assets/favicon.ico';
  import { page } from '$app/stores';
  import { base } from '$app/paths';
  import { progress } from '$lib/progress.svelte.js';
  import { theme } from '$lib/theme.svelte.js';
  import { sfx } from '$lib/sfx.svelte.js';
  import { initVoices } from '$lib/tts.js';
  import { onMount } from 'svelte';

  let { children } = $props();

  onMount(() => {
    theme.init();
    sfx.init();
    progress.init();
    initVoices();
  });

  const tabs = [
    { href: '/', icon: '家', label: 'Home' },
    { href: '/practice', icon: '练', label: 'Practice' },
    { href: '/class', icon: '课', label: 'Class' },
    { href: '/watch', icon: '影', label: 'Watch' },
    { href: '/search', icon: '查', label: 'Search' }
  ];

  const path = $derived($page.url.pathname.replace(base, '') || '/');
  // /word/... is reached from Search, so keep that tab lit
  const active = $derived(path.startsWith('/word') ? '/search' : path);

</script>

<svelte:head>
  <link rel="icon" href={favicon} sizes="32x32" />
</svelte:head>

<div class="app">
  {@render children()}
</div>

<nav class="tabs">
  {#each tabs as t}
    <a href="{base}{t.href}" class:on={active === t.href}>
      <span class="ico zh">{t.icon}</span>
      <span>{t.label}</span>
    </a>
  {/each}
</nav>

<script>
  import '../app.css';
  import { page } from '$app/stores';
  import { base } from '$app/paths';
  import { progress } from '$lib/progress.svelte.js';
  import { theme } from '$lib/theme.svelte.js';
  import { initVoices } from '$lib/tts.js';
  import { onMount } from 'svelte';

  let { children } = $props();

  onMount(() => {
    theme.init();
    progress.init();
    initVoices();
  });

  const tabs = [
    { href: '/', icon: '家', label: 'Home' },
    { href: '/practice', icon: '练', label: 'Practice' },
    { href: '/class', icon: '课', label: 'Class' },
    { href: '/search', icon: '查', label: 'Search' },
    { href: '/account', icon: '我', label: 'Account' }
  ];

  const path = $derived($page.url.pathname.replace(base, '') || '/');
  // /word/... is reached from Search, so keep that tab lit
  const active = $derived(path.startsWith('/word') ? '/search' : path);
</script>

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

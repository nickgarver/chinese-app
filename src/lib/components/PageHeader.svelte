<script>
  import { base } from '$app/paths';

  /**
   * The bar above every page. Sits outside `.page` so it spans the full
   * width while its contents line up with the column below, and so every
   * page gets identical heading height and spacing.
   *
   *   title    heading text
   *   end      optional snippet rendered before the avatar (home puts the
   *            comprehension badge there)
   *   account  set false during a session, where it would only be in the way
   */
  let { title, end = undefined, account = true } = $props();
</script>

<header class="topbar">
  <div class="topbar-inner">
    <h1>{title}</h1>
    {#if end || account}
      <div class="topbar-end">
        {#if end}{@render end()}{/if}
        {#if account}
          <a class="profile" href="{base}/account" aria-label="Account">
            <span class="zh">我</span>
          </a>
        {/if}
      </div>
    {/if}
  </div>
</header>

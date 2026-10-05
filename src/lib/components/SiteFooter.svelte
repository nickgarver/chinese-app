<script>
  import { base } from '$app/paths';
  import { Heart, Info, Presentation, CircleX } from '@lucide/svelte';

  /**
   * Footer for the home tab: one muted line, credit on the left, icons on the
   * right. Sits at the bottom of the page even when the content is short.
   *
   * Fill in DONATE_URL to make the heart a link. While it's empty the icon
   * still shows but isn't clickable.
   */
  const DONATE_URL = 'https://buy.stripe.com/28E6oG6653y78bgdj95kk00';
  const INSTAGRAM_URL = 'https://www.instagram.com/internetboy/';

  /**
   * Blank white screen covering the whole browser window. Uses the browser's
   * own <dialog>, so Escape closes it and focus stays on it while it's open.
   */
  let blank;
</script>

<footer class="site-footer">
  <p class="footer-credit">
    Made by <a href={INSTAGRAM_URL} target="_blank" rel="noopener">internetboy</a>
  </p>

  <div class="footer-icons">
    <button
      class="footer-icon"
      type="button"
      aria-label="Blank white screen"
      title="Blank white screen"
      onclick={() => blank.showModal()}
    >
      <Presentation size={17} strokeWidth={1.75} aria-hidden="true" />
    </button>

    <a
      class="footer-icon"
      href={DONATE_URL || undefined}
      target={DONATE_URL ? '_blank' : undefined}
      rel="noopener"
      aria-label="Donate"
      title="Donate"
    >
      <Heart size={17} strokeWidth={1.75} aria-hidden="true" />
    </a>

    <a class="footer-icon" href="{base}/about" aria-label="About" title="About">
      <Info size={17} strokeWidth={1.75} aria-hidden="true" />
    </a>
  </div>
</footer>

<dialog class="blank-screen" bind:this={blank} aria-label="Blank white screen">
  <button class="blank-close" type="button" aria-label="Close" onclick={() => blank.close()}>
    <CircleX size={32} strokeWidth={1.75} aria-hidden="true" />
  </button>
</dialog>

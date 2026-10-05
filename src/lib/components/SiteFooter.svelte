<script>
  import { base } from '$app/paths';
  import { Heart, Info } from '@lucide/svelte';

  /**
   * Footer for the home tab: one muted line, credit on the left, icons on the
   * right. Sits at the bottom of the page even when the content is short.
   *
   * Fill in DONATE_URL to make the heart a link. While it's empty the icon
   * still shows but isn't clickable.
   */
  const DONATE_URL = 'https://buy.stripe.com/28E6oG6653y78bgdj95kk00';
  const INSTAGRAM_URL = 'https://www.instagram.com/internetboy/';
</script>

<footer class="site-footer">
  <p class="footer-credit">
    Made by <a href={INSTAGRAM_URL} target="_blank" rel="noopener">internetboy</a>
  </p>

  <div class="footer-icons">
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

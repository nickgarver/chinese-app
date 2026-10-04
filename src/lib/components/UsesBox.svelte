<script>
  import { base } from '$app/paths';

  /**
   * The word a round was built around, linking to its page. The session lives
   * in the store, so following the link and coming back resumes the round.
   */
  let { word } = $props();
</script>

<a class="card tint uses" href="{base}/word/{encodeURIComponent(word)}">
  <p class="label">Uses</p>
  <p class="zh uses-word">{word}</p>
  <p class="uses-go">View word →</p>
</a>

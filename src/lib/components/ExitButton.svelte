<script>
  import { ChevronLeft } from '@lucide/svelte';

  /**
   * The session Exit button, with a confirmation step so a stray tap doesn't
   * end the session.
   *
   * Uses the browser's own <dialog>: Escape cancels, focus stays inside it
   * while it's open, and it renders above everything else on the page.
   * Clicking the dimmed backdrop also cancels.
   */
  let { onexit } = $props();

  let dialog;

  function ask() {
    dialog.showModal();
  }

  function stay() {
    dialog.close();
  }

  function leave() {
    dialog.close();
    onexit();
  }

  // the backdrop belongs to the dialog element itself, so a click whose
  // target is the dialog (not anything inside it) landed on the backdrop
  function onBackdrop(event) {
    if (event.target === dialog) stay();
  }
</script>

<button class="btn ghost sm auto with-icon exit" onclick={ask}>
  <ChevronLeft size={18} strokeWidth={2.5} aria-hidden="true" />Exit
</button>

<dialog class="confirm" bind:this={dialog} onclick={onBackdrop} aria-labelledby="exit-title">
  <div class="confirm-body">
    <h2 id="exit-title">End this session?</h2>
    <p class="note tight">Answers you've already given are saved.</p>
    <div class="confirm-actions">
      <button class="btn" onclick={leave}>End session</button>
      <button class="btn primary" onclick={stay}>Keep going</button>
    </div>
  </div>
</dialog>

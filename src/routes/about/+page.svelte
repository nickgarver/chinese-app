<script>
  import PageHeader from '$lib/components/PageHeader.svelte';
</script>

<PageHeader title="About" />

<div class="page prose">
  <div class="card">
    <h2>Score</h2>
    <p>
      Each flashcard answer schedules the word's next review. <strong>Know it</strong>
      brings it back in a day, then three days, then progressively longer gaps.
      <strong>Don't know</strong> brings it back a few cards later in the same session.
      <strong>Do again</strong> repeats it at the end of the session and grows the gap
      only slightly.
    </p>
    <p>
      A word is <strong>known</strong> once you've reviewed it at least three times and its
      next review is a week or more away. Anything you've started but not reached
      that point is <strong>learning</strong>. A word is <strong>due</strong> when its review
      date has arrived. Missing a known word sends it back to learning.
    </p>
    <p>
      Sentence and clip answers count too, at a third of a flashcard review, since
      picking from four options is easier than recalling a word cold. Only the word
      shown under "Uses" is affected, and a wrong pick shortens that word's gap
      rather than resetting it.
    </p>
    <p>
      The percentage on the home screen counts known words in full and learning
      words at half, out of every word in the app. Each 10% earns a new rank, from
      Iron through Bronze, Silver, Gold, Platinum, Emerald, Diamond, Ascendant and
      Immortal, up to Radiant.
    </p>
  </div>

  <div class="card">
    <h2>Pages</h2>
    <dl class="about-list">
      <div>
        <dt>Home</dt>
        <dd>Your progress at a glance, and one button that reviews whatever is due,
          or runs a quick set of 15 when nothing is.</dd>
      </div>
      <div>
        <dt>Practice</dt>
        <dd>Pick HSK levels or topics, then study vocabulary flashcards or pick the
          meaning of example sentences.</dd>
      </div>
      <div>
        <dt>Class</dt>
        <dd>The same practice, built from the vocabulary of specific class
          chapters.</dd>
      </div>
      <div>
        <dt>Watch</dt>
        <dd>Short clips from Chinese YouTube channels. Listen, then pick what was
          said.</dd>
      </div>
      <div>
        <dt>Search</dt>
        <dd>Every word, grouped by level, filterable by known, learning or due. Tap
          a word to see its examples and your history with it.</dd>
      </div>
      <div>
        <dt>Account</dt>
        <dd>Settings for theme, sounds and highlighting, plus a test for your
          device's Chinese voice.</dd>
      </div>
    </dl>
  </div>

  <div class="card">
    <h2>Content</h2>
    <p>
      Vocabulary follows the HSK 1–5 word lists, plus class chapter lists. Example
      sentences come from <a href="https://tatoeba.org" target="_blank" rel="noopener">Tatoeba</a>,
      shared under <a href="https://creativecommons.org/licenses/by/2.0/fr/" target="_blank" rel="noopener">CC BY 2.0 FR</a>.
      Sentence pinyin is generated automatically, so the occasional tone may be off.
    </p>
    <p>
      Clips play directly from their creators' YouTube channels, so the views go to
      them.
    </p>
  </div>
</div>

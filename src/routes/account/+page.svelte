<script>
  import { progress } from '$lib/progress.svelte.js';
  import { createAccount, signIn, signOut } from '$lib/pb.js';
  import { hasVoice, voiceName, speak } from '$lib/tts.js';
  import { theme } from '$lib/theme.svelte.js';

  let tab = $state('create'); // create | existing
  let busy = $state(false);
  let error = $state('');
  let fresh = $state(null); // the ID, shown once after creation
  let idInput = $state('');
  let copied = $state(false);

  async function create() {
    busy = true; error = '';
    try {
      const account = await createAccount();
      progress.rememberAccount(account);
      await progress.adoptRemote();
      fresh = account.username;
    } catch (e) {
      error = e?.message ?? 'Could not reach the server.';
    }
    busy = false;
  }

  async function restore() {
    busy = true; error = '';
    try {
      const account = await signIn(idInput);
      progress.rememberAccount(account);
      await progress.adoptRemote();
      idInput = '';
    } catch {
      error = 'No progress found for that ID.';
    }
    busy = false;
  }

  function leave() {
    signOut();
    progress.forgetAccount();
    fresh = null;
  }

  async function copyId(value) {
    await navigator.clipboard.writeText(value);
    copied = true;
    setTimeout(() => (copied = false), 1600);
  }

  function download() {
    const blob = new Blob([progress.export()], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'hsk-progress.json';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function upload(event) {
    const file = event.currentTarget.files?.[0];
    if (!file) return;
    try {
      progress.import(await file.text());
      error = '';
    } catch {
      error = 'That file could not be read.';
    }
  }
</script>

<div class="page">
  <h1>Account</h1>

  {#if fresh}
    <div class="card pop callout good">
      <h2>Write this down</h2>
      <p class="note tight">
        This ID is the only way back into your progress. There is no password and no reset.
      </p>
      <div class="card tint mono spaced">{fresh}</div>
      <button class="btn sm spaced" onclick={() => copyId(fresh)}>
        {copied ? 'Copied' : 'Copy ID'}
      </button>
    </div>
  {/if}

  {#if progress.signedIn}
    <div class="card">
      <p class="label">Signed in as</p>
      <p class="mono spaced">{progress.user?.username}</p>
      <p class="note tight">Sync: {progress.status}</p>
      <div class="chips spaced">
        <button class="btn sm auto" onclick={() => copyId(progress.user?.username)}>
          {copied ? 'Copied' : 'Copy ID'}
        </button>
        <button class="btn sm auto" onclick={leave}>Sign out</button>
      </div>
    </div>
  {:else}
    <div class="card">
      <div class="chips">
        <button class="chip" class:on={tab === 'create'} onclick={() => { tab = 'create'; error = ''; }}>
          New ID
        </button>
        <button class="chip" class:on={tab === 'existing'} onclick={() => { tab = 'existing'; error = ''; }}>
          I have an ID
        </button>
      </div>

      {#if tab === 'create'}
        <p class="note">
          No email, no password. You get one generated ID, and your progress follows it to
          any device you enter it on.
        </p>
        <button class="btn primary spaced" disabled={busy} onclick={create}>
          {busy ? 'Working…' : 'Generate my ID'}
        </button>
      {:else}
        <p class="note">Enter the ID you saved.</p>
        <div class="stack spaced">
          <input
            class="field mono"
            placeholder="jade-tiger-x7k2m9q4wp3n"
            bind:value={idInput}
            autocapitalize="none"
            autocorrect="off"
            autocomplete="username"
          />
          <button class="btn" disabled={busy || !idInput.trim()} onclick={restore}>
            Restore progress
          </button>
        </div>
      {/if}
    </div>
  {/if}

  {#if error}
    <div class="card callout bad">{error}</div>
  {/if}

  <div class="card">
    <h2>Your data</h2>
    <p class="note tight">
      {Object.keys(progress.cards).length} words have review history on this device.
    </p>
    <div class="stack spaced">
      <button class="btn sm" onclick={download}>Download a backup</button>
      <label class="btn sm">
        Restore from a file
        <input class="hidden-input" type="file" accept="application/json" onchange={upload} />
      </label>
      <button class="btn sm bad"
        onclick={() => confirm('Erase all review history?') && progress.reset()}>
        Erase progress
      </button>
    </div>
  </div>

  <div class="card">
    <h2>Appearance</h2>
    <div class="chips spaced">
      {#each [['system', 'Match device'], ['light', 'Light'], ['dark', 'Dark']] as [value, label]}
        <button class="chip" class:on={theme.mode === value} onclick={() => theme.set(value)}>
          {label}
        </button>
      {/each}
    </div>
  </div>

  <div class="card">
    <h2>Audio</h2>
    <p class="note tight">
      {hasVoice()
        ? `Using ${voiceName()}.`
        : 'No Chinese voice found on this device. Android users may need to install the Google Chinese language pack.'}
    </p>
    <button class="btn sm spaced" onclick={() => speak('你好，这是中文发音测试。')}>
      Test the voice
    </button>
  </div>
</div>

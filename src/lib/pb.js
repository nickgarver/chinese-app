import PocketBase from 'pocketbase';
import { browser } from '$app/environment';

export const PB_URL = import.meta.env.VITE_PB_URL || 'http://127.0.0.1:8090';

export const pb = browser ? new PocketBase(PB_URL) : null;

if (pb) pb.autoCancellation(false);

const ADJ = ['jade', 'amber', 'quiet', 'red', 'north', 'clever', 'small', 'bright',
             'iron', 'blue', 'swift', 'green', 'old', 'silver', 'warm', 'wild'];
const NOUN = ['tiger', 'crane', 'river', 'lotus', 'panda', 'bamboo', 'dragon', 'moon',
              'sparrow', 'lantern', 'mountain', 'fox', 'willow', 'carp', 'peony', 'wolf'];

/**
 * The ID is the only credential, so it carries all the entropy: two words for
 * readability plus 12 random base36 characters, about 2^62 of randomness. That
 * is far too large to guess, but it does mean anyone who sees the ID has full
 * access to that progress, and there is no way to recover a lost one.
 */
export function makeUserId() {
  const pick = new Uint32Array(2);
  crypto.getRandomValues(pick);
  const bytes = new Uint8Array(9);
  crypto.getRandomValues(bytes);
  const tail = [...bytes]
    .map((b) => b.toString(36).padStart(2, '0'))
    .join('')
    .slice(0, 12);
  return `${ADJ[pick[0] % ADJ.length]}-${NOUN[pick[1] % NOUN.length]}-${tail}`;
}

/**
 * PocketBase still wants a password, so derive one from the ID. It is not a
 * secret in its own right — the ID is — but it lets the same ID sign in on any
 * device without the user carrying a second string around.
 */
async function derivePassword(id) {
  const data = new TextEncoder().encode(`hsk-practice:v1:${id.trim().toLowerCase()}`);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
    .slice(0, 32);
}

export async function createAccount() {
  const username = makeUserId();
  const password = await derivePassword(username);
  await pb.collection('users').create({ username, password, passwordConfirm: password });
  await pb.collection('users').authWithPassword(username, password);
  return { username };
}

export async function signIn(rawId) {
  const username = rawId.trim().toLowerCase();
  const password = await derivePassword(username);
  await pb.collection('users').authWithPassword(username, password);
  return { username };
}

export function signOut() {
  pb?.authStore.clear();
}

export function currentUser() {
  if (!pb) return null;
  return pb.authStore.isValid ? (pb.authStore.record ?? pb.authStore.model) : null;
}

/** Re-authenticate from a stored ID alone. */
export async function resumeSession(id) {
  if (!pb || !id) return null;
  return signIn(id);
}

export async function fetchProgress() {
  const user = currentUser();
  if (!user) return {};
  try {
    const rec = await pb.collection('progress').getFirstListItem(`user="${user.id}"`);
    return typeof rec.cards === 'string' ? JSON.parse(rec.cards) : (rec.cards ?? {});
  } catch (err) {
    if (err?.status === 404) return {};
    throw err;
  }
}

/**
 * Whole-blob save. Fine at this size — a maxed-out user is a few hundred KB of
 * JSON. If you outgrow it, switch to an append-only `reviews` collection and
 * derive card state from the log.
 */
export async function saveProgress(cards) {
  const user = currentUser();
  if (!user) return;
  const payload = { user: user.id, cards, updated_at: new Date().toISOString() };
  try {
    const rec = await pb.collection('progress').getFirstListItem(`user="${user.id}"`);
    await pb.collection('progress').update(rec.id, payload);
  } catch (err) {
    if (err?.status === 404) await pb.collection('progress').create(payload);
    else throw err;
  }
}

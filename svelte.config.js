import adapter from '@sveltejs/adapter-static';

// GitHub Pages project sites live at /<repo>/, so the app needs a base path.
// Set BASE_PATH in CI; leave it unset for local dev and root-domain hosting.
const base = process.env.BASE_PATH ?? '';

export default {
  kit: {
    adapter: adapter({ fallback: 'index.html' }),
    paths: { base },
    prerender: { entries: [] }
  }
};
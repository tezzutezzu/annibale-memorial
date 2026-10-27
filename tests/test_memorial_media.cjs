/* Functional checks against the local archive; no external network is needed.
 * CSS/layout are checked separately in the in-app browser with the real styles.
 * NODE_PATH=<playwright packages> CHROMIUM_EXECUTABLE=<browser> node tests/test_memorial_media.cjs
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const base = process.env.BASE_URL || 'http://127.0.0.1:8899/';
const rows = fs.readFileSync(path.join(__dirname, '../data/posts.jsonl'), 'utf8')
  .trim().split('\n').map(JSON.parse);
const bySource = id => rows.find(p => p.id === id || (p.aliases || []).includes(id));

(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {}) });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('https://**/*', route => route.fulfill({
      contentType: route.request().resourceType() === 'script' ? 'text/javascript' : 'text/css',
      body: route.request().resourceType() === 'script' ? 'window.tailwind = {};' : '',
    }));
    async function open(id) {
      await page.goto(base + '#' + id);
      const canonical = bySource(id).id;
      await page.waitForFunction(expected => document.querySelector('#counter').textContent &&
        location.hash === '#' + expected, canonical);
    }
    await open('ig_DeyTGIhgMCX');
    assert.equal(new URL(page.url()).hash, '#fb_10246260011659377', 'old Facebook identity remains canonical');
    assert.ok((await page.locator('#text').innerText()).length > 1400, 'full Instagram text replaces clipped preview');
    assert.equal(await page.locator('#source-links a').count(), 2);
    assert.ok((await page.locator('#source-links').innerText()).includes('Facebook'));
    assert.ok((await page.locator('#source-links').innerText()).includes('Instagram'));

    await open('ig_DexDvKgDqXQ');
    assert.equal(await page.locator('#photo-counter').innerText(), 'Foto 1 / 16');
    await page.getByRole('button', { name: 'Contenuto successivo', exact: true }).click();
    assert.equal(await page.locator('#photo-counter').innerText(), 'Video 2 / 16');
    await page.waitForFunction(() => document.querySelector('#video').readyState >= 1);
    await page.locator('#video').evaluate(el => el.play());
    await page.waitForFunction(() => document.querySelector('#video').currentTime > 0);
    const beforeHash = new URL(page.url()).hash;
    await page.locator('#video').press('ArrowRight');
    assert.equal(new URL(page.url()).hash, beforeHash, 'player shortcuts must not change memory');
    await page.getByRole('button', { name: 'Contenuto successivo', exact: true }).click();
    assert.equal(await page.locator('#photo-counter').innerText(), 'Foto 3 / 16');
    assert.equal(await page.locator('#video').evaluate(el => el.paused && !el.getAttribute('src')), true,
      'leaving a video stops playback and clears its source');
    for (let i = 3; i < 16; i++) {
      await page.getByRole('button', { name: 'Contenuto successivo', exact: true }).click();
    }
    assert.equal(await page.locator('#photo-counter').innerText(), 'Foto 16 / 16');
    assert.equal(await page.getByRole('button', { name: 'Contenuto successivo', exact: true }).isEnabled(), false);

    const input = JSON.parse(fs.readFileSync(path.join(__dirname, '../instagram/import/2026-10-27.json'), 'utf8'));
    for (const post of input.posts.filter(p => p.media.some(m => m.type === 'video'))) {
      await open(post.id);
      const canonical = bySource(post.id);
      const playable = canonical.media.filter(m => m.type === 'image' || (m.type === 'video' && m.local_path));
      const index = playable.findIndex(m => m.type === 'video' && m.local_path);
      for (let i = 0; i < index; i++) {
        await page.getByRole('button', { name: 'Contenuto successivo', exact: true }).click();
      }
      await page.waitForFunction(() => !document.querySelector('#video').hidden && document.querySelector('#video').readyState >= 1);
      assert.ok(await page.locator('#video').evaluate(el => Number.isFinite(el.duration) && el.duration > 10), post.author);
    }

    await open('ig_DevvSZzs54Z');
    assert.equal(new URL(page.url()).hash, '#ig_Dev0CHpo0ON');
    assert.equal(await page.locator('#source-links a').count(), 2, 'both Puglia Culture accounts remain credited');
    await page.getByRole('searchbox').fill('pugliaculture_circuitoteatrale');
    await page.getByRole('option').first().waitFor({ state: 'visible' });
    assert.equal(await page.getByRole('option').count(), 1, 'secondary source author is searchable');
    assert.deepEqual(errors, []);
    console.log('PASS: aliases, full text, source links, mixed gallery, all six local videos, player shortcuts and search');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });

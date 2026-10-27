/* Offline DOM integration tests. Requires playwright and a Chromium executable.
 * NODE_PATH=<playwright packages> CHROMIUM_EXECUTABLE=<browser> node tests/test_instagram_console.cjs
 * Every HTTP request is intercepted; no Instagram account or network is used.
 */
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('playwright');

const fixture = `<!doctype html><html><head><title>Annibale</title><style>
body { margin: 0; } main { height: 600px; } a.tile { display: inline-block; }
.tile img { width: 200px; height: 180px; } [role=dialog] { position: fixed; inset: 0; background: white; }
article { width: 800px; height: 600px; } article > img, article > video { width: 500px; height: 300px; }
button { min-width: 60px; min-height: 30px; } header img { width: 32px; height: 32px; }
</style></head><body>
<aside><a href="/p/OUTSIDE/"><img src="https://cdn.example/outside.jpg" width="200" height="180"></a></aside>
<main><a class="tile" href="/amico/p/FIRST123456/"><img src="https://cdn.example/thumb1.jpg"></a>
<a class="tile" href="/reel/SECOND/"><img src="https://cdn.example/thumb2.jpg"></a></main>
<script>
window.opened = [];
for (const a of document.querySelectorAll('main a')) a.onclick = event => {
  event.preventDefault();
  const id = a.pathname.split('/').filter(Boolean).pop();
  window.opened.push(id);
  history.pushState({}, '', a.getAttribute('href'));
  const d = document.createElement('div'); d.setAttribute('role', 'dialog');
  d.innerHTML = '<button aria-label="Chiudi">Chiudi</button><article>' +
    '<header><a href="/amico/">amico</a><img src="https://cdn.example/avatar.jpg"></header>' +
    (window.noCaption ? '' : '<h1>Un ricordo<br>per Annibale</h1>') +
    '<a href="/p/' + id + '/"><time datetime="2026-10-24T12:00:00Z">24 ottobre</time></a>' +
    (window.emptyPost ? '' : '<img alt="Foto del ricordo" src="https://cdn.example/' + id + '-one.jpg">') +
    (id.startsWith('FIRST') ? '<button aria-label="Avanti">Avanti</button>' : '') +
    '<ul><li><a href="/commentatore/">commentatore</a><span dir="auto">COMMENTO DA ESCLUDERE</span></li></ul></article>';
  document.body.appendChild(d);
  const buttons = d.querySelectorAll('button');
  document.body.appendChild(buttons[0]); // Instagram's close button is outside the dialog.
  buttons[0].onclick = () => { buttons[0].remove(); d.remove(); history.replaceState({}, '', '/andrea/saved/annibale/'); };
  if (buttons[1]) buttons[1].onclick = () => {
    if (window.stuckCarousel) return;
    if (window.mixedCarousel && !d.querySelector('video')) {
      d.querySelector('article > img').style.display = 'none';
      const video = document.createElement('video');
      video.src = 'blob:https://www.instagram.com/fixture-video';
      d.querySelector('article').prepend(video);
      return;
    }
    d.querySelector('video')?.remove();
    d.querySelector('article > img').style.display = '';
    d.querySelector('article > img').src = 'https://cdn.example/' + id + '-two.jpg';
    buttons[1].remove();
  };
};
</script></body></html>`;

(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {}),
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1200, height: 1000 } });
    const pixel = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jR1sAAAAASUVORK5CYII=', 'base64');
    await page.route('**/*', route => route.fulfill(route.request().resourceType() === 'image'
      ? { contentType: 'image/png', body: pixel }
      : { contentType: 'text/html', body: fixture }));
    await page.goto('https://www.instagram.com/andrea/saved/annibale/');
    await page.addScriptTag({ path: path.join(__dirname, '../console/ig_scrape_console.js') });
    assert.equal(await page.evaluate(() => igScrape.status().posts), 0, 'pasting must not start collection');
    assert.equal(await page.evaluate(() => igScrape.collectLinks()), 2, 'only collection tiles belong to the queue');
    const opts = { maxPosts: 2, maxScrolls: 2, startFromTop: false,
      delayMin: 0, delayMax: 0, openWait: 30, slideWait: 30, timeout: 1000 };
    await page.evaluate(cfg => igScrape.run(cfg), opts);
    let data = await page.evaluate(() => ({ posts: igScrape.posts(), status: igScrape.status(), opened }));
    assert.equal(data.posts.length, 2);
    assert.equal(data.posts[0].media.length, 2, 'carousel must retain both slides: ' + JSON.stringify(data));
    assert.equal(data.posts[1].media.length, 1);
    assert.equal(data.posts[0].author, 'amico');
    assert.equal(data.posts[0].time_text, '2026-10-24');
    assert.equal(data.posts[0].text, 'Un ricordo\nper Annibale');
    assert.equal(data.status.pending, 0);
    assert.equal(data.status.warnings, 0);
    assert.equal(new URL(page.url()).pathname, '/andrea/saved/annibale/');
    assert.deepEqual(data.opened, ['FIRST123456', 'SECOND']);

    await page.evaluate(cfg => igScrape.run(cfg), opts);
    assert.equal(await page.evaluate(() => opened.length), 2, 'completed posts must not be reopened');
    await page.reload();
    await page.addScriptTag({ path: path.join(__dirname, '../console/ig_scrape_console.js') });
    assert.equal(await page.evaluate(() => igScrape.restore()), 2, 'progress must survive reload');

    await page.evaluate(() => { igScrape.reset(); window.mixedCarousel = true; });
    await page.evaluate(cfg => igScrape.run({ ...cfg, maxPosts: 1 }), opts);
    data = await page.evaluate(() => igScrape.posts()[0]);
    assert.deepEqual(data.media.map(m => m.type), ['image', 'video', 'image'],
      'a streamed video must not stop the carousel or lose later images');
    assert.equal(data.carousel_complete, true);
    assert.ok(data.capture_warnings.includes('video_stream_without_direct_url'));
    assert.ok(!data.capture_warnings.includes('carousel_did_not_advance'));
    assert.equal(await page.evaluate(() => igScrape.retryWarnings({authors:['another']})), 0);
    assert.equal(await page.evaluate(() => igScrape.retryWarnings({authors:['amico']})), 1);

    await page.evaluate(() => { igScrape.reset(); window.mixedCarousel = false; window.noCaption = true; window.stuckCarousel = true; });
    await page.evaluate(cfg => igScrape.run({ ...cfg, maxPosts: 1 }), opts);
    data = await page.evaluate(() => igScrape.posts()[0]);
    assert.equal(data.text, '', 'a comment must never become the caption');
    assert.ok(data.capture_warnings.includes('caption_not_found_or_empty'));
    assert.ok(data.capture_warnings.includes('carousel_did_not_advance'));
    assert.equal(data.carousel_complete, false);
    await page.evaluate(() => igScrape.retryWarnings());
    assert.equal(await page.evaluate(() => igScrape.links()[0].status), 'pending');

    await page.evaluate(() => { igScrape.reset(); window.noCaption = true; window.emptyPost = true; });
    await page.evaluate(cfg => igScrape.run(cfg), opts);
    const failed = await page.evaluate(() => ({ status: igScrape.status(), links: igScrape.links() }));
    assert.equal(failed.status.posts, 0, 'empty captures must not enter the importable posts');
    assert.equal(failed.status.last_run.reason, 'capture_error');
    assert.equal(failed.links[0].status, 'error');
    assert.equal(failed.links[1].attempts, 0, 'stop at first extraction failure');

    await page.evaluate(() => history.replaceState({}, '', '/andrea/saved/other/'));
    await assert.rejects(page.evaluate(() => igScrape.run()), /Raccolta diversa/);
    console.log('PASS: grid scope, modal opening/closing, caption isolation, carousel, identity, resume, warnings and failure stop');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });

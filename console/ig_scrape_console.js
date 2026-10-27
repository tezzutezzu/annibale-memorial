/* Instagram saved collection -> local JSON, using only the rendered page.
 * Paste in the collection's DevTools Console, then:
 *   await igScrape.run({ maxPosts: 3 })   // first check a small sample
 *   igScrape.saveJSON()
 * Nothing starts on paste. No API tokens, cookies or private endpoints are read.
 * Instagram's DOM changes: inspect the sample before collecting everything.
 */
(() => {
  'use strict';
  if (!/(^|\.)instagram\.com$/.test(location.hostname)) {
    throw new Error('Apri la raccolta su instagram.com prima di incollare lo script.');
  }
  if (window.igScrape?.status().running) {
    console.warn('[igScrape] Già in esecuzione: usa igScrape.stop().');
    return;
  }

  const CFG = {
    maxPosts: 500, maxScrolls: 300, idleLimit: 8,
    delayMin: 1800, delayMax: 3000, openWait: 1500, timeout: 15000,
    maxSlides: 30, slideWait: 1200, startFromTop: true,
    collectionName: '', captionSelector: '', linksOnly: false,
  };
  const LS_KEY = 'annibale.igScrape.v1';
  const state = window.__igCapture || {
    version: 1, collection_url: '', collection_name: '',
    posts: [], links: [], last_run: null,
  };
  window.__igCapture = state;
  let running = false;
  let stopFlag = false;
  let storageWarned = false;
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const text = el => (el?.textContent || '').trim();
  const log = message => console.log('[igScrape] ' + message);
  const warn = message => console.warn('[igScrape] ' + message);

  function canonical(value) {
    try {
      const u = new URL(value, location.href);
      if (!['instagram.com', 'www.instagram.com'].includes(u.hostname)) return null;
      const m = u.pathname.match(/^\/(?:[\w.]+\/)?(?:p|reel|reels|tv)\/([A-Za-z0-9_-]+)\/?$/);
      return m ? 'https://www.instagram.com/p/' + m[1] + '/' : null;
    } catch (_) { return null; }
  }
  const code = url => canonical(url)?.split('/')[4];
  const scope = () => document.querySelector('main, [role="main"]') || document.body;
  const isCollection = () => /\/saved(?:\/|$)/.test(location.pathname);
  const samePage = url => {
    const u = new URL(url);
    return u.pathname === location.pathname && u.search === location.search;
  };

  function persist() {
    state.saved_at = new Date().toISOString();
    try {
      const raw = JSON.stringify(state);
      if (raw.length > 4_000_000) throw new Error('quota');
      localStorage.setItem(LS_KEY, raw);
      return true;
    } catch (_) {
      if (!storageWarned) warn('Copia locale non disponibile o piena: salva ora con igScrape.saveJSON().');
      storageWarned = true;
      return false;
    }
  }

  function savedInfo() {
    try {
      const s = JSON.parse(localStorage.getItem(LS_KEY) || 'null');
      return s && { count: s.posts.length, links: s.links.length,
        saved_at: s.saved_at, collection_url: s.collection_url };
    } catch (_) { return null; }
  }

  function restore() {
    if (running) throw new Error('Ferma prima la raccolta.');
    const s = JSON.parse(localStorage.getItem(LS_KEY) || 'null');
    if (!s || s.version !== 1 || !Array.isArray(s.posts) || !Array.isArray(s.links)) return 0;
    if (s.collection_url && !samePage(s.collection_url)) {
      throw new Error('Apri la raccolta originale prima di restore(): ' + s.collection_url);
    }
    Object.assign(state, s);
    log('Ripristinati ' + state.posts.length + ' post e ' + state.links.length + ' link.');
    return state.posts.length;
  }

  // Intersect overflow ancestors too: carousels preload off-screen slides.
  function visible(el) {
    let r = el.getBoundingClientRect();
    let left = Math.max(0, r.left), right = Math.min(innerWidth, r.right);
    let top = Math.max(0, r.top), bottom = Math.min(innerHeight, r.bottom);
    if (!r.width || !r.height || getComputedStyle(el).visibility === 'hidden') return false;
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const style = getComputedStyle(p);
      if (Number(style.opacity) === 0 || style.display === 'none') return false;
      const b = p.getBoundingClientRect();
      if (/(hidden|clip|scroll|auto)/.test(style.overflowX)) {
        left = Math.max(left, b.left); right = Math.min(right, b.right);
      }
      if (/(hidden|clip|scroll|auto)/.test(style.overflowY)) {
        top = Math.max(top, b.top); bottom = Math.min(bottom, b.bottom);
      }
    }
    return right - left > Math.min(30, r.width / 2) && bottom - top > Math.min(30, r.height / 2);
  }

  function postRoot(expected) {
    const roots = [...document.querySelectorAll('article'), ...document.querySelectorAll('[role="dialog"]')];
    return roots.find(root => visible(root) &&
      (root.tagName === 'ARTICLE' || root.querySelector('h1') ||
       [...root.querySelectorAll('img, video')].some(el => el.getBoundingClientRect().width >= 150)) && (
      canonical(location.href) === expected ||
      [...root.querySelectorAll('time')].some(t => canonical(t.closest('a')?.href) === expected)
    )) || null;
  }

  function profileLink(root) {
    const candidates = root.querySelectorAll('header a[href], h2 a[href], h1 a[href]');
    return [...candidates].find(a => {
      try {
        const u = new URL(a.href);
        return u.hostname.endsWith('instagram.com') && /^\/[\w.]+\/$/.test(u.pathname) &&
          !/^\/(?:explore|direct|accounts|reels|stories)\/$/.test(u.pathname) && text(a);
      } catch (_) { return false; }
    });
  }

  function caption(root, author, selector) {
    const heading = root.querySelector(selector || 'h1');
    if (heading) return (heading.innerText || text(heading)).trim();
    // Older layouts place the caption in the first list row, next to its author.
    // Never use the article's whole text: that includes comments and UI labels.
    const first = root.querySelector('ul > li');
    if (first && author && [...first.querySelectorAll('h2 a')].some(a => text(a) === author)) {
      const body = first.querySelector('span[dir="auto"], span[dir="ltr"], div[dir="auto"]');
      if (body && text(body) !== author) return (body.innerText || text(body)).trim();
    }
    return '';
  }

  function media(root) {
    const result = [];
    for (const el of root.querySelectorAll('img, video')) {
      if (!visible(el) || el.closest('header')) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 150 || r.height < 120) continue; // avatars and action icons
      if (el.tagName === 'IMG') {
        const url = el.currentSrc || el.src;
        if (/^https?:/.test(url)) result.push({ type: 'image', url, alt: el.alt || '' });
      } else {
        const url = el.currentSrc || el.src || el.querySelector('source')?.src || '';
        result.push({ type: 'video', url: /^https?:/.test(url) ? url : '',
          poster: el.poster || '', stream_only: !/^https?:/.test(url) });
        if (/^https?:/.test(el.poster || '')) {
          result.push({ type: 'image', url: el.poster, alt: 'Anteprima video Instagram', video_poster: true });
        }
      }
    }
    return result;
  }

  // A streamed video has no downloadable URL in media(), but its blob URL still
  // identifies the visible slide. Keep this transient key out of the export.
  const mediaNodeIds = new WeakMap();
  let mediaNodeCounter = 0;
  function mediaSignature(root) {
    return [...root.querySelectorAll('img, video')].filter(el => {
      const r = el.getBoundingClientRect();
      return visible(el) && !el.closest('header') && r.width >= 150 && r.height >= 120;
    }).map(el => {
      if (!mediaNodeIds.has(el)) mediaNodeIds.set(el, ++mediaNodeCounter);
      const src = el.currentSrc || el.src || el.querySelector('source')?.src || el.poster || '';
      return el.tagName + ':' + (src || 'node-' + mediaNodeIds.get(el));
    }).join('|');
  }

  function labelledButton(root, pattern) {
    for (const el of root.querySelectorAll('button, [role="button"]')) {
      if (!visible(el) || el.disabled || el.getAttribute('aria-disabled') === 'true') continue;
      const labels = [el.getAttribute('aria-label'), text(el),
        ...[...el.querySelectorAll('[aria-label], title')].map(n => n.getAttribute('aria-label') || text(n))];
      if (labels.some(label => pattern.test((label || '').trim()))) return el;
    }
    return null;
  }
  const NEXT = /^(?:next|avanti|successiv[oa]|next slide|diapositiva successiva)$/i;
  const CLOSE = /^(?:close|chiudi|close dialog|chiudi finestra)$/i;

  function carouselNext(root) {
    const next = labelledButton(root, NEXT);
    if (!next || root.tagName === 'ARTICLE') return next;
    // A dialog may also have a "Next post" arrow outside the media. Never click
    // that as if it advanced the carousel of the current post.
    const b = next.getBoundingClientRect();
    const x = b.left + b.width / 2, y = b.top + b.height / 2;
    return [...root.querySelectorAll('img, video')].some(el => {
      if (!visible(el) || el.closest('header')) return false;
      const r = el.getBoundingClientRect();
      return r.width >= 150 && r.height >= 120 && x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
    }) ? next : null;
  }

  async function waitFor(fn, timeout, honourStop = true) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const value = fn();
      if (value) return value;
      if (honourStop && stopFlag) throw new Error('Interrotto');
      await sleep(200);
    }
    throw new Error('Tempo di attesa esaurito: controllare la pagina e i selettori.');
  }

  async function capture(expected, cfg) {
    let root = await waitFor(() => postRoot(expected), cfg.timeout);
    await sleep(cfg.openWait);
    root = postRoot(expected);
    if (!root) throw new Error('Il post è cambiato durante il caricamento.');
    const more = [...root.querySelectorAll('button, [role="button"]')].find(el =>
      !el.querySelector('svg') && visible(el) &&
      /^(?:…?\s*more|altro|vedi altro|leggi tutto|see more)$/i.test(text(el)));
    if (more) { more.click(); await sleep(500); }
    const authorLink = profileLink(root);
    const author = text(authorLink);
    const times = [...root.querySelectorAll('time')];
    const time = times.find(t => canonical(t.closest('a')?.href) === expected) || times[0];
    const post = {
      id: 'ig_' + code(expected), platform: 'instagram', source: 'collection',
      permalink: expected, author, author_url: authorLink?.href || '',
      text: caption(root, author, cfg.captionSelector),
      published_at: time?.getAttribute('datetime') || '',
      time_text: time?.getAttribute('datetime')?.slice(0, 10) || time?.getAttribute('title') || text(time),
      collected_at: new Date().toISOString(), collection_url: state.collection_url,
      collection_name: state.collection_name, media: [], capture_warnings: [],
      carousel_complete: false,
    };
    const seen = new Set();
    let previous = '';
    for (let slide = 0; slide < cfg.maxSlides; slide++) {
      root = postRoot(expected);
      if (!root) throw new Error('Post non più visibile.');
      let signature = mediaSignature(root);
      if (slide && (!signature || signature === previous)) {
        // Rendering and video loading may take longer than the pacing pause.
        try {
          await waitFor(() => {
            const current = postRoot(expected);
            const key = current && mediaSignature(current);
            return key && key !== previous;
          }, cfg.timeout);
          root = postRoot(expected);
          signature = mediaSignature(root);
        } catch (_) {
          post.capture_warnings.push(stopFlag ? 'stopped_during_carousel' : 'carousel_did_not_advance');
          break;
        }
      }
      previous = signature;
      const items = media(root);
      for (const item of items) {
        // Consecutive streamed videos may both lack url/poster. Preserve each
        // slide rather than merging all such videos into a single placeholder.
        const key = item.type + ':' + (item.url || item.poster || 'slide-' + slide);
        if (!seen.has(key)) { seen.add(key); post.media.push(item); }
      }
      const next = carouselNext(root);
      if (!next) { post.carousel_complete = true; break; }
      if (stopFlag) { post.capture_warnings.push('stopped_during_carousel'); break; }
      if (slide + 1 === cfg.maxSlides) { post.capture_warnings.push('max_slides'); break; }
      next.click();
      await sleep(cfg.slideWait);
    }
    if (!post.text) post.capture_warnings.push('caption_not_found_or_empty');
    if (!post.author) post.capture_warnings.push('author_not_found');
    if (!post.media.length) post.capture_warnings.push('media_not_found');
    if (post.media.some(m => m.stream_only)) post.capture_warnings.push('video_stream_without_direct_url');
    if (!post.text && !post.media.length) throw new Error('Nessun testo o media: post non importato.');
    return post;
  }

  function ingest(post) {
    const i = state.posts.findIndex(p => p.id === post.id);
    if (i < 0) state.posts.push(post);
    else {
      const old = state.posts[i];
      state.posts[i] = { ...post,
        text: (old.text || '').length > post.text.length ? old.text : post.text,
        media: old.carousel_complete && !post.carousel_complete ? old.media : post.media,
      };
    }
    persist();
  }

  function tiles() {
    const result = new Map();
    for (const a of scope().querySelectorAll('a[href]')) {
      const link = canonical(a.href);
      if (link && visible(a) && a.querySelector('img, video')) result.set(link, a);
    }
    return result;
  }

  function collectLinks() {
    if (!isCollection()) throw new Error('Apri prima la raccolta nei Salvati.');
    if (state.collection_url && !samePage(state.collection_url)) {
      throw new Error('Raccolta diversa: salva il JSON, poi usa reset() prima di cambiare raccolta.');
    }
    state.collection_url ||= location.href;
    let added = 0;
    for (const link of tiles().keys()) {
      if (!state.links.some(item => item.permalink === link)) {
        state.links.push({ permalink: link, status: 'pending', attempts: 0 });
        added++;
      }
    }
    persist();
    return added;
  }

  function scroller() {
    let el = tiles().values().next().value;
    for (let p = el?.parentElement; p && p !== document.body; p = p.parentElement) {
      if (/(auto|scroll)/.test(getComputedStyle(p).overflowY) && p.scrollHeight > p.clientHeight + 20) return p;
    }
    return document.scrollingElement || document.documentElement;
  }

  async function closePost(expected, collectionURL, historyLength, cfg) {
    if (samePage(collectionURL) && !postRoot(expected)) return;
    // Only touch a close button after verifying that the requested post is open.
    if (!postRoot(expected) && canonical(location.href) !== expected) {
      throw new Error('Navigazione inattesa: torna alla raccolta manualmente.');
    }
    const dialog = document.querySelector('[role="dialog"]');
    const close = (dialog && labelledButton(dialog, CLOSE)) || labelledButton(document, CLOSE);
    if (close) close.click();
    else if (canonical(location.href) === expected && history.length > historyLength) history.back();
    else throw new Error('Chiusura automatica non disponibile: torna alla raccolta e rilancia run().');
    await waitFor(() => samePage(collectionURL) && !postRoot(expected), cfg.timeout, false);
  }

  async function run(options = {}) {
    if (running) { warn('Già in esecuzione.'); return status(); }
    if (!isCollection() || document.querySelector('[role="dialog"] article')) {
      throw new Error('Apri la griglia della raccolta nei Salvati e chiudi il post aperto.');
    }
    const cfg = { ...CFG, ...options };
    for (const key of ['maxPosts', 'maxScrolls', 'idleLimit', 'maxSlides', 'timeout']) {
      if (!Number.isInteger(cfg[key]) || cfg[key] < 1) throw new Error('Opzione non valida: ' + key);
    }
    for (const key of ['delayMin', 'delayMax', 'openWait', 'slideWait']) {
      if (!Number.isFinite(cfg[key]) || cfg[key] < 0) throw new Error('Opzione non valida: ' + key);
    }
    if (document.visibilityState === 'hidden') throw new Error('Tieni la scheda Instagram in primo piano.');
    collectLinks(); // enforces the collection boundary before changing state
    state.collection_name = cfg.collectionName || state.collection_name || document.title;
    running = true; stopFlag = false;
    const attempted = new Set();
    let idle = 0;
    let reason = 'max_scrolls';
    log('Avvio; stop con igScrape.stop(). Mantieni la scheda in primo piano.');
    try {
      if (cfg.startFromTop) { scroller().scrollTop = 0; await sleep(1000); }
      for (let round = 0; round < cfg.maxScrolls; round++) {
        if (stopFlag) { if (reason !== 'capture_error') reason = 'stopped'; break; }
        if (document.visibilityState === 'hidden') { reason = 'hidden_tab'; break; }
        if ((cfg.linksOnly ? state.links.length : state.posts.length) >= cfg.maxPosts) {
          reason = 'max_posts'; break;
        }
        const added = collectLinks();
        let captured = 0;
        if (!cfg.linksOnly) {
          for (const [link] of tiles()) {
            if (stopFlag || state.posts.length >= cfg.maxPosts) break;
            const entry = state.links.find(item => item.permalink === link);
            if (entry.status === 'captured' || attempted.has(link)) continue;
            attempted.add(link);
            const anchor = tiles().get(link);
            if (!anchor) continue;
            const returnURL = location.href;
            const historyLength = history.length;
            entry.attempts++; entry.status = 'opening'; delete entry.error;
            persist(); // a full-page navigation must not lose the pending link
            anchor.click();
            try {
              const post = await capture(link, cfg);
              ingest(post); entry.status = 'captured'; captured++;
              log(state.posts.length + ' post; ' + post.author + '; ' + post.media.length + ' media' +
                (post.capture_warnings.length ? '; avvisi: ' + post.capture_warnings.join(', ') : ''));
            } catch (error) {
              entry.status = 'error'; entry.error = error.message;
              warn(link + ': ' + error.message);
              // A changed layout, login wall or challenge needs a human check.
              stopFlag = true; reason = 'capture_error';
            } finally {
              persist();
              await closePost(link, returnURL, historyLength, cfg);
            }
            if (stopFlag) break;
            await sleep(cfg.delayMin + Math.random() * Math.max(0, cfg.delayMax - cfg.delayMin));
          }
        }
        idle = added || captured ? 0 : idle + 1;
        const s = scroller(), before = s.scrollTop;
        if (!stopFlag) s.scrollTop += Math.max(250, s.clientHeight * 0.8);
        log('Giro ' + (round + 1) + ': ' + state.links.length + ' link, ' + state.posts.length + ' post.');
        if (idle >= cfg.idleLimit && s.scrollTop === before) { reason = 'end_of_loaded_grid'; break; }
        if (stopFlag) break;
        await sleep(cfg.delayMin + Math.random() * Math.max(0, cfg.delayMax - cfg.delayMin));
      }
    } catch (error) {
      reason = 'error'; warn(error.message);
    } finally {
      running = false;
      if (reason === 'max_scrolls' && stopFlag) reason = 'stopped';
      if (reason === 'max_scrolls' && (cfg.linksOnly ? state.links.length : state.posts.length) >= cfg.maxPosts) reason = 'max_posts';
      state.last_run = { ended_at: new Date().toISOString(), reason,
        pending: state.links.filter(item => item.status !== 'captured').length };
      persist();
      log('Fermo (' + reason + '). ' + state.posts.length + ' post, ' + state.last_run.pending +
        ' link da completare. Ora: igScrape.saveJSON()');
    }
    return status();
  }

  function saveJSON(name = 'ig_posts') {
    persist();
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = name + '_' + new Date().toISOString().replace(/[:.]/g, '-') + '.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    log('Salvati ' + state.posts.length + ' post; il JSON include anche link e avvisi.');
    return state.posts.length;
  }

  function status() {
    return { running, posts: state.posts.length, links: state.links.length,
      pending: state.links.filter(item => item.status !== 'captured').length,
      warnings: state.posts.filter(p => p.capture_warnings.length).length,
      collection_url: state.collection_url, last_run: state.last_run };
  }

  window.igScrape = {
    run, stop() { stopFlag = true; log('Arresto dopo il post corrente.'); },
    saveJSON, persist, savedInfo, restore, collectLinks, status,
    posts: () => state.posts, links: () => state.links,
    inspect: () => ({ ...status(), visible_tiles: tiles().size,
      articles: document.querySelectorAll('article').length, url: location.href }),
    async dump(options = {}) {
      if (running) throw new Error('Ferma prima la raccolta.');
      const link = canonical(location.href);
      if (!link) throw new Error('Apri un singolo post per dump(); dalla griglia usa run().');
      stopFlag = false;
      ingest(await capture(link, { ...CFG, ...options }));
      return saveJSON();
    },
    retryWarnings(options = {}) {
      if (running) throw new Error('Ferma prima la raccolta.');
      let queued = 0;
      for (const entry of state.links) {
        if (state.posts.some(p => p.permalink === entry.permalink && p.capture_warnings.length &&
          (!options.authors || options.authors.includes(p.author)))) {
          entry.status = 'pending'; queued++;
        }
      }
      persist();
      return queued;
    },
    reset() {
      if (running) throw new Error('Ferma prima la raccolta.');
      state.posts.length = 0; state.links.length = 0;
      state.collection_url = ''; state.collection_name = ''; state.last_run = null;
      localStorage.removeItem(LS_KEY);
    },
    config: { ...CFG },
  };
  log('Pronto. Prova: await igScrape.run({ maxPosts: 3 }); poi igScrape.saveJSON().');
  if (savedInfo()) log('Esiste una copia locale: igScrape.savedInfo(); igScrape.restore() per recuperarla.');
})();

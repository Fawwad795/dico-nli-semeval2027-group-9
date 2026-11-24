// Evaluated by the renderer after the screenshot. Returns the slide's measured geometry as JSON.
// Opt-outs on any ancestor: data-pcv-allow="overlap small bleed contrast spelling decor".
(opts) => {
  const root = document.querySelector(opts.selector);
  if (!root) return { error: `slide root not found: ${opts.selector}` };

  const r2 = (r) => ({ x: +r.left.toFixed(2), y: +r.top.toFixed(2), w: +r.width.toFixed(2), h: +r.height.toFixed(2) });
  const allow = (el, what) => !!el.closest(`[data-pcv-allow~="${what}"]`);
  const pathOf = (el) => {
    if (el === root) return '';
    const parts = [];
    for (let e = el; e && e !== root; e = e.parentElement) {
      const p = e.parentElement;
      if (!p) break;
      parts.unshift(`${e.tagName.toLowerCase()}:nth-child(${Array.prototype.indexOf.call(p.children, e) + 1})`);
    }
    return parts.join(' > ');
  };
  const visible = (el) => !el.checkVisibility || el.checkVisibility({ opacityProperty: true, visibilityProperty: true });
  const isBlock = (e) => {
    const d = getComputedStyle(e).display;
    return !(d === 'inline' || d === 'contents');
  };
  const blockOf = (el) => {
    for (let e = el; e; e = e.parentElement) if (e === root || isBlock(e)) return e;
    return root;
  };
  const opacityOf = (el) => {
    let o = 1;
    for (let e = el; e; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity);
    return o;
  };
  const clipsOf = (el) => {
    const out = [];
    for (let e = el; e && e !== root; e = e.parentElement) {
      const cs = getComputedStyle(e);
      const cx = cs.overflowX !== 'visible', cy = cs.overflowY !== 'visible';
      if (cx || cy) out.push({ path: pathOf(e), rect: r2(e.getBoundingClientRect()), x: cx, y: cy });
    }
    return out;
  };

  const blocks = new Map();
  const blockList = [];
  const blockId = (b) => {
    if (!blocks.has(b)) {
      const cs = getComputedStyle(b);
      blocks.set(b, blockList.length);
      blockList.push({
        path: pathOf(b), tag: b.tagName.toLowerCase(), rect: r2(b.getBoundingClientRect()),
        scroll: [b.scrollWidth, b.scrollHeight], client: [b.clientWidth, b.clientHeight],
        overflow: [cs.overflowX, cs.overflowY], fontSize: parseFloat(cs.fontSize),
        isRoot: b === root, svg: b instanceof SVGElement, overlapAllowed: allow(b, 'overlap'),
      });
    }
    return blocks.get(b);
  };

  const texts = [];
  const samples = new Map();
  const fontSamples = [];
  let fid = 0;
  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = tw.nextNode(); n; n = tw.nextNode()) {
    const raw = n.nodeValue;
    if (!raw || !raw.trim()) continue;
    const el = n.parentElement;
    if (!el || ['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'TITLE'].includes(el.tagName)) continue;
    if (!visible(el)) continue;
    const range = document.createRange();
    range.selectNodeContents(n);
    const rects = Array.from(range.getClientRects()).filter((r) => r.width > 0.5 && r.height > 0.5).map(r2);
    if (!rects.length) continue;
    const cs = getComputedStyle(el);
    // Rendered size: SVG text scales with its viewBox (screen CTM); HTML text with the scale part of
    // every ancestor's CSS transform (rotation does not change size, so bounding boxes are not used).
    let scale = 1;
    if (el instanceof SVGGraphicsElement && el.getScreenCTM) {
      const m = el.getScreenCTM();
      if (m) scale = Math.hypot(m.a, m.b) || 1;
    } else {
      for (let e = el; e; e = e.parentElement) {
        const t = getComputedStyle(e).transform;
        if (t && t !== 'none') {
          const m = new DOMMatrix(t);
          scale *= Math.hypot(m.a, m.b) || 1;
        }
      }
    }
    // The colour actually painted: -webkit-text-fill-color wins over color; SVG fill-opacity dims the
    // fill; gradient-clipped text has no single colour (reported as unmeasured, not guessed).
    let paint = el instanceof SVGElement ? cs.fill : cs.color;
    const tfc = cs.webkitTextFillColor;
    if (!(el instanceof SVGElement) && tfc && tfc !== cs.color) paint = tfc;
    if ((cs.backgroundClip || cs.webkitBackgroundClip) === 'text') paint = 'gradient-clipped';
    const fillOpacity = el instanceof SVGElement ? parseFloat(cs.fillOpacity || '1') : 1;
    const cssSize = parseFloat(cs.fontSize);
    const font = { size: +(cssSize * scale).toFixed(2), cssSize, family: cs.fontFamily, weight: parseInt(cs.fontWeight, 10) || 400, style: cs.fontStyle };
    const key = `${font.family}|${font.weight}|${font.style}`;
    const k = samples.get(key) || 0;
    if (k < 2 && !el.hasAttribute('data-pcv-fid')) {
      el.setAttribute('data-pcv-fid', String(fid));
      fontSamples.push({ fid: fid++, family: font.family, weight: font.weight, style: font.style, text: raw.trim().slice(0, 40) });
      samples.set(key, k + 1);
    }
    texts.push({
      text: raw.replace(/\s+/g, ' ').trim(), path: pathOf(el), block: blockId(blockOf(el)), rects, font,
      color: paint, opacity: opacityOf(el) * fillOpacity, clips: clipsOf(el),
      flags: {
        title: !!(opts.titleSelector && el.closest(opts.titleSelector)),
        source: !!(opts.sourceSelector && el.closest(opts.sourceSelector)),
        nocheck: !!(opts.nocheckSelector && el.closest(opts.nocheckSelector)),
        overlap: allow(el, 'overlap'), small: allow(el, 'small'), bleed: allow(el, 'bleed'),
        contrast: allow(el, 'contrast'), spelling: allow(el, 'spelling'), svg: el instanceof SVGElement,
      },
    });
  }

  const graphics = [];
  root.querySelectorAll('img, svg, canvas, video, [data-pcv-graphic]').forEach((g) => {
    if (g instanceof SVGElement && g.ownerSVGElement) return;
    if (!visible(g)) return;
    const cs = getComputedStyle(g);
    const o = {
      path: pathOf(g), kind: g.tagName.toLowerCase(), rect: r2(g.getBoundingClientRect()),
      decor: allow(g, 'decor') || g.getAttribute('aria-hidden') === 'true', bleed: allow(g, 'bleed'), overlap: allow(g, 'overlap'),
    };
    if (g.tagName === 'IMG') {
      const src = g.currentSrc || g.getAttribute('src') || '';
      Object.assign(o, {
        src, complete: g.complete, natural: [g.naturalWidth, g.naturalHeight], objectFit: cs.objectFit,
        vector: /\.svg(\?|#|$)/i.test(src) || /^data:image\/svg/i.test(src),
      });
    }
    graphics.push(o);
  });

  const titles = Array.from(root.querySelectorAll(opts.titleSelector || 'h1')).filter(visible).map((t) => {
    const cs = getComputedStyle(t);
    const fs = parseFloat(cs.fontSize);
    const tops = [];
    const walker = document.createTreeWalker(t, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (!n.nodeValue.trim()) continue;
      const r = document.createRange();
      r.selectNodeContents(n);
      for (const x of r.getClientRects()) {
        if (x.width < 0.5) continue;
        if (!tops.some((y) => Math.abs(y - x.top) < fs * 0.5)) tops.push(x.top);
      }
    }
    return {
      path: pathOf(t), text: t.textContent.replace(/\s+/g, ' ').trim(), rect: r2(t.getBoundingClientRect()),
      lines: tops.length, fontSize: fs, family: cs.fontFamily, weight: cs.fontWeight,
    };
  });

  const charts = Array.from(root.querySelectorAll('[data-pcv-chart]')).map((e) => {
    let spec;
    try { spec = JSON.parse(e.getAttribute('data-pcv-chart')); } catch (err) { spec = { error: String(err) }; }
    return { path: pathOf(e), spec, labels: Array.from(e.querySelectorAll('text, [data-pcv-label]')).map((t) => t.textContent.trim()) };
  });

  return {
    root: r2(root.getBoundingClientRect()),
    viewport: [innerWidth, innerHeight, devicePixelRatio],
    texts,
    blocks: blockList,
    graphics,
    titles,
    refs: Array.from(root.querySelectorAll('[data-ref]')).map((e) => e.getAttribute('data-ref')),
    charts,
    faces: Array.from(document.fonts).map((f) => ({ family: f.family.replace(/^["']|["']$/g, ''), status: f.status, weight: f.weight, style: f.style })),
    fontSamples,
    slideText: root.innerText,
  };
}

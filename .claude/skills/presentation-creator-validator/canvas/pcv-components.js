/* pcv-components.js: slide components for presentation-creator-validator.
 *
 * Plain browser JavaScript, no dependencies, no build step. Load after pcv.css:
 *   <link rel="stylesheet" href="/__pcv__/pcv.css">
 *   <script src="/__pcv__/pcv-components.js"></script>
 *
 * API (window.PCV):
 *   ready(promise?)        add a promise the renderer must wait for; returns window.PCV_READY
 *   barChart(host, spec)   horizontal (default) or vertical bars, zero baseline, direct value labels
 *   lineChart(host, spec)  lines with direct end labels, no legend box
 *   flow(host, spec)       HTML nodes joined by orthogonal SVG connectors with arrowheads
 *   timeline(host, spec)   horizontal milestones on one axis
 *   table(host, spec)      ruled table, numeric columns right-aligned with tabular figures
 *   fitText(el, opts)      shrink font size until el fits its own box, never below opts.min
 *
 * Every component draws synchronously, then redraws once the page's web fonts have loaded so
 * that text measurement uses the real faces. window.PCV_READY resolves after that final pass;
 * the renderer awaits it. Output depends only on the spec and the fonts: no randomness, no clock.
 * Charts set data-pcv-chart = {"type", "yMin", "valueLabels"} where valueLabels are the exact
 * value strings drawn, so the validator can check the drawing against the data.
 */
(function () {
  'use strict';

  const SVG_NS = 'http://www.w3.org/2000/svg';
  const draws = [];
  const waits = [];
  let resolveReady;
  const READY = new Promise((r) => { resolveReady = r; });
  window.PCV_READY = READY;

  /* ---------- lifecycle ---------- */

  function register(draw) {
    draws.push(draw);
    draw();
  }

  function fontSignature() {
    return Array.from(document.fonts).map((f) => f.status).join(',');
  }

  async function settle() {
    try {
      for (let pass = 0; pass < 4; pass++) {
        await document.fonts.ready;
        if (waits.length) await Promise.allSettled(waits.slice());
        const before = fontSignature();
        const n = draws.length;
        draws.slice().forEach((d) => d());
        await document.fonts.ready;
        if (fontSignature() === before && draws.length === n) break;
      }
    } catch (err) {
      console.error('PCV: settle failed', err);
    }
    resolveReady();
  }

  if (document.readyState === 'complete') settle();
  else window.addEventListener('load', settle, { once: true });

  function ready(promise) {
    if (promise && typeof promise.then === 'function') waits.push(Promise.resolve(promise).catch(() => null));
    return READY;
  }

  /* ---------- helpers ---------- */

  function svgEl(tag, attrs, parent) {
    const e = document.createElementNS(SVG_NS, tag);
    if (attrs) for (const k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }

  function htmlEl(tag, cls, parent, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = String(text);
    if (parent) parent.appendChild(e);
    return e;
  }

  function clean(x) {
    return +(+x).toPrecision(12);
  }

  function niceStep(range, target) {
    if (!(range > 0)) return 1;
    const raw = range / (target || 5);
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    const f = raw / p;
    const n = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10;
    return clean(n * p);
  }

  function niceCeil(v, target) {
    if (v <= 0) return 0;
    const s = niceStep(v, target || 5);
    return clean(Math.ceil(v / s - 1e-9) * s);
  }

  function niceFloor(v, target) {
    if (v >= 0) return 0;
    return -niceCeil(-v, target);
  }

  function decimalsOf(step) {
    const s = String(clean(step));
    return s.includes('e-') ? +s.split('e-')[1] : (s.split('.')[1] || '').length;
  }

  const fmtCache = new Map();
  function fmt(v, digits, unit) {
    const d = Math.max(0, Math.min(20, digits | 0));
    if (!fmtCache.has(d)) {
      fmtCache.set(d, new Intl.NumberFormat('en-US', { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: true }));
    }
    let s = fmtCache.get(d).format(Math.abs(v));
    const zero = /^[0.,]+$/.test(s);
    if (v < 0 && !zero) s = '−' + s;
    return s + (unit || '');
  }

  function boxOf(host, spec) {
    const r = host.getBoundingClientRect();
    const w = Math.round(spec.width || r.width || host.clientWidth || 960);
    const h = Math.round(spec.height || r.height || host.clientHeight || 540);
    return [w, h];
  }

  /* A colour option: explicit value from spec.colors, else a theme custom property. */
  function palette(spec) {
    const c = spec.colors || {};
    return {
      bar: c.bar || 'var(--pcv-ink-2)',
      muted: c.muted || 'var(--pcv-mark)',
      emphasis: c.emphasis || 'var(--pcv-accent)',
      text: c.text || 'var(--pcv-ink)',
      text2: c.text2 || 'var(--pcv-ink-2)',
      text3: c.text3 || 'var(--pcv-ink-3)',
      rule: c.rule || 'var(--pcv-rule)',
      axis: c.axis || 'var(--pcv-ink)',
      bg: c.bg || 'var(--pcv-bg)',
    };
  }

  /* Text measurement inside the chart's own SVG, so the chart's fonts and features apply. */
  function measurer(svg) {
    const t = svgEl('text', { x: 0, y: -10000, 'aria-hidden': 'true' }, svg);
    return {
      width(text, size, weight) {
        t.style.fontSize = size + 'px';
        t.style.fontWeight = String(weight || 400);
        t.textContent = text;
        return t.getComputedTextLength();
      },
      done() { t.remove(); },
    };
  }

  /* Greedy word wrap to maxW; shrinks the size (never below minSize) until it fits maxLines. */
  function wrapFit(m, text, maxW, size, weight, maxLines, minSize) {
    const words = String(text).split(/\s+/).filter(Boolean);
    for (let s = size; s >= minSize; s--) {
      const lines = [];
      let cur = '';
      for (const w of words) {
        const next = cur ? cur + ' ' + w : w;
        if (!cur || m.width(next, s, weight) <= maxW) cur = next;
        else { lines.push(cur); cur = w; }
      }
      if (cur) lines.push(cur);
      const widest = Math.max(0, ...lines.map((l) => m.width(l, s, weight)));
      if (lines.length <= maxLines && widest <= maxW + 0.5) return { lines, size: s, width: widest };
      if (s === minSize) return { lines, size: s, width: widest };
    }
    return { lines: [String(text)], size: minSize, width: m.width(String(text), minSize, weight) };
  }

  /* Multi-line SVG text centred vertically on cy. anchor: start | middle | end. */
  function textBlock(parent, lines, x, cy, size, opts) {
    const lh = Math.round(size * 1.2);
    const first = Math.round(cy - ((lines.length - 1) * lh) / 2 + size * 0.36);
    const t = svgEl('text', { x, y: first, 'text-anchor': opts.anchor || 'start' }, parent);
    t.style.fontSize = size + 'px';
    t.style.fontWeight = String(opts.weight || 400);
    t.style.fill = opts.fill;
    if (lines.length === 1) t.textContent = lines[0];
    else lines.forEach((l, i) => { const s = svgEl('tspan', { x, y: first + i * lh }, t); s.textContent = l; });
    return t;
  }

  function prepHost(host, kind, spec) {
    if (!host || !host.nodeType) throw new Error(`PCV.${kind}: host element not found`);
    host.textContent = '';
    host.classList.add('pcv-chart');
    host.setAttribute('role', 'img');
    if (spec.ariaLabel) host.setAttribute('aria-label', spec.ariaLabel);
  }

  /* ---------- barChart ---------- */

  function barChart(host, spec) {
    spec = spec || {};
    register(() => drawBars(host, spec));
    return host;
  }

  function drawBars(host, spec) {
    prepHost(host, 'barChart', spec);
    const data = (spec.data || []).map((d) => ({ label: String(d.label), value: +d.value, emphasis: !!d.emphasis }));
    const vertical = spec.orientation === 'vertical';
    const digits = spec.digits === undefined ? 3 : spec.digits;
    const unit = spec.unit || '';
    const fs = spec.fontSize || 24;
    const vals = data.map((d) => d.value);
    const dmin = Math.min(0, ...vals);
    const dmax = Math.max(0, ...vals);
    const min = spec.min !== undefined ? +spec.min : (dmin < 0 ? niceFloor(dmin) : 0);
    const max = spec.max !== undefined ? +spec.max : Math.max(niceCeil(dmax), min + niceStep(dmax - min || 1));
    const [W, H] = boxOf(host, spec);
    const col = palette(spec);
    const anyEmph = data.some((d) => d.emphasis);
    const labels = data.map((d) => fmt(d.value, digits, unit));

    host.style.width = W + 'px';
    host.style.height = H + 'px';
    const svg = svgEl('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}` }, host);
    const m = measurer(svg);
    const barFill = (d) => (anyEmph ? (d.emphasis ? col.emphasis : col.muted) : col.bar);
    const span = max - min || 1;
    const valW = Math.ceil(Math.max(0, ...data.map((d, i) => m.width(labels[i], fs, d.emphasis ? 600 : 500))));
    const gap = 14;

    if (!vertical) {
      const n = Math.max(1, data.length);
      const rowH = Math.floor(H / n);
      const barH = Math.max(12, Math.min(64, Math.round(rowH * 0.56)));
      const natural = Math.ceil(Math.max(0, ...data.map((d) => m.width(d.label, fs, d.emphasis ? 600 : 400))));
      const labelMax = Math.round(W * 0.36);
      const fitted = data.map((d) => (natural <= labelMax
        ? { lines: [d.label], size: fs }
        : wrapFit(m, d.label, labelMax, fs, d.emphasis ? 600 : 400, rowH >= fs * 2.6 ? 2 : 1, 20)));
      const labelW = natural <= labelMax ? natural : labelMax;
      const x0 = labelW + 28;
      const leftRoom = vals.some((v) => v < 0) ? valW + gap : 0;
      const plot = W - x0 - leftRoom - valW - gap;
      const sx = (v) => x0 + leftRoom + ((Math.max(min, Math.min(max, v)) - min) / span) * plot;
      const xz = Math.round(sx(Math.max(min, 0)));
      const g = svgEl('g', null, svg);
      data.forEach((d, i) => {
        const top = i * rowH;
        const cy = top + rowH / 2;
        const y = Math.round(cy - barH / 2);
        const xv = Math.round(sx(d.value));
        const x = Math.min(xz, xv);
        const w = Math.abs(xv - xz);
        const r = svgEl('rect', { x, y, width: Math.max(w, 0), height: barH }, g);
        r.style.fill = barFill(d);
        textBlock(g, fitted[i].lines, labelW, cy, fitted[i].size,
          { anchor: 'end', weight: d.emphasis ? 600 : 400, fill: d.emphasis || !anyEmph ? col.text : col.text2 });
        const neg = d.value < 0;
        const t = textBlock(g, [labels[i]], neg ? x - gap : x + w + gap, cy, fs,
          { anchor: neg ? 'end' : 'start', weight: d.emphasis ? 600 : 500, fill: d.emphasis ? col.emphasis : col.text });
        t.setAttribute('data-pcv-label', '');
      });
      const axis = svgEl('line', { x1: xz, x2: xz, y1: 0, y2: n * rowH }, svg);
      axis.style.stroke = col.axis;
      axis.style.strokeWidth = '2px';
    } else {
      const n = Math.max(1, data.length);
      const colW = Math.floor(W / n);
      const barW = Math.max(16, Math.min(160, Math.round(colW * 0.56)));
      const fitted = data.map((d) => wrapFit(m, d.label, colW - 12, fs, d.emphasis ? 600 : 400, 2, 20));
      const lines = Math.max(1, ...fitted.map((f) => f.lines.length));
      const labelH = Math.round(lines * fs * 1.2) + 20;
      const topRoom = fs + 16;
      const negRoom = vals.some((v) => v < 0) ? fs + 16 : 0;
      const plot = H - labelH - topRoom - negRoom;
      const sy = (v) => topRoom + plot - ((Math.max(min, Math.min(max, v)) - min) / span) * plot;
      const yz = Math.round(sy(Math.max(min, 0)));
      const g = svgEl('g', null, svg);
      data.forEach((d, i) => {
        const cx = Math.round(i * colW + colW / 2);
        const yv = Math.round(sy(d.value));
        const y = Math.min(yz, yv);
        const h = Math.abs(yv - yz);
        const r = svgEl('rect', { x: Math.round(cx - barW / 2), y, width: barW, height: Math.max(h, 0) }, g);
        r.style.fill = barFill(d);
        const neg = d.value < 0;
        const vy = neg ? y + h + 10 + fs * 0.5 : y - 10 - fs * 0.5;
        const t = textBlock(g, [labels[i]], cx, vy, fs,
          { anchor: 'middle', weight: d.emphasis ? 600 : 500, fill: d.emphasis ? col.emphasis : col.text });
        t.setAttribute('data-pcv-label', '');
        const f = fitted[i];
        const ly = H - labelH + 20 + (f.lines.length * Math.round(f.size * 1.2)) / 2;
        textBlock(g, f.lines, cx, ly - 6, f.size,
          { anchor: 'middle', weight: d.emphasis ? 600 : 400, fill: d.emphasis || !anyEmph ? col.text : col.text2 });
      });
      const axis = svgEl('line', { x1: 0, x2: n * colW, y1: yz, y2: yz }, svg);
      axis.style.stroke = col.axis;
      axis.style.strokeWidth = '2px';
    }
    m.done();
    // yMin is the value the bars grow from: 0 unless spec.min/max push the baseline off zero,
    // which is exactly the truncation the validator flags.
    const baseline = Math.max(min, Math.min(max, 0));
    host.setAttribute('data-pcv-chart', JSON.stringify({ type: 'bar', yMin: baseline, axisMin: min, axisMax: max, valueLabels: labels }));
  }

  /* ---------- lineChart ---------- */

  function lineChart(host, spec) {
    spec = spec || {};
    register(() => drawLines(host, spec));
    return host;
  }

  function drawLines(host, spec) {
    prepHost(host, 'lineChart', spec);
    const series = (spec.series || []).map((s) => ({
      name: String(s.name),
      points: (s.points || []).map((p) => [+p[0], +p[1]]).sort((a, b) => a[0] - b[0]),
      emphasis: !!s.emphasis,
    }));
    const digits = spec.digits === undefined ? 3 : spec.digits;
    const unit = spec.unit || '';
    const fs = spec.fontSize || 24;
    const tickFs = Math.max(20, fs - 2);
    const [W, H] = boxOf(host, spec);
    const col = palette(spec);
    const ys = series.flatMap((s) => s.points.map((p) => p[1]));
    const xsAll = Array.from(new Set(series.flatMap((s) => s.points.map((p) => p[0])))).sort((a, b) => a - b);
    const dmin = ys.length ? Math.min(...ys) : 0;
    const dmax = ys.length ? Math.max(...ys) : 1;
    const pad = (dmax - dmin) * 0.08 || Math.abs(dmax) * 0.1 || 1;
    const step0 = niceStep(dmax - dmin + 2 * pad, 4);
    const min = spec.min !== undefined ? +spec.min : clean(Math.floor((dmin - pad) / step0) * step0);
    const max = spec.max !== undefined ? +spec.max : clean(Math.ceil((dmax + pad) / step0) * step0);
    const step = niceStep(max - min, 4);
    const ticks = [];
    for (let v = Math.ceil(min / step - 1e-9) * step; v <= max + step * 1e-6; v += step) ticks.push(clean(v));
    const tickDigits = Math.max(0, decimalsOf(step));
    const anyEmph = series.some((s) => s.emphasis);
    const cycle = [col.text2, 'var(--pcv-accent-2)', col.text3];
    const styleOf = (s, i) => {
      if (anyEmph) return s.emphasis ? { line: col.emphasis, text: col.emphasis, width: 4 } : { line: col.muted, text: col.text3, width: 3 };
      const c = cycle[i % cycle.length];
      return { line: c, text: c, width: 3 };
    };

    host.style.width = W + 'px';
    host.style.height = H + 'px';
    const svg = svgEl('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}` }, host);
    const m = measurer(svg);
    const tickLabels = ticks.map((t) => fmt(t, tickDigits, ''));
    const ends = series.map((s) => (s.points.length ? s.points[s.points.length - 1] : null));
    const endVals = ends.map((p) => (p ? fmt(p[1], digits, unit) : ''));
    const tickW = Math.ceil(Math.max(0, ...tickLabels.map((t) => m.width(t, tickFs, 400))));
    const endW = Math.ceil(Math.max(0, ...series.map((s, i) => m.width(endVals[i], fs, 600) + 10 + m.width(s.name, fs, s.emphasis ? 600 : 400))));
    const left = tickW + 20;
    const right = W - endW - 24;
    const top = Math.ceil(fs * 0.7);
    const bottom = H - (fs + 22);
    const xmin = xsAll[0] !== undefined ? xsAll[0] : 0;
    const xmax = xsAll.length > 1 ? xsAll[xsAll.length - 1] : xmin + 1;
    const sx = (x) => left + ((x - xmin) / (xmax - xmin)) * (right - left);
    const sy = (y) => bottom - ((y - min) / (max - min || 1)) * (bottom - top);

    const grid = svgEl('g', null, svg);
    // Axis scale labels are not data claims; keep them out of the number-provenance check.
    grid.setAttribute('data-pcv-nocheck', '');
    ticks.forEach((t, i) => {
      const y = Math.round(sy(t));
      const isBase = i === 0 && Math.abs(t - min) < 1e-9;
      if (!isBase) {
        const l = svgEl('line', { x1: left, x2: right, y1: y, y2: y }, grid);
        l.style.stroke = col.rule;
        l.style.strokeWidth = '1px';
      }
      textBlock(grid, [tickLabels[i]], left - 20, y, tickFs, { anchor: 'end', fill: col.text3 });
    });
    const base = svgEl('line', { x1: left, x2: right, y1: Math.round(bottom), y2: Math.round(bottom) }, grid);
    base.style.stroke = col.axis;
    base.style.strokeWidth = '2px';

    let xl = spec.xLabels;
    let xlPairs;
    if (Array.isArray(xl) && xl.length && Array.isArray(xl[0])) xlPairs = xl.map((p) => [+p[0], String(p[1])]);
    else if (Array.isArray(xl) && xl.length) xlPairs = xsAll.slice(0, xl.length).map((x, i) => [x, String(xl[i])]);
    // Default x labels are positions (often years): no thousands separator, so 2024 is not "2,024".
    else xlPairs = xsAll.map((x) => [x, String(x)]);
    xlPairs.forEach(([x, label], i) => {
      const anchor = i === 0 && Math.abs(sx(x) - left) < 1 ? 'start' : 'middle';
      textBlock(grid, [label], Math.round(sx(x)), Math.round(H - fs * 0.6), tickFs, { anchor, fill: col.text3 });
    });

    const marks = svgEl('g', null, svg);
    const order = series.map((s, i) => i).sort((a, b) => (series[a].emphasis ? 1 : 0) - (series[b].emphasis ? 1 : 0));
    order.forEach((i) => {
      const s = series[i];
      if (!s.points.length) return;
      const st = styleOf(s, i);
      const pts = s.points.map((p) => `${Math.round(sx(p[0]) * 2) / 2},${Math.round(sy(p[1]) * 2) / 2}`).join(' ');
      const pl = svgEl('polyline', { points: pts, fill: 'none', 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, marks);
      pl.style.stroke = st.line;
      pl.style.strokeWidth = st.width + 'px';
      const dots = s.emphasis ? s.points : [s.points[s.points.length - 1]];
      dots.forEach((p) => {
        const c = svgEl('circle', { cx: Math.round(sx(p[0])), cy: Math.round(sy(p[1])), r: s.emphasis ? 6 : 5 }, marks);
        c.style.fill = st.line;
        c.style.stroke = col.bg;
        c.style.strokeWidth = '3px';
      });
    });

    // End labels: start at each series' last value, then push apart so none collide.
    const lh = Math.round(fs * 1.25);
    const items = series.map((s, i) => ({ i, y: ends[i] ? sy(ends[i][1]) : null })).filter((o) => o.y !== null).sort((a, b) => a.y - b.y);
    for (let k = 1; k < items.length; k++) if (items[k].y - items[k - 1].y < lh) items[k].y = items[k - 1].y + lh;
    const maxY = bottom - fs * 0.2;
    if (items.length && items[items.length - 1].y > maxY) {
      items[items.length - 1].y = maxY;
      for (let k = items.length - 2; k >= 0; k--) if (items[k + 1].y - items[k].y < lh) items[k].y = items[k + 1].y - lh;
    }
    const lab = svgEl('g', null, svg);
    items.forEach((o) => {
      const s = series[o.i];
      const st = styleOf(s, o.i);
      const x = Math.round(right + 20);
      const y = Math.round(o.y);
      const v = textBlock(lab, [endVals[o.i]], x, y, fs, { anchor: 'start', weight: 600, fill: st.text });
      v.setAttribute('data-pcv-label', '');
      const vw = Math.ceil(m.width(endVals[o.i], fs, 600));
      textBlock(lab, [s.name], x + vw + 10, y, fs, { anchor: 'start', weight: s.emphasis ? 600 : 400, fill: st.text });
    });
    m.done();
    host.setAttribute('data-pcv-chart', JSON.stringify({ type: 'line', yMin: min, valueLabels: endVals.filter(Boolean) }));
  }

  /* ---------- flow ---------- */

  function flow(host, spec) {
    spec = spec || {};
    register(() => drawFlow(host, spec));
    return host;
  }

  const NORMAL = { left: [-1, 0], right: [1, 0], top: [0, -1], bottom: [0, 1] };

  function overlap(a0, a1, b0, b1) {
    return Math.min(a1, b1) - Math.max(a0, b0);
  }

  function autoSides(a, b) {
    const ox = overlap(a.x, a.x + a.w, b.x, b.x + b.w);
    const oy = overlap(a.y, a.y + a.h, b.y, b.y + b.h);
    const dx = b.x + b.w / 2 - (a.x + a.w / 2);
    const dy = b.y + b.h / 2 - (a.y + a.h / 2);
    if (ox > 0 && oy <= 0) return dy > 0 ? ['bottom', 'top'] : ['top', 'bottom'];
    if (oy > 0 && ox <= 0) return dx > 0 ? ['right', 'left'] : ['left', 'right'];
    if (Math.abs(dx) >= Math.abs(dy)) return dx > 0 ? ['right', 'left'] : ['left', 'right'];
    return dy > 0 ? ['bottom', 'top'] : ['top', 'bottom'];
  }

  function anchorOf(n, side, along) {
    if (side === 'left') return [n.x, along !== undefined ? along : n.y + n.h / 2];
    if (side === 'right') return [n.x + n.w, along !== undefined ? along : n.y + n.h / 2];
    if (side === 'top') return [along !== undefined ? along : n.x + n.w / 2, n.y];
    return [along !== undefined ? along : n.x + n.w / 2, n.y + n.h];
  }

  function route(a, b, s1, s2) {
    const h1 = s1 === 'left' || s1 === 'right';
    const h2 = s2 === 'left' || s2 === 'right';
    let p1, p2;
    if (h1 && h2) {
      const oy = overlap(a.y, a.y + a.h, b.y, b.y + b.h);
      const y = oy > 24 ? Math.max(a.y, b.y) + oy / 2 : undefined;
      p1 = anchorOf(a, s1, y); p2 = anchorOf(b, s2, y);
    } else if (!h1 && !h2) {
      const ox = overlap(a.x, a.x + a.w, b.x, b.x + b.w);
      const x = ox > 24 ? Math.max(a.x, b.x) + ox / 2 : undefined;
      p1 = anchorOf(a, s1, x); p2 = anchorOf(b, s2, x);
    } else {
      p1 = anchorOf(a, s1); p2 = anchorOf(b, s2);
    }
    p1 = p1.map(Math.round); p2 = p2.map(Math.round);
    const [n1x, n1y] = NORMAL[s1];
    const [n2x, n2y] = NORMAL[s2];
    const out = 32;
    let pts;
    if (h1 && h2) {
      const facing = (p2[0] - p1[0]) * n1x > 0 && (p1[0] - p2[0]) * n2x > 0;
      if (p1[1] === p2[1] && facing) pts = [p1, p2];
      else if (facing) { const mx = Math.round((p1[0] + p2[0]) / 2); pts = [p1, [mx, p1[1]], [mx, p2[1]], p2]; }
      else if (n1x === n2x) { const x = n1x > 0 ? Math.max(p1[0], p2[0]) + out : Math.min(p1[0], p2[0]) - out; pts = [p1, [x, p1[1]], [x, p2[1]], p2]; }
      else {
        const my = Math.round(Math.max(a.y + a.h, b.y + b.h) + out);
        pts = [p1, [p1[0] + n1x * out, p1[1]], [p1[0] + n1x * out, my], [p2[0] + n2x * out, my], [p2[0] + n2x * out, p2[1]], p2];
      }
    } else if (!h1 && !h2) {
      const facing = (p2[1] - p1[1]) * n1y > 0 && (p1[1] - p2[1]) * n2y > 0;
      if (p1[0] === p2[0] && facing) pts = [p1, p2];
      else if (facing) { const my = Math.round((p1[1] + p2[1]) / 2); pts = [p1, [p1[0], my], [p2[0], my], p2]; }
      else if (n1y === n2y) { const y = n1y > 0 ? Math.max(p1[1], p2[1]) + out : Math.min(p1[1], p2[1]) - out; pts = [p1, [p1[0], y], [p2[0], y], p2]; }
      else {
        const mx = Math.round(Math.max(a.x + a.w, b.x + b.w) + out);
        pts = [p1, [p1[0], p1[1] + n1y * out], [mx, p1[1] + n1y * out], [mx, p2[1] + n2y * out], [p2[0], p2[1] + n2y * out], p2];
      }
    } else if (h1) {
      pts = [p1, [p2[0], p1[1]], p2];
    } else {
      pts = [p1, [p1[0], p2[1]], p2];
    }
    return { pts: pts.filter((p, i) => i === 0 || p[0] !== pts[i - 1][0] || p[1] !== pts[i - 1][1]), end: [-n2x, -n2y] };
  }

  function drawFlow(host, spec) {
    if (!host || !host.nodeType) throw new Error('PCV.flow: host element not found');
    const [W, H] = boxOf(host, spec);
    host.textContent = '';
    host.classList.add('pcv-flow');
    host.style.width = W + 'px';
    host.style.height = H + 'px';
    if (spec.ariaLabel) { host.setAttribute('role', 'img'); host.setAttribute('aria-label', spec.ariaLabel); }
    const nodes = new Map();
    (spec.nodes || []).forEach((n) => nodes.set(String(n.id), { x: Math.round(n.x), y: Math.round(n.y), w: Math.round(n.w), h: Math.round(n.h), src: n }));
    const svg = svgEl('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, 'aria-hidden': 'true' }, host);
    const AL = 14, AW = 7;
    const labelJobs = [];
    (spec.edges || []).forEach((e) => {
      const a = nodes.get(String(e.from));
      const b = nodes.get(String(e.to));
      if (!a || !b) { console.warn(`PCV.flow: edge ${e.from} -> ${e.to} names a missing node`); return; }
      const [s1a, s2a] = autoSides(a, b);
      const r = route(a, b, e.fromSide || s1a, e.toSide || s2a);
      const pts = r.pts.map((p) => p.slice());
      const last = pts[pts.length - 1];
      const [ex, ey] = r.end;
      const tip = last.slice();
      last[0] -= ex * AL;
      last[1] -= ey * AL;
      const tone = e.tone === 'accent' ? 'var(--pcv-accent)' : 'var(--pcv-ink-2)';
      const path = svgEl('path', { d: 'M' + pts.map((p) => p.join(' ')).join(' L'), fill: 'none', 'stroke-linejoin': 'miter' }, svg);
      path.style.stroke = tone;
      path.style.strokeWidth = '2px';
      const px = -ey, py = ex;
      const head = svgEl('polygon', {
        points: [tip, [last[0] + px * AW, last[1] + py * AW], [last[0] - px * AW, last[1] - py * AW]].map((p) => p.join(',')).join(' '),
      }, svg);
      head.style.fill = tone;
      if (e.label) {
        let best = 0, bi = 0;
        for (let i = 1; i < r.pts.length; i++) {
          const len = Math.abs(r.pts[i][0] - r.pts[i - 1][0]) + Math.abs(r.pts[i][1] - r.pts[i - 1][1]);
          if (len > best) { best = len; bi = i; }
        }
        const p = r.pts[bi - 1], q = r.pts[bi];
        labelJobs.push({ text: e.label, x: (p[0] + q[0]) / 2, y: (p[1] + q[1]) / 2 });
      }
    });
    nodes.forEach((n) => {
      const d = htmlEl('div', 'pcv-flow-node', host);
      const tone = n.src.tone === 'accent' || n.src.tone === 'muted' ? n.src.tone : 'default';
      d.setAttribute('data-tone', tone);
      d.setAttribute('data-node', String(n.src.id));
      Object.assign(d.style, { left: n.x + 'px', top: n.y + 'px', width: n.w + 'px', height: n.h + 'px' });
      if (n.src.align === 'center') d.style.textAlign = 'center';
      htmlEl('div', 'pcv-flow-title', d, n.src.title);
      if (n.src.body) htmlEl('div', 'pcv-flow-body', d, n.src.body);
      fitBox(d, 20);
    });
    labelJobs.forEach((j) => {
      const l = htmlEl('div', 'pcv-flow-label', host, j.text);
      const w = l.offsetWidth, h = l.offsetHeight;
      l.style.left = Math.round(j.x - w / 2) + 'px';
      l.style.top = Math.round(j.y - h / 2) + 'px';
    });
  }

  /* Shrink every text child of a fixed-size box together until the box no longer overflows. */
  function fitBox(box, min) {
    const kids = Array.from(box.children);
    const base = kids.map((k) => parseFloat(getComputedStyle(k).fontSize));
    const fits = () => box.scrollHeight <= box.clientHeight + 0.5 && box.scrollWidth <= box.clientWidth + 0.5;
    for (let f = 1; !fits() && f > 0.5; f -= 0.04) {
      kids.forEach((k, i) => { k.style.fontSize = Math.max(min, Math.floor(base[i] * f)) + 'px'; });
      if (kids.every((k) => parseFloat(k.style.fontSize) <= min)) break;
    }
    if (!fits()) warnOnce(box, `PCV.flow: node "${box.getAttribute('data-node')}" overflows at the ${min}px minimum; enlarge it or cut text`);
  }

  const warned = new Set();
  function warnOnce(el, msg) {
    const key = msg;
    if (warned.has(key)) return;
    warned.add(key);
    console.warn(msg);
  }

  /* ---------- timeline ---------- */

  function timeline(host, spec) {
    spec = spec || {};
    register(() => drawTimeline(host, spec));
    return host;
  }

  function drawTimeline(host, spec) {
    if (!host || !host.nodeType) throw new Error('PCV.timeline: host element not found');
    host.textContent = '';
    host.classList.add('pcv-timeline');
    if (spec.width) host.style.width = Math.round(spec.width) + 'px';
    (spec.items || []).forEach((it) => {
      const d = htmlEl('div', 'pcv-tl-item', host);
      if (it.emphasis) d.setAttribute('data-emphasis', '');
      htmlEl('div', 'pcv-tl-when', d, it.when);
      htmlEl('div', 'pcv-tl-mark', d).setAttribute('aria-hidden', 'true');
      htmlEl('div', 'pcv-tl-title', d, it.title);
      if (it.body) htmlEl('div', 'pcv-tl-body', d, it.body);
    });
  }

  /* ---------- table ---------- */

  function table(host, spec) {
    spec = spec || {};
    register(() => drawTable(host, spec));
    return host;
  }

  function drawTable(host, spec) {
    if (!host || !host.nodeType) throw new Error('PCV.table: host element not found');
    host.textContent = '';
    const digits = spec.digits === undefined ? 3 : spec.digits;
    const cols = (spec.columns || []).map((c) => (typeof c === 'string' ? { label: c } : c));
    const t = htmlEl('table', 'pcv-table', host);
    const hr = htmlEl('tr', null, htmlEl('thead', null, t));
    cols.forEach((c) => {
      const th = htmlEl('th', null, hr, c.label);
      th.setAttribute('scope', 'col');
      const align = c.align || (c.numeric ? 'right' : 'left');
      if (align !== 'left') th.setAttribute('data-align', align);
    });
    const tb = htmlEl('tbody', null, t);
    (spec.rows || []).forEach((row, ri) => {
      const tr = htmlEl('tr', null, tb);
      if (spec.emphasisRow === ri) tr.setAttribute('data-emphasis', '');
      row.forEach((cell, ci) => {
        const c = cols[ci] || {};
        const obj = cell !== null && typeof cell === 'object' ? cell : { value: cell };
        const v = obj.value;
        const text = typeof v === 'number' ? fmt(v, c.digits !== undefined ? c.digits : digits, c.unit || '') : (v === null || v === undefined ? '' : String(v));
        const td = htmlEl('td', null, tr, text);
        const align = c.align || (c.numeric ? 'right' : 'left');
        if (align !== 'left') td.setAttribute('data-align', align);
        if (c.numeric) td.setAttribute('data-numeric', '');
        if (obj.emphasis) td.setAttribute('data-emphasis', '');
      });
    });
    // Freeze the auto layout to whole-pixel column widths so rules and row tints have no seams.
    const ths = Array.from(hr.children);
    const total = Math.round(t.getBoundingClientRect().width);
    if (total > 0 && ths.length) {
      const ws = ths.map((th) => Math.floor(th.getBoundingClientRect().width));
      ws[0] += total - ws.reduce((a, b) => a + b, 0);
      const cg = document.createElement('colgroup');
      ws.forEach((w) => { const c = document.createElement('col'); c.style.width = w + 'px'; cg.appendChild(c); });
      t.insertBefore(cg, t.firstChild);
      t.style.tableLayout = 'fixed';
      t.style.width = total + 'px';
    }
  }

  /* ---------- fitText ---------- */

  function fitText(el, opts) {
    if (!el || !el.nodeType) throw new Error('PCV.fitText: element not found');
    opts = opts || {};
    const min = Math.max(1, Math.floor(opts.min || 20));
    el.style.fontSize = '';
    const max = Math.floor(opts.max || parseFloat(getComputedStyle(el).fontSize));
    const run = () => {
      const fits = () => el.scrollWidth <= el.clientWidth + 0.5 && el.scrollHeight <= el.clientHeight + 0.5;
      let lo = min, hi = max;
      el.style.fontSize = hi + 'px';
      if (fits()) return hi;
      while (lo < hi) {
        const mid = Math.ceil((lo + hi) / 2);
        el.style.fontSize = mid + 'px';
        if (fits()) lo = mid; else hi = mid - 1;
      }
      el.style.fontSize = lo + 'px';
      if (!fits()) warnOnce(el, `PCV.fitText: "${el.textContent.trim().slice(0, 40)}" still overflows at the ${min}px minimum`);
      return lo;
    };
    register(run);
    return parseFloat(el.style.fontSize);
  }

  window.PCV = Object.freeze({ ready, barChart, lineChart, flow, timeline, table, fitText, version: '1.0.0' });
})();

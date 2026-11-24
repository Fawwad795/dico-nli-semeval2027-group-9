"""Deterministic slide rendering: one HTML file per slide -> one exact-size image.

Slides load from a virtual origin (http://deck.local/) served from the deck folder, with the
skill's canvas library at /__pcv__/. Every other request is either served from a local cache
(allow-listed CDN and font hosts, fetched once; each file's sha256 is recorded in the slide's network
log) or blocked and logged, so a render needs no network after the first run and never silently
misses an asset. Clearing the cache refetches; compare the recorded hashes if that matters.

Chrome runs headed with its window parked off-screen (GPU rendering, no SwiftShader); pass
headless=True only where no display exists.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from .deckcfg import Deck
from .util import CANVAS_DIR, cache_dir, content_type, read_json, sha256_file, write_json

ORIGIN = "http://deck.local"
FREEZE_CSS = (
    "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}"
    "html,body{margin:0!important;padding:0!important;overflow:hidden!important}"
)
WAIT_READY_JS = """async (ms) => {
  const ready = (async () => {
    await document.fonts.ready;
    await Promise.all(Array.from(document.images).map(i => i.complete ? null : i.decode().catch(() => null)));
    if (window.PCV_READY && typeof window.PCV_READY.then === 'function') await window.PCV_READY;
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    await document.fonts.ready;
    return 'ready';
  })();
  return Promise.race([ready, new Promise(r => setTimeout(() => r('timeout'), ms))]);
}"""


def inject_style(html: str, css: str) -> str:
    """Insert CSS at the start of <head> (after <html> or the doctype if there is no head), never
    before the doctype, which would switch the page into quirks mode."""
    tag = f"<style data-pcv-injected>\n{css}\n</style>"
    for pat in (r"<head\b[^>]*>", r"<html\b[^>]*>", r"<!doctype[^>]*>"):
        m = re.search(pat, html, re.I)
        if m:
            return html[:m.end()] + tag + html[m.end():]
    return tag + html


class Router:
    def __init__(self, deck: Deck):
        self.deck = deck
        self.allow = set(deck.cfg["network"]["allow"])
        self.cache = cache_dir()
        self.log: list[dict] = []
        self.inject: dict[str, str] = {}  # slide path -> CSS placed in its <head> before any script runs

    def __call__(self, route):
        url = route.request.url
        if url.startswith(ORIGIN + "/"):
            return self._local(route, url)
        host = urllib.parse.urlsplit(url).hostname or ""
        if host in self.allow:
            return self._cached(route, url)
        self.log.append({"url": url, "result": "blocked"})
        return route.abort("blockedbyclient")

    def _local(self, route, url):
        path = urllib.parse.unquote(urllib.parse.urlsplit(url).path).lstrip("/")
        if path.startswith("__pcv__/"):
            base, rel = CANVAS_DIR, path[len("__pcv__/"):]
        else:
            base, rel = self.deck.dir, path
        base = base.resolve()
        f = (base / rel).resolve()
        if not f.is_relative_to(base) or not f.is_file():
            self.log.append({"url": url, "result": "missing"})
            return route.fulfill(status=404, body="not found")
        self.log.append({"url": url, "result": "local"})
        body = f.read_bytes()
        if path in self.inject:
            body = inject_style(body.decode("utf-8", errors="replace"), self.inject[path]).encode("utf-8")
        return route.fulfill(status=200, body=body,
                             headers={"content-type": content_type(f), "access-control-allow-origin": "*"})

    def _cached(self, route, url):
        key = hashlib.sha256(url.encode()).hexdigest()
        body_p, meta_p = self.cache / key, self.cache / f"{key}.json"
        if body_p.is_file() and meta_p.is_file():
            meta = read_json(meta_p)
            self.log.append({"url": url, "result": "cached", "sha256": meta["sha256"]})
            return route.fulfill(status=200, body=body_p.read_bytes(),
                                 headers={"content-type": meta["content_type"], "access-control-allow-origin": "*"})
        try:
            resp = route.fetch(timeout=30000)
        except Exception as e:  # network down on first use
            self.log.append({"url": url, "result": "fetch-failed", "error": str(e)[:200]})
            return route.abort("internetdisconnected")
        body = resp.body()
        if resp.ok:
            body_p.write_bytes(body)
            write_json(meta_p, {"url": url, "content_type": resp.headers.get("content-type", "application/octet-stream"),
                                "sha256": hashlib.sha256(body).hexdigest(),
                                "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            self.log.append({"url": url, "result": "fetched", "sha256": hashlib.sha256(body).hexdigest()})
        else:
            self.log.append({"url": url, "result": f"http-{resp.status}"})
        headers = dict(resp.headers)
        headers["access-control-allow-origin"] = "*"
        return route.fulfill(status=resp.status, body=body, headers=headers)


def _platform_fonts(context, page, samples: list[dict]) -> dict:
    out: dict = {}
    if not samples:
        return out
    cdp = context.new_cdp_session(page)
    try:
        cdp.send("DOM.enable")
        cdp.send("CSS.enable")
        root = cdp.send("DOM.getDocument", {"depth": 0})["root"]["nodeId"]
        for s in samples:
            nid = cdp.send("DOM.querySelector", {"nodeId": root, "selector": f'[data-pcv-fid="{s["fid"]}"]'})["nodeId"]
            if nid:
                out[str(s["fid"])] = cdp.send("CSS.getPlatformFontsForNode", {"nodeId": nid})["fonts"]
    finally:
        cdp.detach()
    return out


def render(deck: Deck, out: Path, only: list[int] | None = None, scale: float | None = None,
           fmt: str | None = None, headless: bool = False) -> dict:
    """Render slides (1-based indices in `only`, default all). Returns the render manifest."""
    from playwright.sync_api import sync_playwright

    r = deck.render
    W, H = r["width"], r["height"]
    scale = float(scale or r["scale"])
    fmt = (fmt or r["format"]).lower()
    ext = "jpg" if fmt in ("jpg", "jpeg") else "png"
    img_dir, dom_dir = out / "images", out / "dom"
    img_dir.mkdir(parents=True, exist_ok=True)
    dom_dir.mkdir(parents=True, exist_ok=True)
    inspect_js = (CANVAS_DIR / "pcv-inspect.js").read_text(encoding="utf-8")
    man_path = out / "render-manifest.json"
    manifest = read_json(man_path) if man_path.is_file() and only else {"slides": {}}
    files = deck.slide_files()
    indices = only or list(range(1, len(files) + 1))
    router = Router(deck)
    errors: list[dict] = []

    with sync_playwright() as p:
        args = ["--window-position=-2400,-2400", "--window-size=1600,1000",
                "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding", "--font-render-hinting=none", "--hide-scrollbars"]
        try:
            browser = p.chromium.launch(channel="chrome", headless=headless, args=args)
        except Exception:
            browser = p.chromium.launch(headless=headless, args=args)
        context = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=scale,
                                      locale="en-US", timezone_id="UTC", color_scheme="light",
                                      reduced_motion="reduce")
        context.route("**/*", router)
        page = context.new_page()
        console: list[str] = []
        page.on("console", lambda m: console.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
        for i in indices:
            f = files[i - 1]
            sid = deck.slide_id(i)
            if not f.is_file():
                errors.append({"slide": i, "error": f"slide source missing: {f}"})
                manifest["slides"].pop(str(i), None)
                continue
            console.clear()
            n_log = len(router.log)
            rel = f.relative_to(deck.dir).as_posix()
            fix_css = deck.fixes_dir() / f"{Path(rel).stem}.css"
            css = [FREEZE_CSS] + [(deck.dir / c).read_text(encoding="utf-8") for c in deck.cfg["inject_css"]]
            if fix_css.is_file():
                css.append(fix_css.read_text(encoding="utf-8"))
            router.inject = {rel: "\n".join(css)}
            t0 = time.perf_counter()
            page.goto(f"{ORIGIN}/{urllib.parse.quote(rel)}?v={int(time.time() * 1000)}", wait_until="load",
                      timeout=r["timeout_ms"])
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            try:
                page.wait_for_selector(r["selector"], state="attached", timeout=r["timeout_ms"])
            except Exception:
                errors.append({"slide": i, "error": f"slide root {r['selector']!r} never appeared"})
                manifest["slides"].pop(str(i), None)
                continue
            if page.evaluate(WAIT_READY_JS, r["timeout_ms"]) != "ready":
                errors.append({"slide": i, "error": f"slide never became ready within {r['timeout_ms']} ms "
                                                    "(fonts, images or window.PCV_READY did not settle)"})
                manifest["slides"].pop(str(i), None)
                continue
            dpr, iw, ih = page.evaluate("[devicePixelRatio, innerWidth, innerHeight]")
            if abs(dpr - scale) > 1e-3 or iw != W or ih != H:
                raise RuntimeError(f"viewport drifted: dpr={dpr} inner={iw}x{ih}, expected {scale} {W}x{H}")
            img_path = img_dir / f"{sid}.{ext}"
            shot = {"path": str(img_path), "clip": {"x": 0, "y": 0, "width": W, "height": H},
                    "scale": "device", "animations": "disabled", "type": "jpeg" if ext == "jpg" else "png"}
            if ext == "jpg":
                shot["quality"] = int(r["jpeg_quality"])
            page.screenshot(**shot)
            with Image.open(img_path) as im:
                size = im.size
            expect = (round(W * scale), round(H * scale))
            if size != expect:
                raise RuntimeError(f"{img_path.name}: {size} != expected {expect}")
            dom = page.evaluate(inspect_js, {
                "selector": r["selector"],
                "titleSelector": deck.rules["title_selector"],
                "sourceSelector": deck.rules["source_selector"],
                "nocheckSelector": deck.rules["nocheck_selector"],
            })
            dom["platformFonts"] = _platform_fonts(context, page, dom.get("fontSamples", []))
            dom["console"] = list(console)
            dom["network"] = router.log[n_log:]
            write_json(dom_dir / f"{sid}.json", dom)
            manifest["slides"][str(i)] = {
                "id": sid, "source": rel, "source_sha256": sha256_file(f), "image": img_path.relative_to(out).as_posix(),
                "image_sha256": sha256_file(img_path), "size": list(size),
                "dom": f"dom/{sid}.json", "fix_css": fix_css.name if fix_css.is_file() else None,
                "ms": round((time.perf_counter() - t0) * 1000),
            }
        version = browser.version
        browser.close()

    # Drop entries for slides no longer in the deck; keep earlier errors for slides not re-rendered now.
    manifest["slides"] = {k: v for k, v in manifest["slides"].items() if int(k) <= len(files)}
    errors = [e for e in manifest.get("errors", []) if e["slide"] not in indices and e["slide"] <= len(files)] + errors
    manifest.update({
        "deck": deck.title, "count": len(files), "canvas": [W, H], "scale": scale, "format": ext,
        "browser": f"chrome {version}", "headless": headless, "platform": platform.platform(),
        "rendered": datetime.now(timezone.utc).isoformat(timespec="seconds"), "errors": errors,
    })
    write_json(man_path, manifest)
    return manifest


def ordered_images(out: Path) -> list[Path]:
    man = read_json(out / "render-manifest.json")
    missing = [i for i in range(1, man["count"] + 1) if str(i) not in man["slides"]]
    if missing:
        raise RuntimeError(f"slides not rendered: {missing}")
    return [out / man["slides"][str(i)]["image"] for i in range(1, man["count"] + 1)]


def load_dom(out: Path, index: int) -> dict:
    man = read_json(out / "render-manifest.json")
    return read_json(out / man["slides"][str(index)]["dom"])


def dump_manifest(out: Path) -> str:
    return json.dumps(read_json(out / "render-manifest.json"), indent=2)

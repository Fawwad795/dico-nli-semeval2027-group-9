"""Load deck.json with defaults. Paths in deck.json are relative to the deck folder."""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path

from .util import read_json

DEFAULTS = {
    "title": "Untitled presentation",
    "author": "",
    "slides": [],
    "render": {
        "width": 1920,
        "height": 1080,
        "scale": 2,
        "format": "png",
        "jpeg_quality": 95,
        "selector": "[data-pcv-slide]",
        "timeout_ms": 30000,
    },
    "rules": {
        "min_font_px": 20,
        "safe_margin_px": 64,
        "max_title_lines": 2,
        "title_selector": "[data-pcv-title], h1",
        "max_words": 90,
        "type_scale": None,
        "number_policy": "major",
        "min_integer_checked": 10,
        "source_selector": "[data-pcv-source]",
        "require_source_for_numbers": False,
        "nocheck_selector": "[data-pcv-nocheck], .pcv-folio",
        "require_title": True,
        "spelling": True,
    },
    "sources": [],
    "glossary": [],
    "references": {},
    "network": {
        "allow": [
            "fonts.googleapis.com",
            "fonts.gstatic.com",
            "cdn.jsdelivr.net",
            "unpkg.com",
            "cdnjs.cloudflare.com",
        ]
    },
    "inject_css": [],
    "fixes_dir": "fixes",
    "build_dir": "build",
    "notes_suffix": ".notes.md",
}


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


@dataclass
class Deck:
    dir: Path
    cfg: dict

    @classmethod
    def load(cls, path: str | Path) -> "Deck":
        p = Path(path).resolve()
        if p.is_dir():
            p = p / "deck.json"
        if not p.is_file():
            raise FileNotFoundError(f"deck.json not found: {p}")
        cfg = _merge(DEFAULTS, read_json(p))
        if not cfg["slides"]:
            raise ValueError(f"{p}: 'slides' is empty")
        if cfg["rules"]["number_policy"] not in ("off", "critical", "major", "minor", "info"):
            raise ValueError(f"{p}: rules.number_policy must be off, critical, major, minor or info")
        if cfg["render"]["format"].lower() not in ("png", "jpeg", "jpg"):
            raise ValueError(f"{p}: render.format must be png or jpeg")
        return cls(p.parent, cfg)

    @property
    def title(self) -> str:
        return self.cfg["title"]

    @property
    def name(self) -> str:
        return self.cfg.get("name") or re.sub(r"[^a-z0-9]+", "-", self.title.lower()).strip("-") or "deck"

    @property
    def render(self) -> dict:
        return self.cfg["render"]

    @property
    def rules(self) -> dict:
        return self.cfg["rules"]

    @property
    def size(self) -> tuple[int, int]:
        return self.render["width"], self.render["height"]

    def slide_files(self) -> list[Path]:
        return [(self.dir / s).resolve() for s in self.cfg["slides"]]

    def slide_id(self, index: int) -> str:
        """1-based index -> stable output stem such as '03-results'."""
        stem = Path(self.cfg["slides"][index - 1]).stem
        return stem if re.match(r"^\d+[-_]", stem) else f"{index:02d}-{stem}"

    def sources(self) -> list[Path]:
        return [(self.dir / s).resolve() for s in self.cfg["sources"]]

    def build_dir(self, override: str | Path | None = None) -> Path:
        d = Path(override).resolve() if override else (self.dir / self.cfg["build_dir"]).resolve()
        d.mkdir(parents=True, exist_ok=True)
        return d

    def fixes_dir(self) -> Path:
        return (self.dir / self.cfg["fixes_dir"]).resolve()

    def notes_for(self, index: int) -> str:
        f = self.slide_files()[index - 1]
        n = f.with_name(f.stem + self.cfg["notes_suffix"])
        return n.read_text(encoding="utf-8").strip() if n.is_file() else ""

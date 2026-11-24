"""Small shared helpers: paths, hashing, JSON, findings."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]
CANVAS_DIR = SKILL_DIR / "canvas"

SEVERITIES = ("critical", "major", "minor", "info")
CATEGORIES = (
    "visual_design",
    "typography",
    "layout",
    "hierarchy",
    "content_accuracy",
    "storytelling",
    "data_visualization",
    "consistency",
    "technical",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def finding(code: str, severity: str, category: str, message: str, slide: int | None = None,
            evidence: dict | None = None, fix: dict | None = None) -> dict:
    assert severity in SEVERITIES, severity
    assert category in CATEGORIES, category
    return {
        "code": code,
        "severity": severity,
        "category": category,
        "slide": slide,
        "message": message,
        "evidence": evidence or {},
        "fix": fix,
    }


def cache_dir() -> Path:
    base = os.environ.get("PCV_CACHE")
    root = Path(base) if base else Path.home() / ".cache" / "presentation-creator-validator"
    d = root / "net"
    d.mkdir(parents=True, exist_ok=True)
    return d


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
}


def content_type(path: Path) -> str:
    return CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")

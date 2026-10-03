"""Local notes: list, search (BM25 over sections) and safely read markdown/text files."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ALLOWED_SUFFIXES = {".md", ".txt"}
TOKEN_RE = re.compile(r"[a-z0-9]+")
MAX_FILE_BYTES = 1_000_000


class NotesError(ValueError):
    """Raised for user-correctable problems (bad path, missing file...)."""


@dataclass
class Section:
    path: str
    heading: str
    text: str


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


class Notes:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise NotesError(f"notes directory does not exist: {root}")
        self._sections: list[Section] = []
        self._tf: list[Counter] = []
        self._df: Counter = Counter()
        self.reindex()

    def _files(self) -> list[Path]:
        out = []
        for p in sorted(self.root.rglob("*")):
            if p.suffix.lower() in ALLOWED_SUFFIXES and p.is_file() and not p.is_symlink():
                if p.stat().st_size <= MAX_FILE_BYTES:
                    out.append(p)
        return out

    def reindex(self) -> int:
        self._sections, self._tf, self._df = [], [], Counter()
        for f in self._files():
            rel = f.relative_to(self.root).as_posix()
            text = f.read_text(encoding="utf-8", errors="replace")
            self._sections.extend(_split_sections(rel, f.stem, text))
        for s in self._sections:
            tf = Counter(tokenize(s.heading + " " + s.text))
            self._tf.append(tf)
            self._df.update(tf.keys())
        return len(self._sections)

    def list_notes(self) -> list[dict]:
        return [{"path": f.relative_to(self.root).as_posix(), "bytes": f.stat().st_size}
                for f in self._files()]

    def search(self, query: str, limit: int = 5, k1: float = 1.5, b: float = 0.75) -> list[dict]:
        if not query.strip():
            raise NotesError("query must not be empty")
        limit = max(1, min(limit, 20))
        terms = set(tokenize(query))
        n = len(self._sections)
        avg = sum(sum(tf.values()) for tf in self._tf) / max(n, 1)
        scored = []
        for sec, tf in zip(self._sections, self._tf):
            dl, score = sum(tf.values()), 0.0
            for t in terms & tf.keys():
                idf = math.log(1 + (n - self._df[t] + 0.5) / (self._df[t] + 0.5))
                score += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * dl / avg))
            if score > 0:
                scored.append((score, sec))
        scored.sort(key=lambda x: -x[0])
        return [{"path": s.path, "heading": s.heading, "score": round(sc, 3),
                 "snippet": _snippet(s.text, terms)} for sc, s in scored[:limit]]

    def read(self, rel_path: str, max_chars: int = 20_000) -> dict:
        target = self._resolve(rel_path)
        text = target.read_text(encoding="utf-8", errors="replace")
        truncated = len(text) > max_chars
        return {"path": rel_path, "truncated": truncated, "total_chars": len(text),
                "content": text[:max_chars]}

    def _resolve(self, rel_path: str) -> Path:
        if not rel_path or "\x00" in rel_path:
            raise NotesError("invalid path")
        candidate = (self.root / rel_path).resolve()
        # resolve() follows symlinks, so a link pointing outside the root is caught here
        if self.root != candidate and self.root not in candidate.parents:
            raise NotesError("path is outside the notes directory")
        if candidate.suffix.lower() not in ALLOWED_SUFFIXES:
            raise NotesError(f"only {sorted(ALLOWED_SUFFIXES)} files can be read")
        if not candidate.is_file():
            raise NotesError(f"no such note: {rel_path}")
        return candidate


def _split_sections(path: str, title: str, text: str) -> list[Section]:
    """Split a note into sections at markdown headings (levels 1-4). Text before the first heading
    belongs to a section named after the file."""
    sections: list[Section] = []
    heading, lines = title, []

    def close() -> None:
        body = "\n".join(lines).strip()
        if body:
            sections.append(Section(path, heading, body))

    for line in text.splitlines():
        m = re.match(r"^#{1,4}\s+(.*)", line)
        if m:
            close()
            heading, lines = m.group(1).strip(), []
        else:
            lines.append(line)
    close()
    return sections


def _snippet(text: str, terms: set[str], width: int = 160) -> str:
    flat = " ".join(text.split())
    low = flat.lower()
    pos = min((low.find(t) for t in terms if low.find(t) >= 0), default=0)
    start = max(0, pos - width // 4)
    return ("..." if start else "") + flat[start:start + width] + ("..." if start + width < len(flat) else "")

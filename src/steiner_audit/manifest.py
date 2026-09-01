"""Acquisition manifests: content-addressed records of third-party inputs.

A manifest pins what was acquired (path, size, sha256) and where it came from,
so every downstream verdict references immutable, identified inputs. The PKU
artifacts pin neither hashes nor sizes; these manifests are the audit's answer.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "steiner-audit/manifest/v1"

_CHUNK = 1 << 22


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class FileEntry:
    """One acquired file, relative to the manifest root, POSIX separators."""

    path: str
    bytes: int
    sha256: str
    # Publisher-declared hash where one exists (HuggingFace LFS oid); None for
    # sources that publish no hashes (the git snapshot's individual files).
    publisher_sha256: str | None = None

    @property
    def matches_publisher(self) -> bool | None:
        if self.publisher_sha256 is None:
            return None
        return self.sha256 == self.publisher_sha256


@dataclass(frozen=True)
class Manifest:
    schema: str
    created_utc: str
    source: dict[str, Any]
    files: tuple[FileEntry, ...]

    @classmethod
    def build(
        cls,
        root: Path,
        relpaths: list[str],
        source: dict[str, Any],
        publisher_sha256: dict[str, str] | None = None,
    ) -> "Manifest":
        declared = publisher_sha256 or {}
        entries = []
        for rel in sorted(relpaths):
            p = root / rel
            entries.append(
                FileEntry(
                    path=rel,
                    bytes=p.stat().st_size,
                    sha256=sha256_file(p),
                    publisher_sha256=declared.get(rel),
                )
            )
        return cls(
            schema=SCHEMA,
            created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            source=source,
            files=tuple(entries),
        )

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = asdict(self)
        doc["file_count"] = len(self.files)
        doc["total_bytes"] = sum(f.bytes for f in self.files)
        path.write_text(json.dumps(doc, indent=2) + "\n")

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        doc = json.loads(path.read_text())
        if doc.get("schema") != SCHEMA:
            raise ValueError(f"unexpected manifest schema: {doc.get('schema')!r}")
        files = tuple(
            FileEntry(
                path=f["path"],
                bytes=f["bytes"],
                sha256=f["sha256"],
                publisher_sha256=f.get("publisher_sha256"),
            )
            for f in doc["files"]
        )
        return cls(
            schema=doc["schema"],
            created_utc=doc["created_utc"],
            source=doc["source"],
            files=files,
        )

    def verify(self, root: Path) -> list[str]:
        """Re-hash every file under root; return human-readable mismatches."""
        problems = []
        for entry in self.files:
            p = root / entry.path
            if not p.is_file():
                problems.append(f"missing: {entry.path}")
                continue
            size = p.stat().st_size
            if size != entry.bytes:
                problems.append(f"size mismatch: {entry.path} ({size} != {entry.bytes})")
                continue
            digest = sha256_file(p)
            if digest != entry.sha256:
                problems.append(f"sha256 mismatch: {entry.path}")
        return problems

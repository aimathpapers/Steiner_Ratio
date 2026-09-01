"""Machine-readable per-region verdicts.

One run = one directory: run.json (provenance: inputs, their hashes, code
revision, precision ladder) + verdicts.jsonl (one row per verified record,
append-friendly so multi-hour runs resume). The filesystem is the store —
no database (M1 implementation decision).
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .kernel import Verdict


def code_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).parent,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return "unknown"


class RunWriter:
    def __init__(self, out_dir: Path, meta: dict[str, Any]) -> None:
        self.out_dir = out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        self.meta = dict(meta)
        self.meta.setdefault("schema", "steiner-audit/run/v1")
        self.meta.setdefault("code_revision", code_revision())
        self.meta["started_utc"] = datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        )
        self.counts: Counter[str] = Counter()
        self._write_meta()
        self._fh = (out_dir / "verdicts.jsonl").open("a")

    def _write_meta(self) -> None:
        (self.out_dir / "run.json").write_text(
            json.dumps(self.meta | {"counts": dict(self.counts)}, indent=2) + "\n"
        )

    def add(self, verdict: Verdict) -> None:
        self.counts[verdict.mode] += 1
        self._fh.write(json.dumps(asdict(verdict)) + "\n")

    def finish(self) -> dict[str, int]:
        self._fh.close()
        self.meta["finished_utc"] = datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        )
        self._write_meta()
        return dict(self.counts)


def iter_verdicts(path: Path) -> Iterator[Verdict]:
    with path.open() as f:
        for line in f:
            if line.strip():
                yield Verdict(**json.loads(line))

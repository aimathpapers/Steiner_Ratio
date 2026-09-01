"""Release-bundle staging: python -m steiner_audit.release (ticket #13).

Assembles the publication-time bundle under release/staging/ from the
repository, applying the ADR-0002 curation rules mechanically:

- nothing from vendor/ is staged (unlicensed upstream artifacts);
- the semantic-diff artifacts are staged as counts-only variants (their
  findings_localized sections embed upstream region records, which the
  release truncates unless upstream licensing is clarified);
- everything else staged is our own work: code, tests, report, manifests,
  curated run records, and one compressed full-verdicts file for the
  smallest case as a spot-check sample (the rest regenerate from the
  released tooling).

The staged tree gets its own content-addressed manifest. Staging is local:
actual publication (public repo, arXiv) stays a human decision.
"""

from __future__ import annotations

import gzip
import json
import shutil
import sys
from pathlib import Path

from . import acquisition as acq
from .manifest import Manifest

STAGING = acq.STEINER_ROOT / "release" / "staging"

_CODE = ("pyproject.toml", "uv.lock", "LICENSE", "README.md")
_TREES = ("src/steiner_audit", "tests")
_ARTIFACT_GLOBS = (
    "artifacts/acquisition/*.json",
    "artifacts/verification/*.run.json",
    "artifacts/verification/their_checker_replays.json",
    # ceiling/probe summaries carry counts, certified bounds, and hashes
    # only — no upstream region geometry (the geometry-bearing
    # bottlenecks.jsonl files stay local per ADR-0002)
    "artifacts/verification/ceiling_full_*.json",
    "artifacts/verification/ceiling_sample_*.json",
    "artifacts/verification/ceiling_fullbox_sample_*.json",
    "artifacts/verification/probe_ceiling_*.json",
    "artifacts/notes/observations.md",
    "report/verification-note.md",
    "report/record-note-0.860.md",
    "paper/steiner-certificate-record.tex",
    "paper/steiner-certificate-record.pdf",
)
_DIFF_GLOB = "artifacts/verification/semantic_diff_*.json"
_SAMPLE_VERDICTS = "runs/full_d_regular_f_ge_d/verdicts.jsonl"

RELEASE_README = """\
# Steiner_Ratio — independent verification of the Gilbert-Pollak certificate layer, and a certificate-layer bound of 0.860

This repository contains, in decreasing order of formality:

- paper/steiner-certificate-record.pdf (+ .tex) — the full paper;
- report/verification-note.md — the audit of the published 0.8559
  certificate layer; report/record-note-0.860.md — the record claim;
- the clean-room verifier and its two-seam test suite, content-addressed
  manifests, and curated run records for every verification run.

Archived release: https://doi.org/10.5281/zenodo.22223485
Contact: aimathpapers@gmail.com

Claim scope: this work verifies the CERTIFICATE LAYER of arXiv:2601.22365
only. It is not an independent verification of rho >= 0.8559 as a theorem;
see the report's Section 1. The companion record note
(report/record-note-0.860.md) extends the certificate layer to
rho >= 0.860 via partition regeneration at the higher target — same
scope, same inherited lemma-layer obligations, exact rational 43/50
throughout; regenerated certificates ship as sha256 hashes only.

The upstream artifacts (github.com/keyisi2006/Steiner-Ratio and the
huggingface.co/datasets/keyisi/steiner-ratio dataset) are NOT included:
they carry no license. Reproduction fetches them from the public sources
and checks them against artifacts/acquisition/*.json (the audited commit
and per-file sha256 are pinned there).

Quick start (no dataset needed):

    uv sync
    uv run pytest -m "not real_data"

Full replay: use `python -m steiner_audit.acquire` to fetch and pin the
upstream artifacts, then `python -m steiner_audit.verify` per case
(`--help` for modes and sharding), and `python -m steiner_audit.status`
for the live view. verdicts_sample/ holds the complete per-region verdict
stream for the d_regular f>=d case (gzipped JSONL) as a spot-check sample;
all other verdict streams regenerate deterministically from the tooling.

Curation note: semantic_diff_*.json here are counts-only variants; the
findings_localized sections (which embed upstream region records) are
truncated per the audit's reuse posture (ADR-0002).
"""


def _counts_only_diff(source: Path, dest: Path) -> None:
    doc = json.loads(source.read_text())
    removed = len(doc.get("findings_localized", []))
    doc["findings_localized"] = []
    doc["curation_note"] = (
        f"{removed} localized findings truncated for release (ADR-0002); "
        "the full artifact lives in the private audit repository"
    )
    dest.write_text(json.dumps(doc, indent=2) + "\n")


def stage(root: Path = STAGING) -> Manifest:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    for name in _CODE:
        source = acq.STEINER_ROOT / name
        if name == "README.md":
            (root / "README.md").write_text(RELEASE_README)
            continue
        shutil.copy2(source, root / name)
    for tree in _TREES:
        shutil.copytree(
            acq.STEINER_ROOT / tree,
            root / tree,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    for pattern in _ARTIFACT_GLOBS:
        for source in sorted(acq.STEINER_ROOT.glob(pattern)):
            rel = source.relative_to(acq.STEINER_ROOT)
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, root / rel)

    # the report cites the pre-audit research (our own work, parent repo)
    research = acq.STEINER_ROOT.parent / "docs" / "research" / "gilbert-pollak-pku-pipeline.md"
    if research.exists():
        dest = root / "docs" / "research" / research.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(research, dest)
    for source in sorted(acq.STEINER_ROOT.glob(_DIFF_GLOB)):
        rel = source.relative_to(acq.STEINER_ROOT)
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        _counts_only_diff(source, root / rel)

    sample = acq.STEINER_ROOT / _SAMPLE_VERDICTS
    if sample.exists():
        out = root / "verdicts_sample" / "full_d_regular_f_ge_d.verdicts.jsonl.gz"
        out.parent.mkdir(parents=True)
        with sample.open("rb") as fin, gzip.open(out, "wb", compresslevel=6) as fout:
            shutil.copyfileobj(fin, fout)

    relpaths = [
        str(p.relative_to(root))
        for p in sorted(root.rglob("*"))
        if p.is_file()
    ]
    manifest = Manifest.build(
        root,
        relpaths,
        source={
            "kind": "release-staging",
            "staged_from": "MathProof steiner/ (private audit repository)",
        },
    )
    manifest.write(root / "BUNDLE_MANIFEST.json")
    return manifest


def main() -> int:
    manifest = stage()
    total = sum(f.bytes for f in manifest.files)
    print(
        f"staged {len(manifest.files)} files ({total / 1e6:.1f} MB) -> {STAGING}"
    )
    forbidden = [f.path for f in manifest.files if f.path.startswith("vendor")]
    if forbidden:
        print(f"ERROR: vendor content staged: {forbidden}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

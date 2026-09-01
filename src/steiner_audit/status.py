"""The audit's single status view: python -m steiner_audit.status.

Aggregates, from the filesystem store: corpus size per case, every run's
verdict counts (live runs counted from their verdicts.jsonl), full-box
coverage, regeneration state, and open triage discrepancies. Coverage
percentages are computed from verdicts, never estimated (user story 17).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

from flint import fmpq

from . import acquisition as acq
from .arbcalc import RHO_M1_STR, parse_rho, rho_str
from .manifest import Manifest
from .records import record_struct

CASES = [
    ("d_regular", "f_ge_d", 5),
    ("d_regular", "f_le_d", 6),
    ("d_steiner", "f_ge_d", 7),
    ("d_steiner", "f_le_d", 8),
]


def best_certified_rho(
    totals: Mapping[str, int],
    runs: Sequence[tuple[Mapping[str, object], Mapping[str, int]]],
    expected_sha: Mapping[str, str] | None = None,
) -> dict[str, fmpq]:
    """Per case, the largest rho certified by a finished, full-coverage,
    zero-defect run. Pre-#15 run metas carry no rho key: those runs were all
    at the M1 bound 8559/10000. Samples, partial runs, and anything with a
    failed/invalid/inconclusive verdict certify nothing. When expected_sha
    is given (case key -> sha256), only runs over that exact certificate
    content count — a full clean run over some other --cert file certifies
    nothing about the corpus, however equal its record count."""
    best: dict[str, fmpq] = {}
    for meta, counts in runs:
        key = f"{meta.get('family')}/{meta.get('subcase')}"
        total = totals.get(key)
        if total is None or not meta.get("finished_utc"):
            continue
        if meta.get("sample") is not None or meta.get("limit") is not None:
            continue
        if expected_sha is not None and (
            meta.get("certificate_sha256") != expected_sha.get(key)
        ):
            continue
        bad = (
            counts.get("failed", 0)
            + counts.get("invalid", 0)
            + counts.get("inconclusive", 0)
        )
        if bad or sum(counts.values()) != total:
            continue
        rho = parse_rho(str(meta.get("rho", RHO_M1_STR)))
        if key not in best or rho > best[key]:
            best[key] = rho
    return best


def _canonical_cert_shas() -> dict[str, str] | None:
    """case key -> published certificate sha256, from the pinned manifest."""
    manifest_file = acq.ARTIFACTS / "acquisition" / "dataset_manifest.json"
    if not manifest_file.exists():
        return None
    by_path = {f.path: f.sha256 for f in Manifest.load(manifest_file).files}
    out = {}
    for family, subcase, _ in CASES:
        sha = by_path.get(f"{family}/certificate_rho=0.8559_{subcase}.bin")
        if sha is not None:
            out[f"{family}/{subcase}"] = sha
    return out


def _corpus_totals() -> dict[str, int]:
    out = {}
    for family, subcase, n in CASES:
        path = acq.DATASET_DIR / family / f"certificate_rho=0.8559_{subcase}.bin"
        if path.exists():
            out[f"{family}/{subcase}"] = (
                path.stat().st_size // record_struct(n).size
            )
    return out


def _run_counts(run_dir: Path) -> tuple[dict[str, object], Counter[str]]:
    meta = json.loads((run_dir / "run.json").read_text())
    counts: Counter[str] = Counter()
    if meta.get("finished_utc") and meta.get("counts"):
        counts.update(meta["counts"])
    else:
        verdicts = run_dir / "verdicts.jsonl"
        if verdicts.exists():
            with verdicts.open() as f:
                for line in f:
                    if line.strip():
                        counts[json.loads(line)["mode"]] += 1
    return meta, counts


def main() -> int:
    print("=== M1 audit status ===")

    totals = _corpus_totals()
    print("\ncorpus (records per case):")
    for key, total in totals.items():
        print(f"  {key:24} {total:>12,}")

    print("\nverification runs (runs/):")
    runs_root = acq.STEINER_ROOT / "runs"
    verified_by_case: Counter[str] = Counter()
    run_summaries: list[tuple[dict[str, object], Counter[str]]] = []
    for run_dir in sorted(runs_root.glob("*/")) if runs_root.exists() else []:
        if not (run_dir / "run.json").exists():
            continue
        meta, counts = _run_counts(run_dir)
        run_summaries.append((meta, counts))
        key = f"{meta.get('family')}/{meta.get('subcase')}"
        state = "done" if meta.get("finished_utc") else "RUNNING"
        mode = meta.get("mode", "vertex-parity")
        n_ok = counts.get("vertex_parity", 0) + counts.get("full_box", 0)
        bad = counts.get("failed", 0) + counts.get("invalid", 0) + counts.get(
            "inconclusive", 0
        )
        if meta.get("sample") is None and meta.get("limit") is None:
            verified_by_case[key] = max(
                verified_by_case[key], sum(counts.values())
            )
        cov = ""
        if counts.get("full_box"):
            attempted = sum(counts.values())
            cov = f"  full-box {counts['full_box']}/{attempted} ({counts['full_box']/attempted:.1%})"
        rho = meta.get("rho", RHO_M1_STR)
        print(
            f"  {run_dir.name:38} {state:8} {mode:15} rho={rho:12} "
            f"ok={n_ok:,} skip={counts.get('skipped', 0):,} bad={bad:,}{cov}"
        )

    print("\nfull-corpus progress (our stack, full runs only):")
    for key, total in totals.items():
        done = verified_by_case.get(key, 0)
        print(f"  {key:24} {done:>12,} / {total:>12,}  ({done/total:.1%})")

    best = best_certified_rho(totals, run_summaries, _canonical_cert_shas())
    print("\nbest certified rho (finished full runs, zero defects, "
          "pinned certificate):")
    for key in totals:
        shown = rho_str(best[key]) if key in best else "-"
        print(f"  {key:24} {shown}")
    all_cases = [f"{fam}/{sub}" for fam, sub, _ in CASES]
    if all(key in best for key in all_cases):
        overall = min(best[key] for key in all_cases)
        # F is nondecreasing in rho, so each case's certificate also covers
        # every smaller rho: the four-case bound is the minimum.
        print(f"  {'ALL FOUR CASES':24} {rho_str(overall)}")
    else:
        print(f"  {'ALL FOUR CASES':24} -  (some case lacks a full clean run)")

    regen_state = acq.VENDOR / "regen" / "state.json"
    print("\nregeneration (their generator, our machine):")
    if regen_state.exists():
        for key, entry in json.loads(regen_state.read_text()).items():
            wall = entry.get("wall_seconds")
            print(f"  {key:24} {entry.get('status'):8} "
                  f"{'' if wall is None else f'{wall}s'}")
    else:
        print("  (none yet)")

    queue_path = runs_root / "triage" / "queue.jsonl"
    print("\ntriage queue:")
    if queue_path.exists():
        states: Counter[str] = Counter()
        latest: dict[str, str] = {}
        for line in queue_path.read_text().splitlines():
            if line.strip():
                entry = json.loads(line)
                latest[entry["entry_id"]] = entry["status"]
        states.update(latest.values())
        for status, count in states.most_common():
            print(f"  {status:12} {count}")
        if not states:
            print("  empty")
    else:
        print("  empty — zero open discrepancies")

    return 0


if __name__ == "__main__":
    sys.exit(main())

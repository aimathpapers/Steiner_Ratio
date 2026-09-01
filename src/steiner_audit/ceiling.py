"""Ceiling search over the published tiling: python -m steiner_audit.ceiling.

    uv run python -m steiner_audit.ceiling --family d_regular --subcase f_ge_d \
        [--sample N --seed S | --limit N] [--workers K] [--fullbox] [--out DIR]

One pass computes, per record, certified bounds on its critical rho (the
sup rho it certifies; see kernel.critical_rho_vertex_parity) and, with
--fullbox, a one-sided full-box certificate driven at --drive-rho. The
corpus minimum of the per-record bounds IS the tiling's ceiling under the
chosen semantics — no bisection, no regeneration. Artifacts per run:

- ceiling.json: certified [lo, hi] for the corpus minimum, outcome counts,
  provenance (certificate sha, code revision, semantics, inherited
  lemma-layer obligations);
- bottlenecks.jsonl: the --bottom K records with the smallest critical-rho
  upper bounds — the machine-readable feed for bottleneck cartography (#17).

The adaptive ceiling (regenerating the partition at probe rhos with their
generator) is the follow-up stage; this fixed-tiling ceiling lower-bounds it
and locates exactly where the tiling binds.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import random
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from flint import fmpq

from . import acquisition as acq
from .arbcalc import parse_rho, rho_str
from .case import CaseFamily, Split, Subcase, parse_splits
from .cases import by_name
from .kernel import (
    DEFAULT_FULLBOX_BUDGET,
    DEFAULT_PREC_LADDER,
    CriticalRho,
    critical_rho_adr0004,
    critical_rho_vertex_parity,
)
from .records import RegionRecord, count_records, iter_records, read_record_at
from .verdicts import code_revision
from .verify import _cert_sha, cert_path, splits_path

INHERITED_NOTE = (
    "Inherited lemma-layer obligations are rho-uniform: trapped-point "
    "polygons, topology validity, and the monotonicity/unimodality claims "
    "are about constituent lengths, never about rho, so they transfer to "
    "every rho unchanged. Full-box leaf certificates need no unimodality."
)


class _Aggregate:
    """Streaming corpus minimum + bottom-K + outcome counts."""

    def __init__(self, bottom: int) -> None:
        self.counts: dict[str, int] = {}
        self.min_lo = math.inf
        self.min_hi = math.inf
        self.min_hi_region: int | None = None
        self.fullbox_min_lo = math.inf
        self.fullbox_closed = 0
        self._bottom_k = bottom
        # heap of (-crit_hi, region_id, row) — the K smallest crit_hi survive
        self._heap: list[tuple[float, int, dict[str, Any]]] = []

    def add(
        self,
        crit: CriticalRho,
        box: tuple[tuple[float, float], ...] | None = None,
    ) -> None:
        self.counts[crit.outcome] = self.counts.get(crit.outcome, 0) + 1
        if crit.fullbox_outcome == "closed" and crit.fullbox_lo is not None:
            self.fullbox_closed += 1
            self.fullbox_min_lo = min(self.fullbox_min_lo, crit.fullbox_lo)
        if crit.outcome != "bounded":
            return
        assert crit.crit_lo is not None and crit.crit_hi is not None
        self.min_lo = min(self.min_lo, crit.crit_lo)
        if crit.crit_hi < self.min_hi:
            self.min_hi = crit.crit_hi
            self.min_hi_region = crit.region_id
        if self._bottom_k > 0:
            row = asdict(crit)
            if box is not None:
                # the bottleneck artifact carries the region's box (CONTEXT.md);
                # unbounded tops as the string "inf" keeps the JSONL strict.
                # Local-analysis data: release curation ships counts-only
                # variants of anything embedding region geometry (ADR-0002).
                row["box"] = [
                    [low, "inf" if math.isinf(high) else high]
                    for (low, high) in box
                ]
            item = (-crit.crit_hi, crit.region_id, row)
            if len(self._heap) < self._bottom_k:
                heapq.heappush(self._heap, item)
            elif item > self._heap[0]:
                heapq.heapreplace(self._heap, item)

    def merge(self, other: "_Aggregate") -> None:
        for key, count in other.counts.items():
            self.counts[key] = self.counts.get(key, 0) + count
        self.min_lo = min(self.min_lo, other.min_lo)
        if other.min_hi < self.min_hi:
            self.min_hi = other.min_hi
            self.min_hi_region = other.min_hi_region
        self.fullbox_min_lo = min(self.fullbox_min_lo, other.fullbox_min_lo)
        self.fullbox_closed += other.fullbox_closed
        for item in other._heap:
            if len(self._heap) < self._bottom_k:
                heapq.heappush(self._heap, item)
            elif item > self._heap[0]:
                heapq.heapreplace(self._heap, item)

    def bottom_rows(self) -> list[dict[str, Any]]:
        return [row for _, _, row in sorted(self._heap, reverse=True)]


def _analyze_one(
    record: RegionRecord,
    family: CaseFamily,
    subcase: Subcase,
    splits: Sequence[Split],
    fullbox: bool,
    fullbox_budget: int,
    drive_rho: fmpq,
) -> CriticalRho:
    if fullbox:
        return critical_rho_adr0004(
            record, family, subcase, splits, fullbox_budget=fullbox_budget,
            drive_rho=drive_rho,
        )
    return critical_rho_vertex_parity(record, family, subcase, splits)


def _analyze_shard(
    shard: int,
    cert: str,
    family_name: str,
    subcase_name: str,
    start: int,
    count: int,
    n_splits: int,
    fullbox: bool,
    fullbox_budget: int,
    drive_rho_text: str,
    bottom: int,
) -> tuple[dict[str, int], float, float, int | None, float, int,
           list[tuple[float, int, dict[str, Any]]]]:
    family = by_name(family_name)
    subcase = family.subcases[subcase_name]
    splits = parse_splits(splits_path(family_name).read_text(), family)
    drive_rho = parse_rho(drive_rho_text)
    n = len(subcase.box_vars)
    agg = _Aggregate(bottom)
    for i, record in enumerate(
        iter_records(Path(cert), n=n, n_splits=n_splits, start=start)
    ):
        if i >= count:
            break
        agg.add(
            _analyze_one(
                record, family, subcase, splits, fullbox, fullbox_budget,
                drive_rho,
            ),
            box=record.box,
        )
    return (
        agg.counts, agg.min_lo, agg.min_hi, agg.min_hi_region,
        agg.fullbox_min_lo, agg.fullbox_closed, agg._heap,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="steiner_audit.ceiling")
    parser.add_argument("--family", default="d_regular")
    parser.add_argument("--subcase", default="f_ge_d", choices=["f_ge_d", "f_le_d"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sample", type=int, default=None)
    parser.add_argument("--seed", type=int, default=20260813)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--bottom", type=int, default=100,
                        help="how many lowest-ceiling records to keep")
    parser.add_argument("--fullbox", action="store_true",
                        help="also compute one-sided full-box certificates")
    parser.add_argument("--fullbox-budget", type=int, default=DEFAULT_FULLBOX_BUDGET)
    parser.add_argument(
        "--drive-rho", type=parse_rho, default="8559/10000",
        help="rho driving the full-box subdivision (the incumbent bound)",
    )
    parser.add_argument("--cert", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--progress-every", type=int, default=20000)
    args = parser.parse_args(argv)

    family = by_name(args.family)
    subcase = family.subcases[args.subcase]
    n = len(subcase.box_vars)
    cert = (
        args.cert.resolve() if args.cert is not None
        else cert_path(args.family, args.subcase)
    )
    splits = parse_splits(splits_path(args.family).read_text(), family)
    total = count_records(cert, n)
    out_dir = args.out or (
        acq.STEINER_ROOT / "runs"
        / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_ceiling_{args.family}_{args.subcase}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    agg = _Aggregate(args.bottom)
    analyzed = 0
    if args.workers > 1 and args.sample is None and args.limit is None:
        from concurrent.futures import ProcessPoolExecutor, as_completed

        chunk = (total + args.workers * 4 - 1) // (args.workers * 4)
        ranges = [
            (i, start, min(chunk, total - start))
            for i, start in enumerate(range(0, total, chunk))
        ]
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [
                pool.submit(
                    _analyze_shard, shard, str(cert), args.family,
                    args.subcase, start, count, len(splits), args.fullbox,
                    args.fullbox_budget, rho_str(args.drive_rho), args.bottom,
                )
                for shard, start, count in ranges
            ]
            done = 0
            for future in as_completed(futures):
                (counts, min_lo, min_hi, min_hi_region, fb_lo, fb_closed,
                 heap) = future.result()
                other = _Aggregate(args.bottom)
                other.counts = counts
                other.min_lo = min_lo
                other.min_hi = min_hi
                other.min_hi_region = min_hi_region
                other.fullbox_min_lo = fb_lo
                other.fullbox_closed = fb_closed
                other._heap = heap
                agg.merge(other)
                analyzed += sum(counts.values())
                done += 1
                print(f"[info] shard {done}/{len(ranges)} done "
                      f"({analyzed:,}/{total:,})", flush=True)
    else:
        records: Iterable[RegionRecord]
        if args.sample is not None:
            rng = random.Random(args.seed)
            indices = sorted(rng.sample(range(total), min(args.sample, total)))
            records = (
                read_record_at(cert, idx, n=n, n_splits=len(splits))
                for idx in indices
            )
        else:
            records = iter_records(cert, n=n, n_splits=len(splits))
        for record in records:
            if args.limit is not None and analyzed >= args.limit:
                break
            agg.add(
                _analyze_one(
                    record, family, subcase, splits, args.fullbox,
                    args.fullbox_budget, args.drive_rho,
                ),
                box=record.box,
            )
            analyzed += 1
            if analyzed % args.progress_every == 0:
                print(f"[info] {analyzed:,} analyzed "
                      f"(min crit_hi so far {agg.min_hi:.6f})", flush=True)

    exhaustive = args.sample is None and args.limit is None
    summary = {
        "schema": "steiner-audit/ceiling/v1",
        "family": args.family,
        "subcase": args.subcase,
        "certificate": str(cert),
        "certificate_sha256": _cert_sha(cert),
        "code_revision": code_revision(),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records_in_file": total,
        "analyzed": analyzed,
        "exhaustive": exhaustive,
        "sample": args.sample,
        "seed": args.seed if args.sample is not None else None,
        "limit": args.limit,
        "prec_ladder": list(DEFAULT_PREC_LADDER),
        "semantics": "vertex" if not args.fullbox else "vertex+fullbox",
        "drive_rho": rho_str(args.drive_rho) if args.fullbox else None,
        "fullbox_budget": args.fullbox_budget if args.fullbox else None,
        "outcome_counts": agg.counts,
        # certified bounds on min-over-analyzed-records critical rho; the
        # corpus ceiling exactly when exhaustive, an upper bound estimate
        # otherwise (unanalyzed records can only lower the min)
        "ceiling_lo": None if math.isinf(agg.min_lo) else agg.min_lo,
        "ceiling_hi": None if math.isinf(agg.min_hi) else agg.min_hi,
        "ceiling_region_id": agg.min_hi_region,
        "fullbox_closed": agg.fullbox_closed,
        "fullbox_ceiling_lo": (
            None if math.isinf(agg.fullbox_min_lo) else agg.fullbox_min_lo
        ),
        "inherited_obligations": INHERITED_NOTE,
    }
    (out_dir / "ceiling.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (out_dir / "bottlenecks.jsonl").open("w") as fh:
        for row in agg.bottom_rows():
            fh.write(json.dumps(row) + "\n")

    print(f"analyzed {analyzed:,}/{total:,} -> {out_dir}")
    print(f"outcomes: {agg.counts}")
    if summary["ceiling_hi"] is not None:
        kind = "ceiling" if exhaustive else "ceiling estimate (sampled)"
        print(f"{kind}: [{summary['ceiling_lo']:.10f}, "
              f"{summary['ceiling_hi']:.10f}] at region "
              f"{agg.min_hi_region} (incumbent 0.8559)")
    if args.fullbox and summary["fullbox_ceiling_lo"] is not None:
        print(f"full-box one-sided ceiling over closed regions: "
              f">= {summary['fullbox_ceiling_lo']:.10f} "
              f"({agg.fullbox_closed:,} closed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Orchestrator CLI: certificate records in, per-region verdicts out.

    uv run python -m steiner_audit.verify --family d_regular --subcase f_ge_d \
        [--limit N] [--sample N --seed S] [--out DIR] [--workers K] [--rho P/Q]

With --sample, record indices are drawn deterministically from the seed;
otherwise records stream in file order. --workers K > 1 shards the file
into contiguous index ranges verified by separate processes (verdicts land
in per-shard JSONL files, counts merged into run.json) — the full-corpus
path for ticket #12.
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from flint import fmpq

from . import acquisition as acq
from .arbcalc import RHO_M1_STR, parse_rho, rho_str
from .case import CaseFamily, Split, Subcase, parse_splits
from .cases import by_name
from .kernel import (
    DEFAULT_FULLBOX_BUDGET,
    DEFAULT_PREC_LADDER,
    Verdict,
    verify_record_adr0004,
    verify_record_vertex_parity,
)
from .manifest import Manifest
from .records import RegionRecord, count_records, iter_records, read_record_at
from .verdicts import RunWriter


def cert_path(family: str, subcase: str) -> Path:
    return acq.DATASET_DIR / family / f"certificate_rho=0.8559_{subcase}.bin"


def splits_path(family: str) -> Path:
    return acq.SNAPSHOT_DIR / "certificate" / family / "splits.txt"


def _cert_sha(cert: Path) -> str | None:
    """The certificate's recorded sha256, from whichever manifest owns it.

    Looked up, never recomputed (hashing 36 GB per run would be wasteful) —
    and never cross-manifest: a regenerated certificate must not inherit
    the published file's hash just because the basenames match.
    """
    candidates = []
    try:
        rel = str(cert.relative_to(acq.DATASET_DIR))
        candidates.append((acq.ARTIFACTS / "acquisition" / "dataset_manifest.json", rel))
    except ValueError:
        pass
    try:
        rel = str(cert.relative_to(acq.VENDOR / "regen"))
        candidates.append((acq.ARTIFACTS / "acquisition" / "regen_manifest.json", rel))
    except ValueError:
        pass
    for manifest_file, rel in candidates:
        if not manifest_file.exists():
            continue
        for entry in Manifest.load(manifest_file).files:
            if entry.path == rel:
                return entry.sha256
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="steiner_audit.verify")
    parser.add_argument("--family", default="d_regular")
    parser.add_argument("--subcase", default="f_ge_d", choices=["f_ge_d", "f_le_d"])
    parser.add_argument("--limit", type=int, default=None,
                        help="verify only the first N records")
    parser.add_argument("--sample", type=int, default=None,
                        help="verify N records drawn uniformly at random")
    parser.add_argument("--seed", type=int, default=20260812)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--progress-every", type=int, default=10000)
    parser.add_argument(
        "--mode",
        choices=["full-box-first", "vertex-parity"],
        default="full-box-first",
        help="full-box-first is the ADR-0004 semantics (the default); "
        "vertex-parity alone replicates their check for cross-comparison "
        "runs and costs 2-5x less",
    )
    parser.add_argument("--fullbox-budget", type=int, default=DEFAULT_FULLBOX_BUDGET)
    parser.add_argument(
        "--rho", type=parse_rho, default=RHO_M1_STR,
        help="exact rational bound to certify, as p/q or a decimal literal "
        "(default: the published 8559/10000; ticket #15)",
    )
    parser.add_argument(
        "--cert", type=Path, default=None,
        help="certificate file to verify (default: the acquired dataset's)",
    )
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)

    family = by_name(args.family)
    subcase = family.subcases[args.subcase]
    n = len(subcase.box_vars)
    cert = (
        args.cert.resolve()
        if args.cert is not None
        else cert_path(args.family, args.subcase)
    )
    splits = parse_splits(splits_path(args.family).read_text(), family)

    total = count_records(cert, n)
    out_dir = args.out or (
        acq.STEINER_ROOT / "runs"
        / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{args.family}_{args.subcase}"
    )
    writer = RunWriter(
        out_dir,
        {
            "kind": f"{args.mode}-run",
            "family": args.family,
            "subcase": args.subcase,
            "certificate": str(cert.relative_to(acq.STEINER_ROOT)),
            "certificate_sha256": _cert_sha(cert),
            "rho": rho_str(args.rho),
            "records_in_file": total,
            "limit": args.limit,
            "sample": args.sample,
            "seed": args.seed if args.sample else None,
            "prec_ladder": list(DEFAULT_PREC_LADDER),
            "mode": args.mode,
            "fullbox_budget": args.fullbox_budget if args.mode == "full-box-first" else None,
        },
    )

    if args.workers > 1 and args.sample is None and args.limit is None:
        counts, not_ok = _run_sharded(
            args, cert, n, len(splits), total, writer.out_dir
        )
        writer.counts.update(counts)
        writer.finish()
        print(f"done: {sum(counts.values())} records -> {out_dir}")
        print(f"counts: {dict(counts)}")
        return 0 if not_ok == 0 else 1

    records: Iterable[RegionRecord]
    if args.sample is not None:
        rng = random.Random(args.seed)
        indices = sorted(rng.sample(range(total), min(args.sample, total)))
        planned = len(indices)
        records = (
            read_record_at(cert, idx, n=n, n_splits=len(splits)) for idx in indices
        )
    else:
        planned = min(total, args.limit) if args.limit else total
        records = iter_records(cert, n=n, n_splits=len(splits))

    done = 0
    not_ok = 0
    for record in records:
        if args.limit is not None and done >= args.limit:
            break
        verdict = _verify_one(
            record, family, subcase, splits, args.mode, args.fullbox_budget,
            args.rho,
        )
        writer.add(verdict)
        if not verdict.ok:
            not_ok += 1
            print(f"[not-ok] region {verdict.region_id}: {verdict.mode}: "
                  f"{verdict.reason}", file=sys.stderr)
        done += 1
        if done % args.progress_every == 0:
            print(f"[info] {done}/{planned} verified ({dict(writer.counts)})")

    final_counts = writer.finish()
    print(f"done: {done} records -> {out_dir}")
    print(f"counts: {final_counts}")
    return 0 if not_ok == 0 else 1


def _verify_one(
    record: RegionRecord,
    family: CaseFamily,
    subcase: Subcase,
    splits: Sequence[Split],
    mode: str,
    fullbox_budget: int,
    rho: fmpq,
) -> Verdict:
    if mode == "full-box-first":
        return verify_record_adr0004(
            record, family, subcase, splits, fullbox_budget=fullbox_budget,
            rho=rho,
        )
    return verify_record_vertex_parity(record, family, subcase, splits, rho=rho)


def _verify_shard(
    shard: int,
    cert: str,
    family_name: str,
    subcase_name: str,
    start: int,
    count: int,
    n_splits: int,
    mode: str,
    fullbox_budget: int,
    rho_text: str,
    out_dir: str,
) -> tuple[int, dict[str, int], int]:
    """Worker: verify records [start, start+count) into a shard JSONL.

    rho crosses the process boundary as its canonical string, never a float.
    """
    import json
    from collections import Counter
    from dataclasses import asdict

    family = by_name(family_name)
    subcase = family.subcases[subcase_name]
    splits = parse_splits(splits_path(family_name).read_text(), family)
    rho = parse_rho(rho_text)
    n = len(subcase.box_vars)
    counts: Counter[str] = Counter()
    not_ok = 0
    shard_path = Path(out_dir) / f"verdicts_shard_{shard:03}.jsonl"
    with shard_path.open("w") as fh:
        for i, record in enumerate(
            iter_records(Path(cert), n=n, n_splits=n_splits, start=start)
        ):
            if i >= count:
                break
            verdict = _verify_one(
                record, family, subcase, splits, mode, fullbox_budget, rho
            )
            counts[verdict.mode] += 1
            if not verdict.ok:
                not_ok += 1
            fh.write(json.dumps(asdict(verdict)) + "\n")
    return shard, dict(counts), not_ok


def _run_sharded(
    args: argparse.Namespace,
    cert: Path,
    n: int,
    n_splits: int,
    total: int,
    out_dir: Path,
) -> tuple[Counter[str], int]:
    from concurrent.futures import ProcessPoolExecutor, as_completed

    workers = args.workers
    chunk = (total + workers * 4 - 1) // (workers * 4)
    ranges = [
        (i, start, min(chunk, total - start))
        for i, start in enumerate(range(0, total, chunk))
    ]
    counts: Counter[str] = Counter()
    not_ok = 0
    done_shards = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                _verify_shard,
                shard, str(cert), args.family, args.subcase, start, count,
                n_splits, args.mode, args.fullbox_budget, rho_str(args.rho),
                str(out_dir),
            )
            for shard, start, count in ranges
        ]
        for future in as_completed(futures):
            _, shard_counts, shard_not_ok = future.result()
            counts.update(shard_counts)
            not_ok += shard_not_ok
            done_shards += 1
            print(
                f"[info] shard {done_shards}/{len(ranges)} done "
                f"({sum(counts.values()):,}/{total:,} records)",
                flush=True,
            )
    return counts, not_ok


if __name__ == "__main__":
    sys.exit(main())

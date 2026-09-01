"""Semantic diff of two certificate datasets (ticket #10, CONTEXT.md term).

Two certificate files are semantically equal when they assert the same
multiset of claims (box bounds, split id, lemma id) — region numbering and
record order are generator bookkeeping, not mathematical content, so benign
regeneration nondeterminism (thread scheduling reordering records or
renumbering regions) produces zero findings. Bounds compare by exact value
(the partition rule makes every endpoint dyadic); the only normalization is
-0.0 == 0.0.

Implementation: each record's canonical payload (normalized bounds + split
+ lemma) is digested; the two digest multisets are compared. Divergences are
localized back to region ids by a second pass over the differing digests.
"""

from __future__ import annotations

import hashlib
import struct
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .records import iter_records

_MAX_LOCALIZED = 100  # per side; enough to localize, bounded output


def _canonical_payload(record_box: tuple[tuple[float, float], ...], split_id: int, lemma_id: int) -> bytes:
    flat: list[float] = []
    for low, high in record_box:
        flat.append(0.0 if low == 0.0 else low)  # merges -0.0
        flat.append(0.0 if high == 0.0 else high)
    if split_id <= 0:
        # Both other-subcase sentinel encodings (published 0/0, snapshot
        # generator -1/-1) assert the same non-claim; canonicalize.
        split_id, lemma_id = 0, 0
    return struct.pack(f"<{len(flat)}dii", *flat, split_id, lemma_id)


def _digest(payload: bytes) -> bytes:
    return hashlib.blake2b(payload, digest_size=16).digest()


def _digest_counts(path: Path, n: int) -> Counter[bytes]:
    counts: Counter[bytes] = Counter()
    for record in iter_records(path, n=n):
        counts[_digest(_canonical_payload(record.box, record.split_id, record.lemma_id))] += 1
    return counts


@dataclass(frozen=True)
class RegionDivergence:
    region_id: int
    box: tuple[tuple[float, float], ...]
    split_id: int
    lemma_id: int
    where: str  # "published-only" | "regenerated-only"


@dataclass(frozen=True)
class DiffResult:
    published_records: int
    regenerated_records: int
    matched_records: int
    findings: tuple[RegionDivergence, ...]
    findings_truncated: bool

    @property
    def clean(self) -> bool:
        return not self.findings


def _localize(
    path: Path, n: int, wanted: Counter[bytes], where: str
) -> Iterator[RegionDivergence]:
    remaining = Counter(wanted)
    for record in iter_records(path, n=n):
        if not remaining:
            return
        d = _digest(
            _canonical_payload(record.box, record.split_id, record.lemma_id)
        )
        if remaining.get(d, 0) > 0:
            remaining[d] -= 1
            yield RegionDivergence(
                region_id=record.region_id,
                box=record.box,
                split_id=record.split_id,
                lemma_id=record.lemma_id,
                where=where,
            )


def diff_boxes_only(published: Path, regenerated: Path, n: int) -> tuple[int, int]:
    """Secondary lens: multiset comparison of box bounds alone (identities
    ignored), separating re-tilings from re-certifications of the same
    tiling."""
    def counts(path: Path) -> Counter[bytes]:
        c: Counter[bytes] = Counter()
        for record in iter_records(path, n=n):
            flat = [0.0 if x == 0.0 else x for lh in record.box for x in lh]
            c[_digest(struct.pack(f"<{len(flat)}d", *flat))] += 1
        return c

    pub, reg = counts(published), counts(regenerated)
    return sum((pub - reg).values()), sum((reg - pub).values())


def semantic_diff(published: Path, regenerated: Path, n: int) -> DiffResult:
    pub = _digest_counts(published, n)
    reg = _digest_counts(regenerated, n)

    pub_only = pub - reg
    reg_only = reg - pub
    matched = sum((pub & reg).values())

    findings: list[RegionDivergence] = []
    truncated = False
    for path, only, where in (
        (published, pub_only, "published-only"),
        (regenerated, reg_only, "regenerated-only"),
    ):
        total_missing = sum(only.values())
        if total_missing > _MAX_LOCALIZED:
            truncated = True
        budget: Counter[bytes] = Counter()
        picked = 0
        for digest, count in only.items():
            take = min(count, _MAX_LOCALIZED - picked)
            if take <= 0:
                break
            budget[digest] = take
            picked += take
        findings.extend(_localize(path, n, budget, where))

    return DiffResult(
        published_records=sum(pub.values()),
        regenerated_records=sum(reg.values()),
        matched_records=matched,
        findings=tuple(findings),
        findings_truncated=truncated,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    from dataclasses import asdict
    from datetime import datetime, timezone

    parser = argparse.ArgumentParser(prog="steiner_audit.semantic_diff")
    parser.add_argument("published", type=Path)
    parser.add_argument("regenerated", type=Path)
    parser.add_argument("-n", type=int, required=True, help="variables per box")
    parser.add_argument("--out", type=Path, required=True,
                        help="findings artifact (JSON)")
    args = parser.parse_args(argv)

    result = semantic_diff(args.published, args.regenerated, n=args.n)
    boxes_pub_only, boxes_reg_only = diff_boxes_only(
        args.published, args.regenerated, n=args.n
    )

    def jsonable_findings() -> list[dict[str, object]]:
        # keep the artifact strict JSON: unbounded tops as the string "inf",
        # the same convention capsule.json uses
        out = []
        for f in result.findings:
            d = asdict(f)
            d["box"] = [
                [low, "inf" if high == float("inf") else high]
                for (low, high) in f.box
            ]
            out.append(d)
        return out

    doc = {
        "schema": "steiner-audit/semantic-diff/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "published": str(args.published),
        "regenerated": str(args.regenerated),
        "published_records": result.published_records,
        "regenerated_records": result.regenerated_records,
        "matched_records": result.matched_records,
        "divergent_per_side": result.published_records - result.matched_records,
        "box_multiset_divergence": {
            "published_only": boxes_pub_only,
            "regenerated_only": boxes_reg_only,
        },
        "findings_localized": jsonable_findings(),
        "findings_truncated": result.findings_truncated,
        "clean": result.clean,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2) + "\n")
    print(
        f"matched {result.matched_records}/{result.published_records}; "
        f"box-only divergence {boxes_pub_only}+{boxes_reg_only}; -> {args.out}"
    )
    return 0 if result.clean else 2


if __name__ == "__main__":
    import sys

    sys.exit(main())

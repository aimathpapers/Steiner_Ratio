"""Semantic diff at its boundary: two small datasets in, findings out."""

import random
from pathlib import Path

from steiner_audit.records import RegionRecord, write_records
from steiner_audit.semantic_diff import semantic_diff

N = 5


def _records(count: int = 50) -> list[RegionRecord]:
    rng = random.Random(7)
    out = []
    for i in range(count):
        lows = [rng.choice([0.0, 0.25, 0.5, 1.0]) for _ in range(N)]
        box = tuple((low, low + rng.choice([0.25, 0.5, 1.0])) for low in lows)
        out.append(
            RegionRecord(
                region_id=i + 1,
                box=box,
                split_id=rng.randint(1, 158),
                lemma_id=rng.randint(0, 8),
            )
        )
    return out


def test_benign_nondeterminism_produces_no_findings(tmp_path: Path) -> None:
    """Reordered records with renumbered region ids (and -0.0 lows) match."""
    published = _records()
    shuffled = list(published)
    random.Random(11).shuffle(shuffled)
    regenerated = [
        RegionRecord(
            region_id=900 + i,  # fresh numbering
            box=tuple(
                (-0.0 if low == 0.0 else low, high) for (low, high) in r.box
            ),
            split_id=r.split_id,
            lemma_id=r.lemma_id,
        )
        for i, r in enumerate(shuffled)
    ]
    pub_path, reg_path = tmp_path / "pub.bin", tmp_path / "reg.bin"
    write_records(pub_path, published, n=N)
    write_records(reg_path, regenerated, n=N)

    result = semantic_diff(pub_path, reg_path, n=N)
    assert result.clean
    assert result.matched_records == 50
    assert result.published_records == result.regenerated_records == 50


def test_injected_divergence_is_detected_and_localized(tmp_path: Path) -> None:
    published = _records()
    regenerated = list(published)
    # a bound nudged by one representable step, and a dropped record
    victim = regenerated[10]
    nudged_box = list(victim.box)
    low, high = nudged_box[2]
    nudged_box[2] = (low, high + 2.0 ** -20)
    regenerated[10] = RegionRecord(
        region_id=victim.region_id,
        box=tuple(nudged_box),
        split_id=victim.split_id,
        lemma_id=victim.lemma_id,
    )
    dropped = regenerated.pop(33)

    pub_path, reg_path = tmp_path / "pub.bin", tmp_path / "reg.bin"
    write_records(pub_path, published, n=N)
    write_records(reg_path, regenerated, n=N)

    result = semantic_diff(pub_path, reg_path, n=N)
    assert not result.clean
    assert result.published_records == 50
    assert result.regenerated_records == 49
    assert result.matched_records == 48

    pub_side = {f.region_id for f in result.findings if f.where == "published-only"}
    reg_side = {f.region_id for f in result.findings if f.where == "regenerated-only"}
    # the nudged record appears on both sides; the dropped one only on the
    # published side, all localized to their region ids
    assert pub_side == {victim.region_id, dropped.region_id}
    assert reg_side == {victim.region_id}
    assert not result.findings_truncated


def test_sentinel_encodings_are_the_same_claim(tmp_path: Path) -> None:
    """Published 0/0 and generator -1/-1 sentinels canonicalize together."""
    box = tuple((0.0, 1.0) for _ in range(N))
    published = [RegionRecord(region_id=1, box=box, split_id=0, lemma_id=0)]
    regenerated = [RegionRecord(region_id=1, box=box, split_id=-1, lemma_id=-1)]
    pub_path, reg_path = tmp_path / "pub.bin", tmp_path / "reg.bin"
    write_records(pub_path, published, n=N)
    write_records(reg_path, regenerated, n=N)
    assert semantic_diff(pub_path, reg_path, n=N).clean


def test_duplicate_multiplicity_counts(tmp_path: Path) -> None:
    """The diff is a multiset comparison: extra copies are findings."""
    published = _records(10)
    regenerated = published + [published[3]]  # duplicated claim
    pub_path, reg_path = tmp_path / "pub.bin", tmp_path / "reg.bin"
    write_records(pub_path, published, n=N)
    write_records(reg_path, regenerated, n=N)

    result = semantic_diff(pub_path, reg_path, n=N)
    assert not result.clean
    (finding,) = result.findings
    assert finding.where == "regenerated-only"
    assert finding.region_id == published[3].region_id

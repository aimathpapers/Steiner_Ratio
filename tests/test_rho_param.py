"""Ticket #15 seam: rho as an exact-rational parameter of the whole stack.

The kernel-boundary fixture (split 1, where F = rho*|AB| + |rB| - (b+s+1))
makes the rho dependence hand-checkable: GOOD_BOX passes at rho = 8559/10000
with margin ~0.15, and its worst vertex crosses zero near rho ~ 0.9936, so
999/1000 must flip the verdict to a certified-positive failure. No float rho
appears anywhere: rhos are fmpq end to end, mpf on the oracle side.
"""

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from flint import fmpq

from steiner_audit.arbcalc import RHO_M1, parse_rho, rho_str
from steiner_audit.capsule import generate_capsule, replay_capsule
from steiner_audit.kernel import (
    Verdict,
    verify_record_adr0004,
    verify_record_vertex_parity,
)
from steiner_audit.records import RegionRecord
from steiner_audit.status import best_certified_rho

from test_kernel_boundary import FAMILY, F_GE_D, GOOD_BOX, SPLITS

GOOD_RECORD = RegionRecord(region_id=1, box=GOOD_BOX, split_id=1, lemma_id=0)


# --- exact-rational parsing / canonical formatting ---------------------------

def test_parse_rho_fraction_and_decimal_agree() -> None:
    assert parse_rho("8559/10000") == fmpq(8559, 10000)
    assert parse_rho("0.8559") == fmpq(8559, 10000)
    assert parse_rho("0.86") == fmpq(43, 50)  # exact, reduced


def test_parse_rho_rejects_out_of_range_and_junk() -> None:
    for bad in ("0", "1", "1.5", "-0.5", "abc", "0.8559000000000000001x"):
        with pytest.raises(ValueError):
            parse_rho(bad)


def test_rho_str_is_canonical_p_over_q() -> None:
    assert rho_str(fmpq(8559, 10000)) == "8559/10000"
    assert rho_str(fmpq(43, 50)) == "43/50"
    assert rho_str(parse_rho(rho_str(fmpq(866, 1000)))) == "433/500"


# --- kernel boundary: the verdict depends on rho ----------------------------

def test_good_region_passes_at_m1_rho_and_stamps_it() -> None:
    v = verify_record_vertex_parity(GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=RHO_M1)
    assert v.ok and v.mode == "vertex_parity"
    assert v.rho == "8559/10000"


def test_good_region_still_passes_at_lower_rho() -> None:
    v = verify_record_vertex_parity(
        GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=fmpq(1, 2)
    )
    assert v.ok
    assert v.rho == "1/2"


def test_good_region_fails_certified_positive_at_high_rho() -> None:
    v = verify_record_vertex_parity(
        GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=fmpq(999, 1000)
    )
    assert not v.ok and v.mode == "failed"
    assert v.reason is not None and "certified positive" in v.reason
    assert v.rho == "999/1000"


def test_full_box_closes_at_lower_rho() -> None:
    v = verify_record_adr0004(GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=fmpq(1, 2))
    assert v.ok and v.mode == "full_box"
    assert v.fullbox_outcome == "closed"
    assert v.rho == "1/2"


def test_verdict_rows_without_rho_read_as_m1() -> None:
    """Pre-#15 verdicts.jsonl rows (no rho key) were all at 8559/10000."""
    row = asdict(
        verify_record_vertex_parity(GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=RHO_M1)
    )
    del row["rho"]
    assert Verdict(**json.loads(json.dumps(row))).rho == "8559/10000"


# --- capsule replay honors the capsule's rho --------------------------------

def test_capsule_confirms_defect_only_at_the_capsule_rho(tmp_path: Path) -> None:
    """The same good region is a genuine defect at rho = 999/1000; the replay
    (independent mpmath stack) must confirm it there and refuse it at M1 rho."""
    high = generate_capsule(
        GOOD_RECORD, FAMILY, F_GE_D, SPLITS[0], tmp_path / "high",
        rho=fmpq(999, 1000),
    )
    assert json.loads((high / "capsule.json").read_text())["rho"] == "999/1000"
    result = replay_capsule(high)
    assert result.confirmed, result.output

    m1 = generate_capsule(
        GOOD_RECORD, FAMILY, F_GE_D, SPLITS[0], tmp_path / "m1", rho=RHO_M1
    )
    result = replay_capsule(m1)
    assert not result.confirmed
    assert "NOT CONFIRMED" in result.output


# --- status: best certified rho ---------------------------------------------

def _meta(family: str, subcase: str, rho: str | None, counts: dict[str, int],
          sample: int | None = None, finished: bool = True) -> tuple[dict, dict]:
    meta = {
        "family": family, "subcase": subcase, "sample": sample, "limit": None,
        "finished_utc": "2026-08-13T00:00:00+00:00" if finished else None,
    }
    if rho is not None:
        meta["rho"] = rho
    return meta, counts


def test_best_certified_rho_full_clean_runs_only() -> None:
    totals = {"d_regular/f_ge_d": 100, "d_regular/f_le_d": 50}
    runs = [
        # full clean run, pre-#15 meta (no rho key) -> counts as 8559/10000
        _meta("d_regular", "f_ge_d", None, {"vertex_parity": 90, "skipped": 10}),
        # higher rho, full and clean -> the best for this case
        _meta("d_regular", "f_ge_d", "433/500", {"vertex_parity": 90, "skipped": 10}),
        # even higher rho but dirty -> ignored
        _meta("d_regular", "f_ge_d", "87/100",
              {"vertex_parity": 89, "skipped": 10, "failed": 1}),
        # higher rho but a sample -> ignored
        _meta("d_regular", "f_ge_d", "9/10", {"vertex_parity": 10}, sample=10),
        # incomplete coverage (30 of 50) -> ignored
        _meta("d_regular", "f_le_d", "433/500", {"vertex_parity": 30}),
        _meta("d_regular", "f_le_d", "8559/10000",
              {"vertex_parity": 40, "skipped": 10}),
    ]
    best = best_certified_rho(totals, runs)
    assert best["d_regular/f_ge_d"] == fmpq(433, 500)
    assert best["d_regular/f_le_d"] == fmpq(8559, 10000)


def test_best_certified_rho_missing_case_has_no_entry() -> None:
    totals = {"d_regular/f_ge_d": 100, "d_regular/f_le_d": 50}
    runs = [_meta("d_regular", "f_ge_d", None, {"vertex_parity": 100})]
    best = best_certified_rho(totals, runs)
    assert "d_regular/f_le_d" not in best


def test_best_certified_rho_requires_the_pinned_certificate() -> None:
    """A full clean run over some other --cert file certifies nothing about
    the corpus, however equal its record count (spec-review finding)."""
    totals = {"d_regular/f_ge_d": 100}
    meta, counts = _meta(
        "d_regular", "f_ge_d", "433/500", {"vertex_parity": 100}
    )
    meta["certificate_sha256"] = "aaaa"
    expected = {"d_regular/f_ge_d": "bbbb"}
    assert best_certified_rho(totals, [(meta, counts)], expected) == {}
    assert best_certified_rho(
        totals, [(meta, counts)], {"d_regular/f_ge_d": "aaaa"}
    ) == {"d_regular/f_ge_d": fmpq(433, 500)}
    # no expectation map -> no filtering (hermetic/test environments)
    assert best_certified_rho(totals, [(meta, counts)]) != {}


# --- triage: their checker speaks only for the published rho ----------------

def test_triage_refuses_their_verdict_at_non_m1_rho(tmp_path: Path) -> None:
    from steiner_audit.crosscheck import TheirVerdict, TriageQueue

    queue = TriageQueue(tmp_path / "queue.jsonl")
    verdict = verify_record_vertex_parity(
        GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=fmpq(999, 1000)
    )
    entry = queue.open_from_verdict(FAMILY, F_GE_D, verdict)
    with pytest.raises(ValueError, match="8559/10000"):
        queue.apply_our_bug_first(
            entry, GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=fmpq(999, 1000),
            their_verdict=TheirVerdict(
                passed=True, verified_count=1, raw_tail="fixture"
            ),
        )
    # without their_verdict the high-precision rerun may proceed at any rho
    entry = queue.apply_our_bug_first(
        entry, GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=fmpq(999, 1000)
    )
    assert entry.evidence["our_high_prec_rerun"]["rho"] == "999/1000"


# --- regression: the committed pre-#15 baseline reproduces at M1 rho --------

@pytest.mark.real_data
@pytest.mark.parametrize(
    "case_dir", ["d_regular_f_ge_d", "d_steiner_f_le_d"]
)
def test_real_data_sample_reproduces_pre_refactor_baseline(case_dir: str) -> None:
    """Acceptance criterion 3, encoded: tests/data/rho_regression holds
    sample runs produced by the pre-#15 code (run.json pins code_revision
    63bff75); the refactored stack must reproduce their verdicts exactly at
    rho = 8559/10000, modulo the new rho stamp."""
    import random

    from steiner_audit.case import parse_splits
    from steiner_audit.cases import by_name
    from steiner_audit.records import count_records, read_record_at
    from steiner_audit.verify import cert_path, splits_path

    base = Path(__file__).parent / "data" / "rho_regression" / case_dir
    meta = json.loads((base / "run.json").read_text())
    rows = [
        json.loads(line)
        for line in (base / "verdicts.jsonl").read_text().splitlines() if line
    ]
    assert len(rows) == meta["sample"]
    family = by_name(meta["family"])
    subcase = family.subcases[meta["subcase"]]
    splits = parse_splits(splits_path(meta["family"]).read_text(), family)
    cert = cert_path(meta["family"], meta["subcase"])
    n = len(subcase.box_vars)
    total = count_records(cert, n)
    assert total == meta["records_in_file"], "dataset changed under the test"

    rng = random.Random(meta["seed"])
    indices = sorted(rng.sample(range(total), meta["sample"]))
    spot = 60  # rows are written in sorted-index order; check a prefix
    for idx, expected in zip(indices[:spot], rows[:spot]):
        record = read_record_at(cert, idx, n=n, n_splits=len(splits))
        got = asdict(
            verify_record_adr0004(
                record, family, subcase, splits,
                fullbox_budget=meta["fullbox_budget"], rho=RHO_M1,
            )
        )
        assert got.pop("rho") == "8559/10000"
        assert got == expected, f"record index {idx} diverged"


# --- CLI: --rho lands in run.json and every verdict row ---------------------

@pytest.mark.real_data
def test_cli_rho_flag_stamps_run_and_verdicts(tmp_path: Path) -> None:
    from steiner_audit.verify import main

    out = tmp_path / "run"
    rc = main([
        "--family", "d_regular", "--subcase", "f_ge_d",
        "--limit", "5", "--mode", "vertex-parity", "--rho", "0.86",
        "--out", str(out),
    ])
    # whether these records still verify at 0.86 is the ceiling search's
    # question (#16), not this test's: only the stamping is asserted
    assert rc in (0, 1)
    meta = json.loads((out / "run.json").read_text())
    assert meta["rho"] == "43/50"
    rows = [
        json.loads(line)
        for line in (out / "verdicts.jsonl").read_text().splitlines() if line
    ]
    assert rows and all(row["rho"] == "43/50" for row in rows)

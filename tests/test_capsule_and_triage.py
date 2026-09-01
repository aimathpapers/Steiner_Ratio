"""Capsule generation + the ADR-0005 gate, on fixture defects.

The capsule replay is executed exactly as a third party would run it
(subprocess, current Python, mpmath only). The triage gate tests prove there
is no path to "reportable" without our-bug-first evidence, their checker's
agreement, and a passing capsule.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from steiner_audit.arbcalc import RHO_M1
from steiner_audit.capsule import CapsuleResult, generate_capsule, replay_capsule
from steiner_audit.crosscheck import TheirVerdict, TriageQueue
from steiner_audit.kernel import verify_record_vertex_parity
from steiner_audit.records import RegionRecord

from test_kernel_boundary import BAD_BOX, FAMILY, F_GE_D, GOOD_BOX, SPLITS

BAD_RECORD = RegionRecord(region_id=42, box=BAD_BOX, split_id=1, lemma_id=0)
GOOD_RECORD = RegionRecord(region_id=7, box=GOOD_BOX, split_id=1, lemma_id=0)


def _capsule(tmp_path: Path, record: RegionRecord) -> CapsuleResult:
    directory = generate_capsule(
        record,
        FAMILY,
        F_GE_D,
        SPLITS[record.split_id - 1],
        tmp_path / f"capsule_{record.region_id}",
        provenance={"fixture": True},
        rho=RHO_M1,
    )
    assert (directory / "capsule.json").exists()
    assert (directory / "README.md").exists()
    return replay_capsule(directory)


def test_capsule_confirms_fixture_defect(tmp_path: Path) -> None:
    result = _capsule(tmp_path, BAD_RECORD)
    assert result.confirmed, result.output
    assert "DEFECT CONFIRMED" in result.output


def test_capsule_refuses_good_region(tmp_path: Path) -> None:
    result = _capsule(tmp_path, GOOD_RECORD)
    assert not result.confirmed
    assert "NOT CONFIRMED" in result.output


def _triaged_entry(tmp_path: Path, their_passed: bool):
    queue = TriageQueue(tmp_path / "queue.jsonl")
    verdict = verify_record_vertex_parity(
        BAD_RECORD, FAMILY, F_GE_D, SPLITS, rho=RHO_M1
    )
    assert not verdict.ok
    entry = queue.open_from_verdict(FAMILY, F_GE_D, verdict)
    entry = queue.apply_our_bug_first(
        entry, BAD_RECORD, FAMILY, F_GE_D, SPLITS, rho=RHO_M1,
        their_verdict=TheirVerdict(
            passed=their_passed, verified_count=1 if their_passed else None,
            raw_tail="fixture",
        ),
    )
    return queue, entry


def test_gate_requires_capsule_confirmation(tmp_path: Path) -> None:
    queue, entry = _triaged_entry(tmp_path, their_passed=False)
    assert entry.status == "open"  # still failing after high-prec re-run

    fake = CapsuleResult(directory=tmp_path, confirmed=False, output="nope")
    with pytest.raises(ValueError, match="capsule replay did not confirm"):
        queue.mark_reportable(entry, fake)


def test_gate_requires_their_agreement(tmp_path: Path) -> None:
    queue, entry = _triaged_entry(tmp_path, their_passed=True)
    good = _capsule(tmp_path, BAD_RECORD)
    with pytest.raises(ValueError, match="their checker has not confirmed"):
        queue.mark_reportable(entry, good)


def test_gate_requires_our_bug_first_evidence(tmp_path: Path) -> None:
    queue = TriageQueue(tmp_path / "queue.jsonl")
    verdict = verify_record_vertex_parity(
        BAD_RECORD, FAMILY, F_GE_D, SPLITS, rho=RHO_M1
    )
    entry = queue.open_from_verdict(FAMILY, F_GE_D, verdict)
    good = _capsule(tmp_path, BAD_RECORD)
    with pytest.raises(ValueError, match="our-bug-first triage has not run"):
        queue.mark_reportable(entry, good)


def test_full_gate_path_reaches_reportable(tmp_path: Path) -> None:
    queue, entry = _triaged_entry(tmp_path, their_passed=False)
    result = _capsule(tmp_path, BAD_RECORD)
    entry = queue.mark_reportable(entry, result)
    assert entry.status == "reportable"

    # the queue reloads from disk with the final state
    reloaded = TriageQueue(tmp_path / "queue.jsonl")
    assert reloaded.entries[entry.entry_id].status == "reportable"


def test_our_bug_closes_when_high_precision_passes(tmp_path: Path) -> None:
    """A region that passes on re-run is closed as our_bug, not escalated."""
    queue = TriageQueue(tmp_path / "queue.jsonl")
    verdict = verify_record_vertex_parity(
        GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=RHO_M1
    )
    entry = queue.open_from_verdict(FAMILY, F_GE_D, replace(verdict, ok=False))
    entry = queue.apply_our_bug_first(
        entry, GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=RHO_M1
    )
    assert entry.status == "our_bug"

"""Verifier-boundary seam for full-box verification (ADR-0004).

The fixture box (b in [1/16,1/8], s in [4,4.5]) has F <= -0.146 at every
vertex of split 1, but interval evaluation cannot see the |rB| - s
cancellation, so the whole-box enclosure spans roughly +/-1 and full-box
must sub-split to close. The irrelevant variables c, d, e are pinned to
[0, 1/64] so widest-dimension bisection works on the variables F actually
depends on.
"""

import math

from steiner_audit.arbcalc import RHO_M1
from steiner_audit.kernel import (
    verify_record_adr0004,
    verify_record_vertex_parity,
)
from steiner_audit.records import RegionRecord

from test_kernel_boundary import FAMILY, F_GE_D, SPLITS

NARROW = (0.0, 0.015625)
WIDE_BOX = ((0.0625, 0.125), NARROW, NARROW, (4.0, 4.5), NARROW)
BAD_BOX = ((1.0, 1.0), NARROW, NARROW, (1.0, 1.0), NARROW)


def adr0004(record: RegionRecord, budget: int = 200):
    return verify_record_adr0004(
        record, FAMILY, F_GE_D, SPLITS, fullbox_budget=budget, rho=RHO_M1
    )


def test_vertex_parity_passes_but_full_box_needs_subdivision() -> None:
    record = RegionRecord(region_id=1, box=WIDE_BOX, split_id=1, lemma_id=0)
    parity = verify_record_vertex_parity(
        record, FAMILY, F_GE_D, SPLITS, rho=RHO_M1
    )
    assert parity.mode == "vertex_parity" and parity.ok

    v = adr0004(record)
    assert v.mode == "full_box"
    assert v.ok
    assert v.fullbox_outcome == "closed"
    assert v.subboxes_used > 1  # the single whole-box enclosure does not close


def test_budget_exhaustion_falls_back_to_vertex_parity() -> None:
    record = RegionRecord(region_id=2, box=WIDE_BOX, split_id=1, lemma_id=0)
    v = adr0004(record, budget=4)
    assert v.mode == "vertex_parity"
    assert v.ok
    assert v.fullbox_outcome == "budget_exhausted"
    assert v.subboxes_used == 4
    assert v.reason is not None and "full-box" in v.reason


def test_unbounded_box_is_not_attemptable() -> None:
    box = ((0.0625, 0.125), NARROW, NARROW, (4.0, 4.5), (1.0, math.inf))
    record = RegionRecord(region_id=3, box=box, split_id=1, lemma_id=0)
    v = adr0004(record)
    assert v.mode == "vertex_parity"
    assert v.ok
    assert v.fullbox_outcome == "not_attemptable"


def test_failing_region_reports_fullbox_positive_enclosure() -> None:
    record = RegionRecord(region_id=4, box=BAD_BOX, split_id=1, lemma_id=0)
    v = adr0004(record)
    assert v.mode == "failed"
    assert not v.ok
    assert v.fullbox_outcome == "positive_enclosure"


def test_skip_and_invalid_bypass_the_full_box_attempt() -> None:
    record = RegionRecord(region_id=5, box=WIDE_BOX, split_id=3, lemma_id=0)
    v = adr0004(record)  # split 3 lacks 'f' in mono_vars -> invalid in f>=d
    assert v.mode == "invalid"
    assert v.fullbox_outcome is None

"""Ceiling-search seam (ticket #16): records in, critical-rho bounds out.

Split 1's fixture geometry makes the critical rho analytic:
F(rho) = rho*|AB| + |rB| - (b+s+1) with |AB| = sqrt(1+b+b^2) and
|rB| = sqrt(s^2+sb+b^2), so crit(b,s) = (b+s+1-|rB|)/|AB|. Over GOOD_BOX
(b in [1/16,1/8], s in [4,4.5]) the minimum sits at (1/8, 4):
crit = (5.125 - sqrt(16.515625))/sqrt(1.140625) = 0.993499...  The kernel's
certified interval must trap that value, and verification must flip exactly
across it.
"""

import math

import pytest
from flint import fmpq

from steiner_audit.arbcalc import RHO_M1
from steiner_audit.case import Split
from steiner_audit.cases import d_regular
from steiner_audit.kernel import (
    critical_rho_adr0004,
    critical_rho_vertex_parity,
    verify_record_vertex_parity,
)
from steiner_audit.records import RegionRecord

from test_kernel_boundary import BAD_BOX, FAMILY, F_GE_D, F_LE_D, GOOD_BOX, SPLITS

FIXTURE_CRIT = (5.125 - math.sqrt(16.515625)) / math.sqrt(1.140625)

GOOD_RECORD = RegionRecord(region_id=1, box=GOOD_BOX, split_id=1, lemma_id=0)

# split 1 stripped of its T* edge: F loses its rho term entirely
SPLIT_NO_TSTAR = Split(
    line_no=1,
    v_star=(d_regular.A,),
    s_minus=(1, 4, 0),
    s_plus=tuple(sorted((d_regular.R_NODE, d_regular.B))),
    t_star=(),
    mono_vars=frozenset({d_regular.VC, d_regular.VD, d_regular.VS,
                         d_regular.VE, d_regular.VF}),
)
# ...and additionally stripped of S-: F = |rB| > 0 at every rho
SPLIT_POSITIVE = Split(
    line_no=1,
    v_star=(d_regular.A,),
    s_minus=(),
    s_plus=tuple(sorted((d_regular.R_NODE, d_regular.B))),
    t_star=(),
    mono_vars=frozenset({d_regular.VC, d_regular.VD, d_regular.VS,
                         d_regular.VE, d_regular.VF}),
)


def test_fixture_critical_rho_traps_the_analytic_value() -> None:
    crit = critical_rho_vertex_parity(GOOD_RECORD, FAMILY, F_GE_D, SPLITS)
    assert crit.outcome == "bounded"
    assert crit.crit_lo is not None and crit.crit_hi is not None
    # the certified interval is tighter than float64: allow the float64
    # reference computation one ulp of slack on each side
    assert crit.crit_lo - 1e-12 <= FIXTURE_CRIT <= crit.crit_hi + 1e-12
    assert crit.crit_hi - crit.crit_lo < 1e-9  # 128-bit balls are tight
    assert 0.9934 < crit.crit_lo and crit.crit_hi < 0.9936
    # the binding vertex is b high (bit 0), s low (bit 3)
    assert crit.binding_vertex is not None
    assert crit.binding_vertex & 1 == 1
    assert (crit.binding_vertex >> 3) & 1 == 0


def test_verification_flips_exactly_across_the_critical_interval() -> None:
    below = verify_record_vertex_parity(
        GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=fmpq(9934, 10000)
    )
    above = verify_record_vertex_parity(
        GOOD_RECORD, FAMILY, F_GE_D, SPLITS, rho=fmpq(9936, 10000)
    )
    assert below.ok
    assert not above.ok and above.mode == "failed"


def test_failing_fixture_has_critical_rho_below_the_incumbent() -> None:
    record = RegionRecord(region_id=2, box=BAD_BOX, split_id=1, lemma_id=0)
    crit = critical_rho_vertex_parity(record, FAMILY, F_GE_D, SPLITS)
    assert crit.outcome == "bounded"
    assert crit.crit_hi is not None and crit.crit_hi < 8559 / 10000
    # analytic: (3 - sqrt(3)) / sqrt(3) at b = s = 1, float64 reference
    expected = (3 - math.sqrt(3)) / math.sqrt(3)
    assert crit.crit_lo is not None
    assert crit.crit_lo - 1e-12 <= expected <= crit.crit_hi + 1e-12


def test_no_tstar_and_nonpositive_s_net_is_unconstrained() -> None:
    crit = critical_rho_vertex_parity(
        GOOD_RECORD, FAMILY, F_GE_D, (SPLIT_NO_TSTAR,) + SPLITS[1:]
    )
    assert crit.outcome == "unconstrained"
    assert crit.crit_lo == math.inf and crit.crit_hi == math.inf


def test_no_tstar_and_positive_s_net_fails_at_every_rho() -> None:
    crit = critical_rho_vertex_parity(
        GOOD_RECORD, FAMILY, F_GE_D, (SPLIT_POSITIVE,) + SPLITS[1:]
    )
    assert crit.outcome == "failed_all_rho"
    assert crit.reason is not None and "certified positive" in crit.reason


def test_skip_and_sentinel_rules_mirror_verification() -> None:
    box = ((0.0625, 0.125), (0.0, 1.0), (0.5, 1.0), (4.0, 4.5), (0.0, 1.0),
           (2.0, 3.0))
    skipped = critical_rho_vertex_parity(
        RegionRecord(region_id=9, box=box, split_id=1, lemma_id=0),
        FAMILY, F_LE_D, SPLITS,
    )
    assert skipped.outcome == "skipped"
    box_bad = ((0.0625, 0.125), (0.0, 1.0), (0.5, 1.0), (4.0, 4.5),
               (0.0, 1.0), (0.0, 0.25))
    invalid = critical_rho_vertex_parity(
        RegionRecord(region_id=12, box=box_bad, split_id=0, lemma_id=0),
        FAMILY, F_LE_D, SPLITS,
    )
    assert invalid.outcome == "invalid"


def test_fullbox_certificate_is_one_sided_and_consistent() -> None:
    from test_fullbox_boundary import WIDE_BOX

    record = RegionRecord(region_id=3, box=WIDE_BOX, split_id=1, lemma_id=0)
    crit = critical_rho_adr0004(
        record, FAMILY, F_GE_D, SPLITS, drive_rho=RHO_M1
    )
    assert crit.outcome == "bounded"
    assert crit.fullbox_outcome == "closed"
    assert crit.fullbox_lo is not None and crit.crit_hi is not None
    # driving at the incumbent must certify at least (nearly) the incumbent,
    # and the box supremum can never exceed the vertex supremum
    assert crit.fullbox_lo >= 0.8558
    assert crit.fullbox_lo <= crit.crit_hi + 1e-9


def test_infinite_monotone_direction_constrains_via_finite_vertices() -> None:
    box = ((0.0625, 0.125), (0.0, 1.0), (0.0, 1.0), (4.0, 4.5),
           (1.0, math.inf))
    record = RegionRecord(region_id=4, box=box, split_id=1, lemma_id=0)
    crit = critical_rho_vertex_parity(record, FAMILY, F_GE_D, SPLITS)
    assert crit.outcome == "bounded"
    assert crit.vertices_checked == 16
    assert crit.crit_lo is not None
    assert crit.crit_lo <= FIXTURE_CRIT + 1e-12  # e does not enter split 1's F


@pytest.mark.real_data
def test_ceiling_cli_writes_coherent_artifacts(tmp_path) -> None:
    import json

    from steiner_audit.ceiling import main

    out = tmp_path / "ceiling_run"
    rc = main([
        "--family", "d_regular", "--subcase", "f_ge_d",
        "--limit", "300", "--bottom", "5", "--out", str(out),
    ])
    assert rc == 0
    summary = json.loads((out / "ceiling.json").read_text())
    assert summary["analyzed"] == 300
    assert not summary["exhaustive"]
    assert sum(summary["outcome_counts"].values()) == 300
    rows = [
        json.loads(line)
        for line in (out / "bottlenecks.jsonl").read_text().splitlines()
        if line
    ]
    assert len(rows) <= 5
    his = [row["crit_hi"] for row in rows]
    assert his == sorted(his)
    if summary["ceiling_hi"] is not None:
        assert summary["ceiling_lo"] <= summary["ceiling_hi"]
        assert his and math.isclose(
            his[0], summary["ceiling_hi"], rel_tol=0, abs_tol=0
        )
        # every analyzed record passed M1 verification, so the sampled
        # ceiling estimate cannot sit below the incumbent
        assert summary["ceiling_hi"] >= 8559 / 10000

"""Verifier-boundary seam: certificate records in, per-region verdicts out.

Fixtures are miniature hand-crafted certificates over the real d_regular
vocabulary. The known-good and must-fail boxes were chosen by hand for
split 1 (V*={A}, S-={(B,s),(s,r),(A,s)}, S+=(r,B), T*={(A,B)}), where
F = rho*|AB| + |rB| - (b + s + 1) depends only on b and s:
at (b,s)=(1/16..1/8, 4..4.5) every vertex gives F < -0.1, while at
(b,s)=(1,1) the value is +0.214..., certified positive.
"""

import math
from pathlib import Path

import pytest

from steiner_audit.arbcalc import RHO_M1
from steiner_audit.case import Split
from steiner_audit.cases import d_regular
from steiner_audit.kernel import Verdict, verify_record_vertex_parity
from steiner_audit.records import RegionRecord, iter_records, write_records

FAMILY = d_regular.FAMILY
F_GE_D = FAMILY.subcases["f_ge_d"]
F_LE_D = FAMILY.subcases["f_le_d"]

# Split 1 of the real d_regular splits.txt, transcribed as a literal so this
# seam needs no vendor snapshot.
SPLIT_1 = Split(
    line_no=1,
    v_star=(d_regular.A,),
    s_minus=(1, 4, 0),  # (B,s), (s,r), (A,s)
    s_plus=tuple(sorted((d_regular.R_NODE, d_regular.B))),
    t_star=((d_regular.A, d_regular.B),),
    mono_vars=frozenset({d_regular.VC, d_regular.VD, d_regular.VS, d_regular.VE, d_regular.VF}),
)
# Same split but T* prices A against the trapped point X via the lemma table.
SPLIT_2_AX = Split(
    line_no=2,
    v_star=(d_regular.A,),
    s_minus=(1, 4, 0),
    s_plus=tuple(sorted((d_regular.R_NODE, d_regular.B))),
    t_star=((d_regular.A, d_regular.X),),
    mono_vars=frozenset({d_regular.VB, d_regular.VD, d_regular.VE, d_regular.VF}),
)
# A split without 'f' in mono_vars (invalid in the f>=d subcase) and with a
# 4-node S+ (invalid in the f<=d subcase).
SPLIT_3_BAD = Split(
    line_no=3,
    v_star=(d_regular.A,),
    s_minus=(1, 4, 0),
    s_plus=tuple(sorted((d_regular.A, d_regular.D, d_regular.Q, d_regular.R))),
    t_star=((d_regular.A, d_regular.B),),
    mono_vars=frozenset({d_regular.VC}),
)
SPLITS = (SPLIT_1, SPLIT_2_AX, SPLIT_3_BAD)

GOOD_BOX = ((0.0625, 0.125), (0.0, 1.0), (0.0, 1.0), (4.0, 4.5), (0.0, 1.0))
BAD_BOX = ((1.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (0.0, 1.0))


def verify(record: RegionRecord, subcase=F_GE_D) -> Verdict:
    return verify_record_vertex_parity(record, FAMILY, subcase, SPLITS, rho=RHO_M1)


def test_known_good_region_passes_vertex_parity() -> None:
    record = RegionRecord(region_id=1, box=GOOD_BOX, split_id=1, lemma_id=0)
    v = verify(record)
    assert v.mode == "vertex_parity"
    assert v.ok
    assert v.vertices_checked == 32
    assert v.prec == 128  # clean pass on the first precision rung


def test_sign_flipped_region_fails_certified_positive() -> None:
    record = RegionRecord(region_id=2, box=BAD_BOX, split_id=1, lemma_id=0)
    v = verify(record)
    assert v.mode == "failed"
    assert not v.ok
    assert v.reason is not None and "certified positive" in v.reason


def test_uncertifiable_lemma_condition_fails_the_record() -> None:
    # X_cond0 requires c <= 1; box pins c = 2, so pricing (A,X) must fail.
    box = ((0.0625, 0.125), (2.0, 2.0), (0.0, 1.0), (4.0, 4.5), (0.0, 1.0))
    record = RegionRecord(region_id=3, box=box, split_id=2, lemma_id=0)
    v = verify(record)
    assert v.mode == "failed"
    assert v.reason is not None and "condition not certified" in v.reason


def test_infinite_top_on_monotone_var_skips_those_vertices() -> None:
    box = ((0.0625, 0.125), (0.0, 1.0), (0.0, 1.0), (4.0, 4.5), (1.0, math.inf))
    record = RegionRecord(region_id=4, box=box, split_id=1, lemma_id=0)
    v = verify(record)
    assert v.mode == "vertex_parity"
    assert v.ok
    assert v.vertices_checked == 16  # e = inf vertices are not evaluable


def test_infinite_top_on_non_monotone_var_is_invalid() -> None:
    # 'b' is not in split 1's mono_vars.
    box = ((0.0625, math.inf), (0.0, 1.0), (0.0, 1.0), (4.0, 4.5), (0.0, 1.0))
    record = RegionRecord(region_id=5, box=box, split_id=1, lemma_id=0)
    v = verify(record)
    assert v.mode == "invalid"
    assert not v.ok
    assert v.reason is not None and "not monotone" in v.reason


def test_infinite_top_with_nonzero_lemma_is_invalid() -> None:
    box = ((0.0625, 0.125), (0.0, 1.0), (0.0, 1.0), (4.0, 4.5), (1.0, math.inf))
    record = RegionRecord(region_id=6, box=box, split_id=1, lemma_id=1)
    v = verify(record)
    assert v.mode == "invalid"
    assert v.reason is not None and "only lemma 0" in v.reason


def test_f_ge_d_requires_f_monotone() -> None:
    record = RegionRecord(region_id=7, box=GOOD_BOX, split_id=3, lemma_id=0)
    v = verify(record)
    assert v.mode == "invalid"
    assert v.reason is not None and "'f' in split 3 mono_vars" in v.reason


def test_f_le_d_forbids_large_s_plus() -> None:
    box = GOOD_BOX + ((0.0, 1.0),)  # n=6 layout
    record = RegionRecord(region_id=8, box=box, split_id=3, lemma_id=0)
    v = verify(record, subcase=F_LE_D)
    assert v.mode == "invalid"
    assert v.reason is not None and "|S+| > 3" in v.reason


def test_f_le_d_skips_boxes_belonging_to_other_subcase() -> None:
    # f_low = 2 > d_high = 1: the whole box violates f <= d.
    box = ((0.0625, 0.125), (0.0, 1.0), (0.5, 1.0), (4.0, 4.5), (0.0, 1.0), (2.0, 3.0))
    record = RegionRecord(region_id=9, box=box, split_id=1, lemma_id=0)
    v = verify(record, subcase=F_LE_D)
    assert v.mode == "skipped"
    assert v.ok
    assert v.reason is not None and "belongs to the f >= d subcase" in v.reason


def test_split_id_zero_skipped_when_subcase_filter_fires() -> None:
    box = ((0.0625, 0.125), (0.0, 1.0), (0.5, 1.0), (4.0, 4.5), (0.0, 1.0), (2.0, 3.0))
    record = RegionRecord(region_id=11, box=box, split_id=0, lemma_id=0)
    v = verify(record, subcase=F_LE_D)
    assert v.mode == "skipped"
    assert v.ok


def test_split_id_zero_not_skipped_is_invalid() -> None:
    box = ((0.0625, 0.125), (0.0, 1.0), (0.5, 1.0), (4.0, 4.5), (0.0, 1.0), (0.0, 0.25))
    record = RegionRecord(region_id=12, box=box, split_id=0, lemma_id=0)
    v = verify(record, subcase=F_LE_D)
    assert v.mode == "invalid"
    assert v.reason is not None and "split_id 0" in v.reason


def test_box_variable_count_mismatch_is_invalid() -> None:
    record = RegionRecord(
        region_id=10, box=GOOD_BOX + ((0.0, 1.0),), split_id=1, lemma_id=0
    )
    v = verify(record)  # n=6 box against the n=5 subcase
    assert v.mode == "invalid"


def test_end_to_end_file_to_verdicts(tmp_path: Path) -> None:
    """The whole seam: bytes on disk in, verdicts out."""
    path = tmp_path / "cert.bin"
    write_records(
        path,
        [
            RegionRecord(region_id=1, box=GOOD_BOX, split_id=1, lemma_id=0),
            RegionRecord(region_id=2, box=BAD_BOX, split_id=1, lemma_id=0),
        ],
        n=5,
    )
    verdicts = [
        verify(record) for record in iter_records(path, n=5, n_splits=len(SPLITS))
    ]
    assert [v.mode for v in verdicts] == ["vertex_parity", "failed"]
    assert [v.ok for v in verdicts] == [True, False]

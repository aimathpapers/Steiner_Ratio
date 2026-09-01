"""Splitting-function oracle seam for d_steiner (conventions: tests/README.md)."""

import random
from pathlib import Path

import pytest
from flint import arb

from steiner_audit.refmath import d_steiner as oracle
from steiner_audit.arbcalc import RHO_M1, set_precision
from steiner_audit.case import F_GE_D, F_LE_D, parse_splits
from steiner_audit.cases import d_steiner
from steiner_audit.evaluate import EvalFailure, evaluate_split

pytestmark = pytest.mark.oracle

FAMILY = d_steiner.FAMILY
N_VARS = 8

SPLITS_TXT = (
    Path(__file__).resolve().parents[1]
    / "vendor" / "Steiner-Ratio" / "certificate" / "d_steiner" / "splits.txt"
)


def dyadic_grid(count: int, seed: int) -> list[tuple[float, ...]]:
    rng = random.Random(seed)
    values = [k / 16 for k in range(1, 65)]
    return [tuple(rng.choice(values) for _ in range(N_VARS)) for _ in range(count)]


def contains(enclosure: arb, reference: object) -> bool:
    lo = float(enclosure.lower())
    hi = float(enclosure.upper())
    slack = 1e-45
    return lo - slack <= float(reference) <= hi + slack


@pytest.fixture(autouse=True)
def _prec() -> None:
    set_precision(128)


BOUND_PAIRS = [
    ((0, "AX"), d_steiner._ax_bound0),
    ((0, "VY"), d_steiner._vy_bound0),
    ((1, "AX"), d_steiner._ax_bound_poly),
    ((2, "AX"), d_steiner._ax_bound_poly),
    ((3, "S+"), d_steiner._steiner_length3),
    ((4, "S+"), d_steiner._steiner_length4),
    ((5, "AX"), d_steiner._ax_bound5),
    ((5, "UX"), d_steiner._ux_bound5),
    ((5, "VX"), d_steiner._vx_bound5),
    ((6, "S+"), d_steiner._steiner_length6),
    ((7, "S+"), d_steiner._steiner_length7),
    ((8, "AX"), d_steiner._ax_bound8),
]


@pytest.mark.parametrize("key,ours", BOUND_PAIRS, ids=[str(k) for k, _ in BOUND_PAIRS])
def test_lemma_bounds_enclose_oracle(key, ours) -> None:
    for point in dyadic_grid(60, seed=hash(key) & 0xFFFF):
        vars_arb = [arb(x) for x in point]
        pos_arb = FAMILY.get_coordinates(vars_arb)
        enclosure = ours(pos_arb, vars_arb)
        reference = oracle.BOUNDS[key](
            oracle.coordinates(*point), [oracle.mpf(x) for x in point]
        )
        assert contains(enclosure, reference), (key, point)


@pytest.mark.parametrize("lemma_id", sorted(oracle.CONDS))
def test_lemma_conditions_agree_with_oracle(lemma_id: int) -> None:
    table = FAMILY.lemma_tables[lemma_id]
    conds = {cond for cond, _ in table.values()}
    conds.discard(d_steiner._y_cond0)
    assert len(conds) == 1
    (ours,) = conds
    disagreements = []
    for point in dyadic_grid(120, seed=lemma_id):
        vars_arb = [arb(x) for x in point]
        pos_arb = FAMILY.get_coordinates(vars_arb)
        got = ours(pos_arb, vars_arb, F_GE_D)
        want = oracle.CONDS[lemma_id](
            oracle.coordinates(*point), [oracle.mpf(x) for x in point], F_GE_D
        )
        if got != want:
            disagreements.append(point)
    assert not disagreements, (lemma_id, disagreements[:5])


def test_y_cond0_is_the_f_le_d_gate() -> None:
    point = [arb(1)] * N_VARS
    pos = FAMILY.get_coordinates(point)
    assert d_steiner._y_cond0(pos, point, F_LE_D) is True
    assert d_steiner._y_cond0(pos, point, F_GE_D) is False


def _usable_lemmas(split) -> list[int]:
    out = []
    for lemma_id in range(9):
        table = FAMILY.lemma_tables[lemma_id]
        if len(split.s_plus) > 3 and split.s_plus not in table:
            continue
        if any(
            (u in FAMILY.imp_nodes or v in FAMILY.imp_nodes) and (u, v) not in table
            for (u, v) in split.t_star
        ):
            continue
        out.append(lemma_id)
    return out


TARGETED_POINTS = [
    (0.25, 4.0, 1.0, 1.0, 0.5, 0.5, 0.0625, 1.0),
    (0.5, 2.0, 2.0, 1.5, 1.0, 1.0, 2.0, 2.0),
    (0.25, 1.5, 0.5, 2.0, 0.25, 0.75, 1.25, 0.5),
    (2.0, 0.5, 3.0, 0.5, 1.5, 0.25, 0.25, 3.0),
]


@pytest.mark.real_data
def test_splitting_function_encloses_oracle_across_real_splits() -> None:
    splits = parse_splits(SPLITS_TXT.read_text(), FAMILY)
    assert len(splits) == 1418
    compared = 0
    unusable = 0
    for split in splits:
        usable = _usable_lemmas(split)
        if not usable:
            unusable += 1
            point = TARGETED_POINTS[0]
            for lemma_id in range(9):
                got = evaluate_split(
                    FAMILY, split, [arb(x) for x in point], lemma_id, F_GE_D,
                    rho=RHO_M1,
                )
                assert isinstance(got, EvalFailure), (split.line_no, lemma_id)
            continue
        needs_lemma = len(split.s_plus) > 3 or any(
            u in FAMILY.imp_nodes or v in FAMILY.imp_nodes for (u, v) in split.t_star
        )
        split_compared = 0
        for lemma_id in usable if needs_lemma else [0]:
            points = TARGETED_POINTS + dyadic_grid(
                4, seed=split.line_no * 100 + lemma_id
            )
            for point in points:
                for f_val in (F_GE_D, F_LE_D):
                    pt = list(point)
                    if f_val == F_GE_D:
                        pt[7] = pt[2]  # the f := d boundary
                    vars_arb = [arb(x) for x in pt]
                    got = evaluate_split(
                        FAMILY, split, vars_arb, lemma_id, f_val, rho=RHO_M1
                    )
                    if isinstance(got, EvalFailure):
                        continue
                    ref = oracle.splitting_function(
                        split, [oracle.mpf(x) for x in pt], lemma_id
                    )
                    assert contains(got, ref), (split.line_no, lemma_id, f_val, pt)
                    split_compared += 1
        assert split_compared > 0, f"split {split.line_no} never compared"
        compared += split_compared
    assert compared > 10000


SPOT_RHOS = [(41, 50), (8559, 10000), (87, 100)]  # below M1, M1, above M1


@pytest.mark.real_data
def test_splitting_function_encloses_oracle_at_spot_rhos() -> None:
    """Rho-parameterized F (ticket #15), d_steiner side; see the d_regular
    twin for the containment + affine-in-rho invariants."""
    from flint import fmpq

    splits = parse_splits(SPLITS_TXT.read_text(), FAMILY)
    r1, r2, r3 = (oracle.mpf(p) / oracle.mpf(q) for p, q in SPOT_RHOS)
    exercised = 0
    for split in splits[::61]:
        usable = _usable_lemmas(split)
        if not usable:
            continue
        lemma_id = usable[0]
        for point in TARGETED_POINTS[:2] + dyadic_grid(2, seed=split.line_no):
            pt = list(point)
            pt[7] = pt[2]  # the f := d boundary of the f >= d subcase
            refs = []
            for p, q in SPOT_RHOS:
                got = evaluate_split(
                    FAMILY, split, [arb(x) for x in pt], lemma_id, F_GE_D,
                    rho=fmpq(p, q),
                )
                if isinstance(got, EvalFailure):
                    break
                ref = oracle.splitting_function(
                    split, [oracle.mpf(x) for x in pt], lemma_id,
                    rho=oracle.mpf(p) / oracle.mpf(q),
                )
                assert contains(got, ref), (split.line_no, (p, q), pt)
                refs.append(ref)
            if len(refs) == len(SPOT_RHOS):
                linear_defect = (refs[2] - refs[0]) * (r2 - r1) - (
                    refs[1] - refs[0]
                ) * (r3 - r1)
                assert abs(linear_defect) < oracle.mpf(10) ** -45, (
                    split.line_no, pt
                )
                exercised += 1
    assert exercised > 20

"""Splitting-function oracle seam: Arb enclosures vs independent mpmath refs.

Every lemma bound, every lemma condition, the 3-point Steiner length, and the
composed splitting function are compared against steiner_audit/refmath/d_regular.py —
a deliberately separate implementation. Sample points are exact-float dyadics
so both stacks start from identical inputs; the oracle value must lie inside
our enclosure, and branch decisions must agree away from boundaries.
"""

import random
from pathlib import Path

import pytest
from flint import arb

from steiner_audit.refmath import d_regular as oracle
from steiner_audit.arbcalc import RHO_M1, set_precision, smt_length
from steiner_audit.case import F_GE_D, F_LE_D, parse_splits
from steiner_audit.cases import d_regular
from steiner_audit.evaluate import EvalFailure, evaluate_split

pytestmark = pytest.mark.oracle

FAMILY = d_regular.FAMILY

SPLITS_TXT = (
    Path(__file__).resolve().parents[1]
    / "vendor" / "Steiner-Ratio" / "certificate" / "d_regular" / "splits.txt"
)


def dyadic_grid(count: int, seed: int) -> list[tuple[float, ...]]:
    rng = random.Random(seed)
    values = [k / 16 for k in range(1, 65)]  # 1/16 .. 4, exact floats
    return [tuple(rng.choice(values) for _ in range(6)) for _ in range(count)]


def contains(enclosure: arb, reference: object) -> bool:
    lo = float(enclosure.lower())
    hi = float(enclosure.upper())
    slack = 1e-45  # mpmath reference rounding at 60 significant digits
    return lo - slack <= float(reference) <= hi + slack


@pytest.fixture(autouse=True)
def _prec() -> None:
    set_precision(128)


BOUND_PAIRS = [
    ((0, "AX"), d_regular._ax_bound0),
    ((0, "DY"), d_regular._dy_bound0),
    ((1, "AX"), d_regular._ax_bound_poly),
    ((2, "AX"), d_regular._ax_bound_poly),
    ((3, "S+"), d_regular._steiner_length3),
    ((4, "S+"), d_regular._steiner_length4),
    ((5, "AX"), d_regular._ax_bound5),
    ((5, "DX"), d_regular._dx_bound5),
    ((6, "S+"), d_regular._steiner_length6),
    ((7, "S+"), d_regular._steiner_length7),
    ((8, "AX"), d_regular._ax_bound8),
]


@pytest.mark.parametrize("key,ours", BOUND_PAIRS, ids=[str(k) for k, _ in BOUND_PAIRS])
def test_lemma_bounds_enclose_oracle(key, ours) -> None:
    for point in dyadic_grid(60, seed=hash(key) & 0xFFFF):
        vars_arb = [arb(x) for x in point]
        pos_arb = FAMILY.get_coordinates(vars_arb)
        enclosure = ours(pos_arb, vars_arb)
        reference = oracle.BOUNDS[key](oracle.coordinates(*point), [oracle.mpf(x) for x in point])
        assert contains(enclosure, reference), (key, point)


@pytest.mark.parametrize("lemma_id", sorted(oracle.CONDS))
def test_lemma_conditions_agree_with_oracle(lemma_id: int) -> None:
    table = FAMILY.lemma_tables[lemma_id]
    conds = {cond for cond, _ in table.values()}
    conds.discard(d_regular._y_cond0)  # trivial f_val gate, checked separately
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
    point = [arb(1)] * 6
    pos = FAMILY.get_coordinates(point)
    assert d_regular._y_cond0(pos, point, F_LE_D) is True
    assert d_regular._y_cond0(pos, point, F_GE_D) is False


def test_smt_length_all_branches_match_oracle() -> None:
    triples = [
        # all angles < 120: equilateral-ish
        ((0.0, 0.0), (2.0, 0.0), (1.0, 1.75)),
        # angle at first point > 120
        ((0.25, 0.0), (4.0, 0.25), (-3.5, 0.5)),
        # angle at second point > 120
        ((-3.5, 0.5), (0.25, 0.0), (4.0, 0.25)),
        # angle at third point > 120
        ((4.0, 0.25), (-3.5, 0.5), (0.25, 0.0)),
    ]
    for pa, pb, pc in triples:
        ours = smt_length(
            (arb(pa[0]), arb(pa[1])),
            (arb(pb[0]), arb(pb[1])),
            (arb(pc[0]), arb(pc[1])),
        )
        ref = oracle.smt_length(
            tuple(map(oracle.mpf, pa)), tuple(map(oracle.mpf, pb)), tuple(map(oracle.mpf, pc))
        )
        assert contains(ours, ref), (pa, pb, pc)


def _usable_lemmas(split) -> list[int]:
    """Lemma ids under which the split is even priceable: the S+ set and every
    trapped T* edge must have a table entry (mirrors their KeyError fail)."""
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


# Hand-picked profiles hitting the rarer lemma condition regions (lemma 5
# needs e < (2/sqrt3 - 1)c; lemma 4 needs c,e >= 1; lemma 6 needs d >= b).
TARGETED_POINTS = [
    (0.25, 4.0, 1.0, 1.0, 0.0625, 1.0),
    (0.5, 2.0, 2.0, 1.5, 2.0, 2.0),
    (0.25, 1.5, 0.5, 2.0, 1.25, 0.5),
    (2.0, 0.5, 3.0, 0.5, 0.25, 3.0),
]


@pytest.mark.real_data
def test_splitting_function_encloses_oracle_across_real_splits() -> None:
    """Full F over every real d_regular split at generic points, both f_vals.

    Every split that is priceable under some lemma must produce at least one
    value comparison; the rest must be exactly the class our evaluator (like
    their checker's KeyError path) fails at every vertex.
    """
    # 158 splits, not the research doc's "160" — recorded divergence.
    splits = parse_splits(SPLITS_TXT.read_text(), FAMILY)
    assert len(splits) == 158
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
                6, seed=split.line_no * 100 + lemma_id
            )
            for point in points:
                for f_val in (F_GE_D, F_LE_D):
                    pt = list(point)
                    if f_val == F_GE_D:
                        pt[5] = pt[2]  # the f := d boundary
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
    assert compared > 2000
    assert unusable > 0  # the unusable class exists and is exercised


SPOT_RHOS = [(41, 50), (8559, 10000), (87, 100)]  # below M1, M1, above M1


@pytest.mark.real_data
def test_splitting_function_encloses_oracle_at_spot_rhos() -> None:
    """Rho-parameterized F (ticket #15): containment at exact rationals below
    and above 8559/10000, plus the affine-in-rho identity
    (F(r3)-F(r1))*(r2-r1) == (F(r2)-F(r1))*(r3-r1) on the reference values."""
    from flint import fmpq

    splits = parse_splits(SPLITS_TXT.read_text(), FAMILY)
    r1, r2, r3 = (oracle.mpf(p) / oracle.mpf(q) for p, q in SPOT_RHOS)
    exercised = 0
    for split in splits[::7]:
        usable = _usable_lemmas(split)
        if not usable:
            continue
        lemma_id = usable[0]
        for point in TARGETED_POINTS[:2] + dyadic_grid(2, seed=split.line_no):
            pt = list(point)
            pt[5] = pt[2]  # the f := d boundary of the f >= d subcase
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


@pytest.mark.real_data
def test_affine_parts_enclose_two_rho_oracle_solve() -> None:
    """evaluate_split_parts (ticket #16): the reference (L_T*, L_S+ - L_S-)
    recovered from F at two rhos by linear solve must lie inside our part
    enclosures — the decomposition the critical-rho ceiling rests on."""
    from steiner_audit.evaluate import evaluate_split_parts

    splits = parse_splits(SPLITS_TXT.read_text(), FAMILY)
    r1, r2 = oracle.mpf(1) / 2, oracle.mpf(3) / 4
    exercised = 0
    for split in splits[::5]:
        usable = _usable_lemmas(split)
        if not usable:
            continue
        lemma_id = usable[0]
        for point in TARGETED_POINTS[:2] + dyadic_grid(2, seed=split.line_no):
            pt = list(point)
            pt[5] = pt[2]
            got = evaluate_split_parts(
                FAMILY, split, [arb(x) for x in pt], lemma_id, F_GE_D
            )
            if isinstance(got, EvalFailure):
                continue
            t_arb, s_arb = got
            f1 = oracle.splitting_function(
                split, [oracle.mpf(x) for x in pt], lemma_id, rho=r1
            )
            f2 = oracle.splitting_function(
                split, [oracle.mpf(x) for x in pt], lemma_id, rho=r2
            )
            t_ref = (f2 - f1) / (r2 - r1)
            s_ref = f1 - r1 * t_ref
            assert contains(t_arb, t_ref), (split.line_no, pt)
            assert contains(s_arb, s_ref), (split.line_no, pt)
            exercised += 1
    assert exercised > 20

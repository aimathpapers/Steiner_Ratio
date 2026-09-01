"""The d_steiner case family: geometry and lemma tables, clean-room.

Same transcription provenance discipline as d_regular (see that module's
docstring). d_steiner extends the local configuration with two further
terminals U, V hanging off D (u, v edge-length variables), replaces the
(D,Y) trapped-point fallback with (V,Y), extends lemma 5 to price (U,X) and
(V,X), and adds a symmetry skip: boxes with max(u_low, v_low) > max(b_high,
1) are covered by relabeling (their README's structural-symmetry filter).

This module deliberately does not share lemma code with d_regular even where
formulas coincide: each case directory upstream is a separate source, and
each transcription is checked against its own oracle.
"""

from __future__ import annotations

from typing import Sequence

from flint import arb

from ..arbcalc import (
    angle_le_120,
    angle_le_120_vec,
    ball_max,
    dist,
    padd,
    psub,
    rotate_ccw_60,
    smul,
    sq,
    sqrt3,
    sqrt_nonneg,
)
from ..case import F_GE_D, F_LE_D, CaseFamily, LemmaTable, Point, Subcase

NODES = ("A", "B", "D", "U", "V", "P", "Q", "R", "s", "r", "X", "Y")
A, B, D, U, V, P, Q, R, S_NODE, R_NODE, X, Y = range(12)

EDGES = (
    (A, S_NODE),  # edge 0: the unit edge
    (B, S_NODE),  # b
    (R_NODE, P),  # c
    (R_NODE, D),  # d
    (S_NODE, R_NODE),  # s
    (D, U),  # u
    (D, V),  # v
    (P, R),  # e
    (P, Q),  # f
)

VAR_NAMES = ("b", "c", "d", "s", "u", "v", "e", "f")
VB, VC, VD, VS, VU, VV, VE, VF = range(8)


def _dir0() -> Point:
    return (arb(1), arb(0))


def _dir1() -> Point:
    return (arb(1) / arb(2), sqrt3() / arb(2))


def _dir2() -> Point:
    return (arb(1) / arb(2), -(sqrt3() / arb(2)))


def get_coordinates(vars: Sequence[arb]) -> tuple[Point, ...]:
    b, c, d, s, u, v, e, f = vars
    a_pt: Point = (arb(0), arb(0))
    s_pt: Point = (arb(1), arb(0))
    b_pt = padd(s_pt, smul(b, _dir1()))
    r_pt = padd(s_pt, smul(s, _dir2()))
    p_pt = padd(r_pt, smul(-c, _dir1()))
    d_pt = padd(r_pt, smul(d, _dir0()))
    u_pt = padd(d_pt, smul(u, _dir1()))
    v_pt = padd(d_pt, smul(v, _dir2()))
    q_pt = padd(p_pt, smul(f, _dir2()))
    r_cap_pt = padd(p_pt, smul(-e, _dir0()))
    return (a_pt, b_pt, d_pt, u_pt, v_pt, p_pt, q_pt, r_cap_pt, s_pt, r_pt)


# --- Lemma 0: baseline trapped-point bounds ---------------------------------

def _x_cond0(pos: Sequence[Point], vars: Sequence[arb], f_val: int) -> bool:
    return vars[VC] <= arb(1)


def _ax_bound0(pos: Sequence[Point], vars: Sequence[arb]) -> arb:
    return ball_max(dist(pos[A], pos[R_NODE]), dist(pos[A], pos[P]))


def _y_cond0(pos: Sequence[Point], vars: Sequence[arb], f_val: int) -> bool:
    return f_val == F_LE_D


def _vy_bound0(pos: Sequence[Point], vars: Sequence[arb]) -> arb:
    return ball_max(
        dist(pos[V], pos[R_NODE]),
        dist(pos[V], pos[P]),
        dist(pos[V], pos[Q]),
    )


# --- Lemmas 1, 2, 8: trapped-point polygons for X off A ---------------------

def _ax_bound_poly(pos: Sequence[Point], vars: Sequence[arb]) -> arb:
    return ball_max(
        dist(pos[A], pos[S_NODE]),
        dist(pos[A], pos[R_NODE]),
        dist(pos[A], pos[P]),
        dist(pos[A], pos[R]),
        sqrt3() / arb(2) * (vars[VC] + vars[VE] - arb(1)),
    )


def _x_cond1(pos: Sequence[Point], vars: Sequence[arb], f_val: int) -> bool:
    c, e, s = vars[VC], vars[VE], vars[VS]
    return (
        e < arb(1) - c + arb(2) / sqrt3() * s
        and c + e >= arb(1)
    )


def _x_cond2(pos: Sequence[Point], vars: Sequence[arb], f_val: int) -> bool:
    c, e = vars[VC], vars[VE]
    return (
        e < arb(1) + (arb(2) / sqrt3() - arb(1)) * c
        and c + e >= arb(1)
    )


def _x_cond8(pos: Sequence[Point], vars: Sequence[arb], f_val: int) -> bool:
    return vars[VE] < vars[VS] + arb(1)


def _ax_bound8(pos: Sequence[Point], vars: Sequence[arb]) -> arb:
    return ball_max(
        dist(pos[A], pos[R_NODE]),
        dist(pos[A], pos[P]),
        dist(pos[A], pos[R]),
        vars[VE] + vars[VC] - arb(1),
    )


# --- Lemma 5: trapped-point bounds for X off A, U, V ------------------------

def _x_cond5(pos: Sequence[Point], vars: Sequence[arb], f_val: int) -> bool:
    return vars[VE] < (arb(2) / sqrt3() - arb(1)) * vars[VC]


def _ax_bound5(pos: Sequence[Point], vars: Sequence[arb]) -> arb:
    return ball_max(
        dist(pos[A], pos[R_NODE]),
        dist(pos[A], pos[P]),
        dist(pos[A], pos[R]),
    )


def _h_point(pos: Sequence[Point], vars: Sequence[arb]) -> Point:
    c, e = vars[VC], vars[VE]
    return psub(pos[R], smul((c - e) / arb(2), _dir2()))


def _ux_bound5(pos: Sequence[Point], vars: Sequence[arb]) -> arb:
    h = _h_point(pos, vars)
    return ball_max(
        dist(pos[U], pos[R_NODE]),
        dist(pos[U], pos[P]),
        dist(pos[U], pos[R]),
        dist(pos[U], h),
    )


def _vx_bound5(pos: Sequence[Point], vars: Sequence[arb]) -> arb:
    h = _h_point(pos, vars)
    return ball_max(
        dist(pos[V], pos[R_NODE]),
        dist(pos[V], pos[P]),
        dist(pos[V], pos[R]),
        dist(pos[V], h),
    )


# --- Lemmas 3, 4, 6, 7: valid 4-point Steiner-tree length bounds ------------

def _steiner_cond3(pos: Sequence[Point], vars: Sequence[arb], f_val: int) -> bool:
    c, d, s, e = vars[VC], vars[VD], vars[VS], vars[VE]
    vpt = padd(pos[D], rotate_ccw_60(psub(pos[Q], pos[D])))
    return (
        c + e >= arb(1)
        and e <= s + c + d + arb(2)
        and e >= arb(2) - c - d + s
        and e * (arb(2) + c + arb(3) * d + s)
        <= arb(2) + c * c + arb(3) * d + arb(2) * s + arb(3) * c * s
        + arb(3) * d * s + arb(2) * s * s
        and e <= arb(3) * s
        and angle_le_120_vec(psub(pos[D], pos[R]), psub(pos[Q], pos[A]))
        and angle_le_120(pos[A], pos[R], vpt)
        and angle_le_120(pos[R], pos[A], vpt)
    )


def _steiner_length3(pos: Sequence[Point], vars: Sequence[arb]) -> arb:
    c, d, s, e = vars[VC], vars[VD], vars[VS], vars[VE]
    uvx = (arb(1) + e + arb(3) * d + arb(2) * s + arb(3) * c) / arb(2)
    uvy = -(sqrt3() * (c + d + e - arb(1)) / arb(2))
    return sqrt_nonneg(sq(uvx) + sq(uvy))


def _steiner_cond4(pos: Sequence[Point], vars: Sequence[arb], f_val: int) -> bool:
    return vars[VC] >= arb(1) and vars[VE] >= arb(1)


def _steiner_length4(pos: Sequence[Point], vars: Sequence[arb]) -> arb:
    c, d, s, e = vars[VC], vars[VD], vars[VS], vars[VE]
    total = arb(1) + s + c + e + arb(2) * d
    return sqrt_nonneg(sq(total) - total + arb(1))


def _steiner_cond6(pos: Sequence[Point], vars: Sequence[arb], f_val: int) -> bool:
    return vars[VD] >= vars[VB]


def _steiner_length6(pos: Sequence[Point], vars: Sequence[arb]) -> arb:
    b, c, d, s, e = vars[VB], vars[VC], vars[VD], vars[VS], vars[VE]
    t1 = arb(2) * b + c + arb(2) * d + e + s
    t2 = c + arb(2) * d + e + s
    return sqrt_nonneg(sq(t1) + arb(3) * sq(t2)) / arb(2)


def _steiner_cond7(pos: Sequence[Point], vars: Sequence[arb], f_val: int) -> bool:
    c, d, s, e = vars[VC], vars[VD], vars[VS], vars[VE]
    csd = c + s + arb(2) * d
    return (
        d * (c + e - arb(1)) + e * (s + c) >= arb(0)
        and e >= (sqrt_nonneg(sq(csd) + arb(4) * d) - csd) / arb(2)
        and -(arb(2) + s - c + d) * (c + arb(2) * e + arb(2) * d)
        + arb(3) * c * (s + c + d) >= arb(0)
        and s + e >= arb(1)
        and c <= arb(1) + d + (s + e) / arb(2)
    )


def _steiner_length7(pos: Sequence[Point], vars: Sequence[arb]) -> arb:
    c, d, s, e = vars[VC], vars[VD], vars[VS], vars[VE]
    total = arb(2) * d + s + c + e
    return sqrt_nonneg(sq(total) + total + arb(1))


_AX = (A, X)
_UX = (U, X)
_VX = (V, X)
_VY = (V, Y)
_ADQR = tuple(sorted((A, D, Q, R)))
_BDQR = tuple(sorted((B, D, Q, R)))

_RAW_TABLES: tuple[dict[tuple[int, ...], tuple[object, object]], ...] = (
    {_AX: (_x_cond0, _ax_bound0), _VY: (_y_cond0, _vy_bound0)},
    {_AX: (_x_cond1, _ax_bound_poly)},
    {_AX: (_x_cond2, _ax_bound_poly)},
    {_ADQR: (_steiner_cond3, _steiner_length3)},
    {_ADQR: (_steiner_cond4, _steiner_length4)},
    {
        _AX: (_x_cond5, _ax_bound5),
        _UX: (_x_cond5, _ux_bound5),
        _VX: (_x_cond5, _vx_bound5),
    },
    {_BDQR: (_steiner_cond6, _steiner_length6)},
    {_ADQR: (_steiner_cond7, _steiner_length7)},
    {_AX: (_x_cond8, _ax_bound8)},
)


def _with_vy_fallback(
    tables: tuple[dict[tuple[int, ...], tuple[object, object]], ...],
) -> tuple[LemmaTable, ...]:
    # Their checker installs lemma 0's (V,Y) pair into every lemma table that
    # lacks one; the fallback's condition restricts it to the f <= d subcase.
    out = []
    for table in tables:
        merged = dict(table)
        merged.setdefault(_VY, (_y_cond0, _vy_bound0))
        out.append(merged)
    return tuple(out)  # type: ignore[arg-type]


LEMMA_TABLES = _with_vy_fallback(_RAW_TABLES)


def _symmetry_skip(
    box: tuple[tuple[float, float], ...], subcase: Subcase
) -> str | None:
    """Their structural-symmetry filter: WLOG max(u, v) <= max(1, b)."""
    u_low = box[subcase.box_vars.index(VU)][0]
    v_low = box[subcase.box_vars.index(VV)][0]
    b_high = box[subcase.box_vars.index(VB)][1]
    if max(u_low, v_low) > max(b_high, 1.0):
        return "max(u_low, v_low) > max(1, b_high): box covered by symmetry"
    return None


SUBCASES = {
    "f_ge_d": Subcase(
        name="f_ge_d",
        f_val=F_GE_D,
        box_vars=(VB, VC, VD, VS, VU, VV, VE),
        derived=((VF, VD),),  # verified on the f = d boundary
    ),
    "f_le_d": Subcase(
        name="f_le_d",
        f_val=F_LE_D,
        box_vars=(VB, VC, VD, VS, VU, VV, VE, VF),
    ),
}

FAMILY = CaseFamily(
    name="d_steiner",
    nodes=NODES,
    imp_nodes=frozenset({X, Y}),
    edges=EDGES,
    var_names=VAR_NAMES,
    subcases=SUBCASES,
    get_coordinates=get_coordinates,
    lemma_tables=LEMMA_TABLES,
    skip_rules=(_symmetry_skip,),
)

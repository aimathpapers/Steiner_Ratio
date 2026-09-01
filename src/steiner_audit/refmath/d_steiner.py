"""Independent mpmath reference for the d_steiner splitting functions.

Same discipline as refmath.d_regular: a separate implementation of the same
mathematics at 60 significant digits, transcribed from the d_steiner case
directory's own lemma files (they are near-copies of d_regular's but are
treated as their own source).
"""

from __future__ import annotations

from mpmath import mp, mpf, sqrt

mp.dps = 60

RHO = mpf(8559) / mpf(10000)
SQRT3 = sqrt(mpf(3))

# Node ids, matching steiner_audit.cases.d_steiner
A, B, D, U, V, P, Q, R, S_NODE, R_NODE, X, Y = range(12)

DIR0 = (mpf(1), mpf(0))
DIR1 = (mpf(1) / 2, SQRT3 / 2)
DIR2 = (mpf(1) / 2, -SQRT3 / 2)


def _add(p, q):
    return (p[0] + q[0], p[1] + q[1])


def _mul(k, p):
    return (k * p[0], k * p[1])


def coordinates(b, c, d, s, u, v, e, f):
    a_pt = (mpf(0), mpf(0))
    s_pt = (mpf(1), mpf(0))
    b_pt = _add(s_pt, _mul(b, DIR1))
    r_pt = _add(s_pt, _mul(s, DIR2))
    p_pt = _add(r_pt, _mul(-c, DIR1))
    d_pt = _add(r_pt, _mul(d, DIR0))
    u_pt = _add(d_pt, _mul(u, DIR1))
    v_pt = _add(d_pt, _mul(v, DIR2))
    q_pt = _add(p_pt, _mul(f, DIR2))
    r_cap = _add(p_pt, _mul(-e, DIR0))
    return (a_pt, b_pt, d_pt, u_pt, v_pt, p_pt, q_pt, r_cap, s_pt, r_pt)


def dist(p, q):
    return sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2)


def _angle_le_120(a, b, c):
    ux, uy = a[0] - b[0], a[1] - b[1]
    vx, vy = c[0] - b[0], c[1] - b[1]
    dot = ux * vx + uy * vy
    return dot >= -sqrt((ux * ux + uy * uy) * (vx * vx + vy * vy)) / 2


def smt_length(a, b, c):
    if not _angle_le_120(a, b, c):
        return dist(a, b) + dist(b, c)
    if not _angle_le_120(b, c, a):
        return dist(b, c) + dist(c, a)
    if not _angle_le_120(c, a, b):
        return dist(c, a) + dist(a, b)
    area = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
    d2 = dist(a, b) ** 2 + dist(b, c) ** 2 + dist(c, a) ** 2
    return sqrt(d2 / 2 + 2 * SQRT3 * area)


def rotate_ccw_60(u):
    return (u[0] / 2 - SQRT3 / 2 * u[1], SQRT3 / 2 * u[0] + u[1] / 2)


# Variables arrive as the 8-tuple (b, c, d, s, u, v, e, f).

def ax_bound0(pos, w):
    return max(dist(pos[A], pos[R_NODE]), dist(pos[A], pos[P]))


def vy_bound0(pos, w):
    return max(dist(pos[V], pos[R_NODE]), dist(pos[V], pos[P]), dist(pos[V], pos[Q]))


def ax_bound_poly(pos, w):
    b, c, d, s, u, v, e, f = w
    return max(
        dist(pos[A], pos[S_NODE]),
        dist(pos[A], pos[R_NODE]),
        dist(pos[A], pos[P]),
        dist(pos[A], pos[R]),
        SQRT3 / 2 * (c + e - 1),
    )


def ax_bound5(pos, w):
    return max(dist(pos[A], pos[R_NODE]), dist(pos[A], pos[P]), dist(pos[A], pos[R]))


def _h_point(pos, w):
    b, c, d, s, u, v, e, f = w
    return (
        pos[R][0] - (c - e) / 2 * DIR2[0],
        pos[R][1] - (c - e) / 2 * DIR2[1],
    )


def ux_bound5(pos, w):
    h = _h_point(pos, w)
    return max(
        dist(pos[U], pos[R_NODE]),
        dist(pos[U], pos[P]),
        dist(pos[U], pos[R]),
        dist(pos[U], h),
    )


def vx_bound5(pos, w):
    h = _h_point(pos, w)
    return max(
        dist(pos[V], pos[R_NODE]),
        dist(pos[V], pos[P]),
        dist(pos[V], pos[R]),
        dist(pos[V], h),
    )


def ax_bound8(pos, w):
    b, c, d, s, u, v, e, f = w
    return max(
        dist(pos[A], pos[R_NODE]),
        dist(pos[A], pos[P]),
        dist(pos[A], pos[R]),
        e + c - 1,
    )


def steiner_length3(pos, w):
    b, c, d, s, u, v, e, f = w
    uvx = (1 + e + 3 * d + 2 * s + 3 * c) / 2
    uvy = -SQRT3 * (c + d + e - 1) / 2
    return sqrt(uvx ** 2 + uvy ** 2)


def steiner_length4(pos, w):
    b, c, d, s, u, v, e, f = w
    total = 1 + s + c + e + 2 * d
    return sqrt(total ** 2 - total + 1)


def steiner_length6(pos, w):
    b, c, d, s, u, v, e, f = w
    t1 = 2 * b + c + 2 * d + e + s
    t2 = c + 2 * d + e + s
    return sqrt(t1 ** 2 + 3 * t2 ** 2) / 2


def steiner_length7(pos, w):
    b, c, d, s, u, v, e, f = w
    total = 2 * d + s + c + e
    return sqrt(total ** 2 + total + 1)


def cond0(pos, w, f_val):
    return w[1] <= 1


def cond1(pos, w, f_val):
    b, c, d, s, u, v, e, f = w
    return e < 1 - c + 2 / SQRT3 * s and c + e >= 1


def cond2(pos, w, f_val):
    b, c, d, s, u, v, e, f = w
    return e < 1 + (2 / SQRT3 - 1) * c and c + e >= 1


def cond3(pos, w, f_val):
    b, c, d, s, u, v, e, f = w
    dq = (pos[Q][0] - pos[D][0], pos[Q][1] - pos[D][1])
    vpt = _add(pos[D], rotate_ccw_60(dq))

    def vec_le_120(x, y):
        dot = x[0] * y[0] + x[1] * y[1]
        return dot >= -sqrt((x[0] ** 2 + x[1] ** 2) * (y[0] ** 2 + y[1] ** 2)) / 2

    return (
        c + e >= 1
        and e <= s + c + d + 2
        and e >= 2 - c - d + s
        and e * (2 + c + 3 * d + s)
        <= 2 + c * c + 3 * d + 2 * s + 3 * c * s + 3 * d * s + 2 * s * s
        and e <= 3 * s
        and vec_le_120(
            (pos[D][0] - pos[R][0], pos[D][1] - pos[R][1]),
            (pos[Q][0] - pos[A][0], pos[Q][1] - pos[A][1]),
        )
        and _angle_le_120(pos[A], pos[R], vpt)
        and _angle_le_120(pos[R], pos[A], vpt)
    )


def cond4(pos, w, f_val):
    return w[1] >= 1 and w[6] >= 1


def cond5(pos, w, f_val):
    b, c, d, s, u, v, e, f = w
    return e < (2 / SQRT3 - 1) * c


def cond6(pos, w, f_val):
    return w[2] >= w[0]


def cond7(pos, w, f_val):
    b, c, d, s, u, v, e, f = w
    csd = c + s + 2 * d
    return (
        d * (c + e - 1) + e * (s + c) >= 0
        and e >= (sqrt(csd ** 2 + 4 * d) - csd) / 2
        and -(2 + s - c + d) * (c + 2 * e + 2 * d) + 3 * c * (s + c + d) >= 0
        and s + e >= 1
        and c <= 1 + d + (s + e) / 2
    )


def cond8(pos, w, f_val):
    b, c, d, s, u, v, e, f = w
    return e < s + 1


CONDS = {i: fn for i, fn in enumerate(
    (cond0, cond1, cond2, cond3, cond4, cond5, cond6, cond7, cond8)
)}

BOUNDS = {
    (0, "AX"): ax_bound0,
    (0, "VY"): vy_bound0,
    (1, "AX"): ax_bound_poly,
    (2, "AX"): ax_bound_poly,
    (3, "S+"): steiner_length3,
    (4, "S+"): steiner_length4,
    (5, "AX"): ax_bound5,
    (5, "UX"): ux_bound5,
    (5, "VX"): vx_bound5,
    (6, "S+"): steiner_length6,
    (7, "S+"): steiner_length7,
    (8, "AX"): ax_bound8,
}

_TRAPPED = {
    (A, X): "AX",
    (U, X): "UX",
    (V, X): "VX",
    (V, Y): "VY",
}


def splitting_function(split, w, lemma_id, rho=None):
    """F for a Split at exact-float inputs; caller ensures conditions hold.

    rho defaults to the module's RHO, resolved at call time so a driver may
    rebind the global."""
    if rho is None:
        rho = RHO
    pos = coordinates(*w)
    t_star = mpf(0)
    for (a, b) in split.t_star:
        if a in (X, Y) or b in (X, Y):
            kind = _TRAPPED[(a, b)]
            key = (lemma_id, kind)
            if key not in BOUNDS:
                key = (0, kind)  # the (V,Y) fallback
            t_star += BOUNDS[key](pos, w)
        else:
            t_star += dist(pos[a], pos[b])

    s_minus = mpf(0)
    for edge_id in split.s_minus:
        s_minus += mpf(1) if edge_id == 0 else w[edge_id - 1]

    if len(split.s_plus) < 2:
        s_plus = mpf(0)
    elif len(split.s_plus) == 2:
        s_plus = dist(pos[split.s_plus[0]], pos[split.s_plus[1]])
    elif len(split.s_plus) == 3:
        s_plus = smt_length(*(pos[i] for i in split.s_plus))
    else:
        s_plus = BOUNDS[(lemma_id, "S+")](pos, w)

    return rho * t_star + s_plus - s_minus

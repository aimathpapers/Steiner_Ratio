"""Independent mpmath reference for the d_regular splitting functions.

A deliberately separate implementation (mpmath, 60 significant digits) of the
same mathematics: local-configuration geometry, lemma bounds, 3-point Steiner
length, and F = rho*L_T* + L_S+ - L_S-. The oracle exists because the Arb
evaluators are clean-room transcriptions — the one place a silent error
corrupts everything downstream while every verifier-boundary test still
passes on internally consistent wrong math.

Branch conditions here are evaluated in plain high-precision arithmetic (no
certification semantics); oracle points are chosen away from branch
boundaries so both implementations take the same branch.
"""

from __future__ import annotations

from mpmath import mp, mpf, sqrt

mp.dps = 60

RHO = mpf(8559) / mpf(10000)
SQRT3 = sqrt(mpf(3))

# Node ids, matching steiner_audit.cases.d_regular
A, B, D, P, Q, R, S_NODE, R_NODE, X, Y = range(10)


def coordinates(b, c, d, s, e, f):
    dir0 = (mpf(1), mpf(0))
    dir1 = (mpf(1) / 2, SQRT3 / 2)
    dir2 = (mpf(1) / 2, -SQRT3 / 2)

    def add(p, q):
        return (p[0] + q[0], p[1] + q[1])

    def mul(k, p):
        return (k * p[0], k * p[1])

    a_pt = (mpf(0), mpf(0))
    s_pt = (mpf(1), mpf(0))
    b_pt = add(s_pt, mul(b, dir1))
    r_pt = add(s_pt, mul(s, dir2))
    p_pt = add(r_pt, mul(-c, dir1))
    d_pt = add(r_pt, mul(d, dir0))
    q_pt = add(p_pt, mul(f, dir2))
    r_cap = add(p_pt, mul(-e, dir0))
    return (a_pt, b_pt, d_pt, p_pt, q_pt, r_cap, s_pt, r_pt)


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


# Lemma bounds (value only; conditions are the Arb side's job).

def ax_bound0(pos, v):
    return max(dist(pos[A], pos[R_NODE]), dist(pos[A], pos[P]))


def dy_bound0(pos, v):
    return max(dist(pos[D], pos[P]), dist(pos[D], pos[Q]))


def ax_bound_poly(pos, v):
    b, c, d, s, e, f = v
    return max(
        dist(pos[A], pos[S_NODE]),
        dist(pos[A], pos[R_NODE]),
        dist(pos[A], pos[P]),
        dist(pos[A], pos[R]),
        SQRT3 / 2 * (c + e - 1),
    )


def ax_bound5(pos, v):
    return max(dist(pos[A], pos[R_NODE]), dist(pos[A], pos[P]), dist(pos[A], pos[R]))


def dx_bound5(pos, v):
    b, c, d, s, e, f = v
    h = (
        pos[R][0] - (c - e) / 2 * mpf(1) / 2,
        pos[R][1] - (c - e) / 2 * (-SQRT3 / 2),
    )
    return max(
        dist(pos[D], pos[R_NODE]),
        dist(pos[D], pos[P]),
        dist(pos[D], pos[R]),
        dist(pos[D], h),
    )


def ax_bound8(pos, v):
    b, c, d, s, e, f = v
    return max(
        dist(pos[A], pos[R_NODE]),
        dist(pos[A], pos[P]),
        dist(pos[A], pos[R]),
        e + c - 1,
    )


def steiner_length3(pos, v):
    b, c, d, s, e, f = v
    uvx = (1 + e + 3 * d + 2 * s + 3 * c) / 2
    uvy = -SQRT3 * (c + d + e - 1) / 2
    return sqrt(uvx ** 2 + uvy ** 2)


def steiner_length4(pos, v):
    b, c, d, s, e, f = v
    total = 1 + s + c + e + 2 * d
    return sqrt(total ** 2 - total + 1)


def steiner_length6(pos, v):
    b, c, d, s, e, f = v
    t1 = 2 * b + c + 2 * d + e + s
    t2 = c + 2 * d + e + s
    return sqrt(t1 ** 2 + 3 * t2 ** 2) / 2


def steiner_length7(pos, v):
    b, c, d, s, e, f = v
    total = 2 * d + s + c + e
    return sqrt(total ** 2 + total + 1)


# Lemma conditions in plain high-precision logic (no certification), for
# agreement checks away from branch boundaries. f_val: 1 = f<=d, 2 = f>=d.

def cond0(pos, v, f_val):
    return v[1] <= 1


def cond_y0(pos, v, f_val):
    return f_val == 1


def cond1(pos, v, f_val):
    b, c, d, s, e, f = v
    return e < 1 - c + 2 / SQRT3 * s and c + e >= 1


def cond2(pos, v, f_val):
    b, c, d, s, e, f = v
    return e < 1 + (2 / SQRT3 - 1) * c and c + e >= 1


def cond3(pos, v, f_val):
    b, c, d, s, e, f = v
    vpt = (
        pos[D][0] + rotate_ccw_60((pos[Q][0] - pos[D][0], pos[Q][1] - pos[D][1]))[0],
        pos[D][1] + rotate_ccw_60((pos[Q][0] - pos[D][0], pos[Q][1] - pos[D][1]))[1],
    )
    def vec_le_120(u, w):
        dot = u[0] * w[0] + u[1] * w[1]
        return dot >= -sqrt((u[0] ** 2 + u[1] ** 2) * (w[0] ** 2 + w[1] ** 2)) / 2
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


def cond4(pos, v, f_val):
    return v[1] >= 1 and v[4] >= 1


def cond5(pos, v, f_val):
    b, c, d, s, e, f = v
    return e < (2 / SQRT3 - 1) * c


def cond6(pos, v, f_val):
    return v[2] >= v[0]


def cond7(pos, v, f_val):
    b, c, d, s, e, f = v
    csd = c + s + 2 * d
    return (
        d * (c + e - 1) + e * (s + c) >= 0
        and e >= (sqrt(csd ** 2 + 4 * d) - csd) / 2
        and -(2 + s - c + d) * (c + 2 * e + 2 * d) + 3 * c * (s + c + d) >= 0
        and s + e >= 1
        and c <= 1 + d + (s + e) / 2
    )


def cond8(pos, v, f_val):
    b, c, d, s, e, f = v
    return e < s + 1


CONDS = {
    0: cond0,
    1: cond1,
    2: cond2,
    3: cond3,
    4: cond4,
    5: cond5,
    6: cond6,
    7: cond7,
    8: cond8,
}

BOUNDS = {
    (0, "AX"): ax_bound0,
    (0, "DY"): dy_bound0,
    (1, "AX"): ax_bound_poly,
    (2, "AX"): ax_bound_poly,
    (3, "S+"): steiner_length3,
    (4, "S+"): steiner_length4,
    (5, "AX"): ax_bound5,
    (5, "DX"): dx_bound5,
    (6, "S+"): steiner_length6,
    (7, "S+"): steiner_length7,
    (8, "AX"): ax_bound8,
}


def splitting_function(split, v, lemma_id, rho=None):
    """F for a Split (steiner_audit.case.Split) at exact-float inputs.

    Lemma conditions are NOT evaluated here — the caller picks points where
    the relevant conditions hold with margin. rho defaults to the module's
    RHO, resolved at call time so a driver may rebind the global.
    """
    if rho is None:
        rho = RHO
    pos = coordinates(*v)
    t_star = mpf(0)
    for (u, w) in split.t_star:
        if u == A and w == X:
            t_star += BOUNDS[(lemma_id, "AX")](pos, v)
        elif u == D and w == X:
            t_star += BOUNDS[(lemma_id, "DX")](pos, v)
        elif u == D and w == Y:
            t_star += BOUNDS[(lemma_id, "DY")](pos, v) if (lemma_id, "DY") in BOUNDS else dy_bound0(pos, v)
        elif X in (u, w) or Y in (u, w):
            raise AssertionError(f"unhandled trapped edge {(u, w)}")
        else:
            t_star += dist(pos[u], pos[w])

    s_minus = mpf(0)
    for edge_id in split.s_minus:
        s_minus += mpf(1) if edge_id == 0 else v[edge_id - 1]

    if len(split.s_plus) < 2:
        s_plus = mpf(0)
    elif len(split.s_plus) == 2:
        s_plus = dist(pos[split.s_plus[0]], pos[split.s_plus[1]])
    elif len(split.s_plus) == 3:
        s_plus = smt_length(*(pos[i] for i in split.s_plus))
    else:
        s_plus = BOUNDS[(lemma_id, "S+")](pos, v)

    return rho * t_star + s_plus - s_minus

"""Ball-arithmetic geometry over python-flint's Arb (ADR-0003).

Comparison discipline mirrors the PKU checker's certified semantics: a
comparison is True only when it provably holds for every point of both balls
(python-flint's operators already behave this way). Any bound used where an
*upper* estimate is required is conservative under uncertainty, so a
too-cautious branch can only widen F, never shrink it.

rho is an exact rational (fmpq) everywhere — a parameter since ticket #15,
never a float — converted to a ball enclosing it at the working precision
only at the moment of evaluation. RHO_M1 = 8559/10000 is the published
bound the M1 audit verified, and the default the CLI starts from.
"""

from __future__ import annotations

from fractions import Fraction
from typing import TYPE_CHECKING

from flint import arb, ctx, fmpq

if TYPE_CHECKING:
    Point = tuple[arb, arb]

RHO_M1 = fmpq(8559, 10000)


def parse_rho(text: str) -> fmpq:
    """An exact rational rho from "p/q" or a decimal literal ("0.8559").

    Decimal strings convert exactly (0.8559 IS 8559/10000); binary-float
    rounding never enters. Anything outside (0, 1) is rejected: a Steiner
    ratio bound at or above 1 is vacuous or meaningless.
    """
    try:
        value = Fraction(text)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"not an exact rational: {text!r}") from exc
    if not 0 < value < 1:
        raise ValueError(f"rho must lie in (0, 1), got {text!r}")
    return fmpq(value.numerator, value.denominator)


def rho_str(rho: fmpq) -> str:
    """Canonical "p/q" form (always slashed, always reduced) for artifacts.

    Canonical only for rhos in parse_rho's (0, 1) range — every rho in the
    system; a negative would format with the sign on p, which parse_rho
    rejects on read-back.
    """
    return f"{rho.p}/{rho.q}"


RHO_M1_STR = rho_str(RHO_M1)


def sq(x: arb) -> arb:
    """x*x. Never use ** on balls: python-flint's __pow__ returns NaN for
    zero-containing bases (it routes inexact bases through exp/log), and
    coordinate differences of coincident points are exactly such balls."""
    return x * x


def sqrt_nonneg(x: arb) -> arb:
    """sqrt of a quantity that is non-negative by mathematics.

    Ball multiplication cannot see that x*x has both factors equal, so sums
    of squares acquire an infinitesimally negative lower bound and Arb's sqrt
    would return NaN. Clamping to the non-negative part is sound exactly
    because every call site's argument is provably >= 0 on paper (sums of
    squares; quadratics with positive discriminant-free minima). Never use
    this on a quantity that could genuinely be negative."""
    return x.nonnegative_part().sqrt()


def set_precision(prec: int) -> None:
    ctx.prec = prec


def sqrt3() -> arb:
    return arb(3).sqrt()


def padd(a: "Point", b: "Point") -> "Point":
    return (a[0] + b[0], a[1] + b[1])


def psub(a: "Point", b: "Point") -> "Point":
    return (a[0] - b[0], a[1] - b[1])


def smul(k: arb, p: "Point") -> "Point":
    return (k * p[0], k * p[1])


def norm2(p: "Point") -> arb:
    return sq(p[0]) + sq(p[1])


def dist2(a: "Point", b: "Point") -> arb:
    return norm2(psub(a, b))


def dist(a: "Point", b: "Point") -> arb:
    return sqrt_nonneg(dist2(a, b))


def dot(a: "Point", b: "Point") -> arb:
    return a[0] * b[0] + a[1] * b[1]


def cross(a: "Point", b: "Point") -> arb:
    return a[0] * b[1] - a[1] * b[0]


def angle_le_120_vec(u: "Point", v: "Point") -> bool:
    """Certified: the angle between u and v is at most 120 degrees.

    False means "could not certify", not "greater than 120".
    """
    d = dot(u, v)
    if d >= arb(0):
        return True
    return arb(4) * sq(d) <= norm2(u) * norm2(v)


def angle_le_120(a: "Point", b: "Point", c: "Point") -> bool:
    """Certified: the angle ABC (at vertex b) is at most 120 degrees."""
    return angle_le_120_vec(psub(a, b), psub(c, b))


def tri_area(a: "Point", b: "Point", c: "Point") -> arb:
    return abs(cross(psub(b, a), psub(c, a)) / arb(2))


def smt_length(a: "Point", b: "Point", c: "Point") -> arb:
    """Length of the Steiner minimal tree on three points.

    When every angle is certifiably <= 120 degrees this is the Maxwell
    formula; otherwise the two edges at the wide (or uncertifiable) vertex,
    which upper-bounds the true SMT length — conservative in the direction
    that only makes F larger.
    """
    if not angle_le_120(a, b, c):
        return dist(a, b) + dist(b, c)
    if not angle_le_120(b, c, a):
        return dist(b, c) + dist(c, a)
    if not angle_le_120(c, a, b):
        return dist(c, a) + dist(a, b)
    s = tri_area(a, b, c)
    return sqrt_nonneg(
        (dist2(a, b) + dist2(b, c) + dist2(c, a)) / arb(2)
        + arb(2) * sqrt3() * s
    )


def rotate_ccw_60(u: "Point") -> "Point":
    cos60 = arb(1) / arb(2)
    sin60 = sqrt3() / arb(2)
    return (cos60 * u[0] - sin60 * u[1], sin60 * u[0] + cos60 * u[1])


def ball_max(*values: arb) -> arb:
    out = values[0]
    for v in values[1:]:
        out = out.max(v)
    return out

"""The verification kernel: vertex-parity checks per ADR-0004.

Vertex-parity replicates their checking semantics — record-level validity
rules, subcase filters, the f := d boundary substitution, infinite endpoints
admitted only for monotone variables under lemma 0 — with two deliberate
differences: the arithmetic is Arb ball arithmetic (ADR-0003), and the vertex
enumeration visits ALL 2^n vertex assignments (bit i of the mask selects the
endpoint of box variable i). Their shipped loop indexes mask bits 1..n, which
skips the last variable's upper endpoint; parity of outcomes against their
checker is the cross-check machinery's job, not silently assumed here.

Precision escalates through a ladder before any verdict of failure or
inconclusiveness is recorded, so enclosure width is never mistaken for a
finding (our-bug-first discipline).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal, Sequence

from flint import arb, fmpq

from .arbcalc import RHO_M1_STR, rho_str, set_precision
from .case import F_GE_D, F_LE_D, CaseFamily, Split, Subcase
from .evaluate import EvalFailure, evaluate_split, evaluate_split_parts
from .records import RegionRecord

Mode = Literal[
    "full_box", "vertex_parity", "skipped", "invalid", "failed", "inconclusive"
]
FullBoxOutcome = Literal[
    "closed", "budget_exhausted", "positive_enclosure", "not_attemptable"
]

DEFAULT_PREC_LADDER = (128, 256, 512)
DEFAULT_FULLBOX_BUDGET = 200


@dataclass(frozen=True)
class Verdict:
    region_id: int
    split_id: int
    lemma_id: int
    mode: Mode
    ok: bool
    reason: str | None
    prec: int
    vertices_checked: int
    # ADR-0004 bookkeeping: how the full-box attempt went (None = not run)
    fullbox_outcome: str | None = None
    subboxes_used: int = 0
    # canonical p/q string; the default makes pre-#15 verdict rows (which
    # carry no rho key and were all at the M1 bound) read back correctly
    rho: str = RHO_M1_STR


def _var_position(subcase: Subcase, var_id: int) -> int | None:
    try:
        return subcase.box_vars.index(var_id)
    except ValueError:
        return None


def _validate_record(
    record: RegionRecord,
    family: CaseFamily,
    subcase: Subcase,
    split: Split,
) -> str | None:
    """Their verify_record's structural rules; a violation fails the record."""
    if record.n != len(subcase.box_vars):
        return (
            f"box has {record.n} variables, subcase {subcase.name} "
            f"expects {len(subcase.box_vars)}"
        )
    f_id = family.var_id("f")
    if subcase.f_val == F_GE_D and f_id not in split.mono_vars:
        return f"subcase f>=d requires 'f' in split {split.line_no} mono_vars"
    if subcase.f_val == F_LE_D and len(split.s_plus) > 3:
        return (
            f"subcase f<=d forbids |S+| > 3 (split {split.line_no} "
            f"has {len(split.s_plus)})"
        )
    for i, (_, high) in enumerate(record.box):
        if math.isinf(high):
            var = subcase.box_vars[i]
            if var not in split.mono_vars:
                return (
                    f"{family.var_names[var]}_max is infinite but "
                    f"'{family.var_names[var]}' is not monotone for split {split.line_no}"
                )
            if record.lemma_id != 0:
                return (
                    f"{family.var_names[var]}_max is infinite but record uses "
                    f"lemma {record.lemma_id} (only lemma 0 admits unbounded boxes)"
                )
    return None


def _skip_reason(
    record: RegionRecord, family: CaseFamily, subcase: Subcase
) -> str | None:
    if subcase.f_val == F_LE_D:
        f_pos = _var_position(subcase, family.var_id("f"))
        d_pos = _var_position(subcase, family.var_id("d"))
        if f_pos is not None and d_pos is not None:
            if record.box[f_pos][0] > record.box[d_pos][1]:
                return "f_low > d_high: box belongs to the f >= d subcase"
    for rule in family.skip_rules:
        reason = rule(record.box, subcase)
        if reason is not None:
            return reason
    return None


def _check_vertices(
    record: RegionRecord,
    family: CaseFamily,
    subcase: Subcase,
    split: Split,
    rho: fmpq,
) -> tuple[Literal["ok", "failed", "inconclusive"], str | None, int]:
    n = record.n
    n_vars = len(family.var_names)
    checked = 0
    for mask in range(1 << n):
        values: list[float] = []
        finite = True
        for i in range(n):
            v = record.box[i][(mask >> i) & 1]
            if math.isinf(v):
                finite = False
                break
            values.append(v)
        if not finite:
            continue  # admissibility of the infinite direction was validated above
        vars: list[arb] = [arb(0)] * n_vars
        for i, v in enumerate(values):
            vars[subcase.box_vars[i]] = arb(v)
        for target, source in subcase.derived:
            vars[target] = vars[source]
        checked += 1
        result = evaluate_split(
            family, split, vars, record.lemma_id, subcase.f_val, rho=rho
        )
        if isinstance(result, EvalFailure):
            return "failed", f"vertex {mask}: {result.reason}", checked
        if not result.is_finite():
            return "inconclusive", f"vertex {mask}: enclosure not finite", checked
        if result <= arb(0):
            continue
        if arb(0) < result:
            return (
                "failed",
                f"vertex {mask}: splitting function certified positive "
                f"(enclosure {result})",
                checked,
            )
        return (
            "inconclusive",
            f"vertex {mask}: non-positivity not certified (enclosure {result})",
            checked,
        )
    return "ok", None, checked


def _hull(low: float, high: float) -> arb:
    return arb(low).union(arb(high))


def _fullbox_attempt(
    record: RegionRecord,
    family: CaseFamily,
    subcase: Subcase,
    split: Split,
    budget: int,
    rho: fmpq,
    leaf_parts: list[tuple[arb, arb]] | None = None,
) -> tuple[FullBoxOutcome, str | None, int]:
    """Try to certify F <= 0 over the whole box by adaptive sub-splitting.

    Success removes this region's dependence on the lemma layer's
    unimodality claim for the boxed variables (ADR-0004; in the f >= d
    subcase the f-monotonicity dependence remains, since only the f = d
    boundary is boxed). Widest-dimension bisection at float midpoints,
    bounded by ``budget`` sub-box evaluations. When ``leaf_parts`` is given,
    the (L_T*, L_S+ - L_S-) enclosure of every closed leaf is appended to it
    (the ceiling search's full-box certificate inputs, ticket #16).
    """
    if any(math.isinf(high) for (_, high) in record.box):
        return "not_attemptable", "unbounded box", 0

    n_vars = len(family.var_names)
    stack = [record.box]
    evals = 0
    while stack:
        if evals >= budget:
            return (
                "budget_exhausted",
                f"{evals} sub-box evaluations without closing",
                evals,
            )
        box = stack.pop()
        evals += 1
        vars: list[arb] = [arb(0)] * n_vars
        for i, (low, high) in enumerate(box):
            vars[subcase.box_vars[i]] = _hull(low, high)
        for target, source in subcase.derived:
            vars[target] = vars[source]
        parts = evaluate_split_parts(
            family, split, vars, record.lemma_id, subcase.f_val
        )
        result: arb | EvalFailure
        if isinstance(parts, EvalFailure):
            result = parts
        else:
            result = arb(rho) * parts[0] + parts[1]
        closed = (
            not isinstance(result, EvalFailure)
            and result.is_finite()
            and result <= arb(0)
        )
        if closed:
            if leaf_parts is not None and not isinstance(parts, EvalFailure):
                leaf_parts.append(parts)
            continue
        if (
            not isinstance(result, EvalFailure)
            and result.is_finite()
            and arb(0) < result
        ):
            # Certified positive throughout this sub-box: with passing
            # vertices this is lemma-layer (unimodality) evidence, not a
            # certificate-layer defect — triage handles it (ADR-0005).
            return (
                "positive_enclosure",
                f"splitting function certified positive on sub-box {box}",
                evals,
            )
        widest = max(
            range(len(box)), key=lambda i: box[i][1] - box[i][0]
        )
        low, high = box[widest]
        if high - low <= 0.0:
            return (
                "budget_exhausted",
                f"sub-box degenerate in every dimension at {evals} evaluations",
                evals,
            )
        mid = (low + high) / 2.0
        left = tuple(
            (low, mid) if i == widest else span for i, span in enumerate(box)
        )
        right = tuple(
            (mid, high) if i == widest else span for i, span in enumerate(box)
        )
        stack.extend((left, right))
    return "closed", None, evals


def verify_record_adr0004(
    record: RegionRecord,
    family: CaseFamily,
    subcase: Subcase,
    splits: Sequence[Split],
    prec_ladder: Sequence[int] = DEFAULT_PREC_LADDER,
    fullbox_budget: int = DEFAULT_FULLBOX_BUDGET,
    *,
    rho: fmpq,
) -> Verdict:
    """Full-box first, vertex-parity fallback (the ADR-0004 semantics)."""
    base = verify_record_vertex_parity(
        record, family, subcase, splits, prec_ladder, rho=rho
    )
    if base.mode in ("skipped", "invalid"):
        return base
    split = splits[record.split_id - 1]
    set_precision(prec_ladder[0])
    outcome, note, used = _fullbox_attempt(
        record, family, subcase, split, fullbox_budget, rho
    )
    if outcome == "closed" and base.mode == "vertex_parity":
        return replace(
            base, mode="full_box", fullbox_outcome="closed", subboxes_used=used
        )
    reason = base.reason
    if note is not None:
        reason = f"{reason}; full-box: {note}" if reason else f"full-box: {note}"
    return replace(
        base, reason=reason, fullbox_outcome=outcome, subboxes_used=used
    )


def verify_record_vertex_parity(
    record: RegionRecord,
    family: CaseFamily,
    subcase: Subcase,
    splits: Sequence[Split],
    prec_ladder: Sequence[int] = DEFAULT_PREC_LADDER,
    *,
    rho: fmpq,
) -> Verdict:
    def verdict(
        mode: Mode, ok: bool, reason: str | None, prec: int, checked: int
    ) -> Verdict:
        return Verdict(
            region_id=record.region_id,
            split_id=record.split_id,
            lemma_id=record.lemma_id,
            mode=mode,
            ok=ok,
            reason=reason,
            prec=prec,
            vertices_checked=checked,
            rho=rho_str(rho),
        )

    skip = _skip_reason(record, family, subcase)
    if skip is not None:
        return verdict("skipped", True, skip, 0, 0)
    if record.split_id <= 0:
        # The other-subcase sentinels (0 in the published data, -1 from the
        # snapshot's generator) are only legal on records the subcase filter
        # skips (their checker would die on a BoundsError here).
        return verdict(
            "invalid", False,
            f"sentinel split_id {record.split_id} on a record no subcase "
            "filter skips", 0, 0,
        )
    split = splits[record.split_id - 1]
    problem = _validate_record(record, family, subcase, split)
    if problem is not None:
        return verdict("invalid", False, problem, 0, 0)

    # Escalate precision before recording anything but a clean pass: a failure
    # or inconclusive verdict must not be an artifact of enclosure width.
    outcome: Literal["ok", "failed", "inconclusive"] = "inconclusive"
    reason: str | None = None
    checked = 0
    prec = prec_ladder[0]
    for prec in prec_ladder:
        set_precision(prec)
        outcome, reason, checked = _check_vertices(
            record, family, subcase, split, rho
        )
        if outcome == "ok":
            return verdict("vertex_parity", True, None, prec, checked)
    if outcome == "failed":
        return verdict("failed", False, reason, prec, checked)
    return verdict("inconclusive", False, reason, prec, checked)


# --- critical rho (ticket #16) ----------------------------------------------
#
# F(rho) = rho * L_T* + (L_S+ - L_S-) is affine in rho with L_T* >= 0, and
# no lemma condition or skip rule reads rho, so each record has a critical
# rho — the sup of the rhos it certifies — computable in one pass as the
# minimum over checked vertices of (L_S- - L_S+) / L_T*. The corpus minimum
# is the exact ceiling of the published tiling under vertex semantics.
# Inherited lemma-layer obligations (trapped-point polygons, monotonicity of
# the constituent lengths) are claims about lengths, not about F, and are
# rho-uniform; the unimodality claim transfers likewise for vertex results
# and is not needed where the full-box variant certifies a leaf partition.

CriticalOutcome = Literal[
    "bounded", "unconstrained", "skipped", "invalid", "failed_all_rho",
    "inconclusive",
]


@dataclass(frozen=True)
class CriticalRho:
    region_id: int
    split_id: int
    lemma_id: int
    outcome: CriticalOutcome
    # certified bounds on this record's critical rho under vertex semantics
    # (math.inf when no vertex constrains it); None unless outcome=="bounded"
    crit_lo: float | None
    crit_hi: float | None
    reason: str | None
    prec: int
    vertices_checked: int
    binding_vertex: int | None = None
    # one-sided full-box certificate: F <= 0 over the whole box for every
    # rho <= fullbox_lo (None = full-box not run or did not close)
    fullbox_lo: float | None = None
    fullbox_outcome: str | None = None
    subboxes_used: int = 0


def _ratio_bounds(t_star: arb, s_net: arb) -> tuple[float, float] | None:
    """Certified [lo, hi] for (-s_net)/t_star given t_star >= 0 on paper.

    Returns None when the vertex constrains nothing (t_star provably 0 with
    s_net <= 0). A certified s_net > 0 is the caller's failed_all_rho case
    and must be handled before calling.
    """
    num = -s_net
    if t_star > arb(0):
        ratio = num / t_star
        return float(ratio.lower()), float(ratio.upper())
    # t_star's ball touches 0; mathematically t_star >= 0, so only an upper
    # bound on t_star survives — it still yields a certified lower bound
    t_hi = float(t_star.upper())
    if t_hi <= 0.0:
        return None  # provably t_star == 0, s_net <= 0: no constraint
    lo = (arb(num.lower()) / arb(t_hi)).lower()
    return float(lo), math.inf


def _vertex_critical(
    record: RegionRecord,
    family: CaseFamily,
    subcase: Subcase,
    split: Split,
) -> tuple[
    Literal["bounded", "unconstrained", "failed_all_rho", "inconclusive"],
    float | None, float | None, str | None, int, int | None,
]:
    n = record.n
    n_vars = len(family.var_names)
    checked = 0
    crit_lo = math.inf
    crit_hi = math.inf
    binding: int | None = None
    for mask in range(1 << n):
        values: list[float] = []
        finite = True
        for i in range(n):
            v = record.box[i][(mask >> i) & 1]
            if math.isinf(v):
                finite = False
                break
            values.append(v)
        if not finite:
            continue
        vars: list[arb] = [arb(0)] * n_vars
        for i, v in enumerate(values):
            vars[subcase.box_vars[i]] = arb(v)
        for target, source in subcase.derived:
            vars[target] = vars[source]
        checked += 1
        parts = evaluate_split_parts(
            family, split, vars, record.lemma_id, subcase.f_val
        )
        if isinstance(parts, EvalFailure):
            # lemma conditions do not read rho: unpriceable at every rho
            return (
                "failed_all_rho",
                None, None,
                f"vertex {mask}: {parts.reason}",
                checked, None,
            )
        t_star, s_net = parts
        if not (t_star.is_finite() and s_net.is_finite()):
            return (
                "inconclusive", None, None,
                f"vertex {mask}: enclosure not finite", checked, None,
            )
        if arb(0) < s_net:
            # t_star >= 0 on paper, so F(rho) >= s_net > 0 at every rho >= 0
            return (
                "failed_all_rho", None, None,
                f"vertex {mask}: L_S+ - L_S- certified positive "
                f"(enclosure {s_net})", checked, None,
            )
        if not s_net <= arb(0) and not t_star > arb(0):
            # sign of neither factor certified: enclosure too wide
            return (
                "inconclusive", None, None,
                f"vertex {mask}: neither s_net <= 0 nor t_star > 0 "
                "certified", checked, None,
            )
        bounds = _ratio_bounds(t_star, s_net)
        if bounds is None:
            continue
        lo, hi = bounds
        crit_lo = min(crit_lo, lo)
        if hi < crit_hi:
            crit_hi = hi
            binding = mask
    if math.isinf(crit_hi) and math.isinf(crit_lo):
        return "unconstrained", math.inf, math.inf, None, checked, None
    return "bounded", crit_lo, crit_hi, None, checked, binding


def critical_rho_vertex_parity(
    record: RegionRecord,
    family: CaseFamily,
    subcase: Subcase,
    splits: Sequence[Split],
    prec_ladder: Sequence[int] = DEFAULT_PREC_LADDER,
) -> CriticalRho:
    """Certified bounds on the record's critical rho under vertex semantics."""
    def result(
        outcome: CriticalOutcome, lo: float | None, hi: float | None,
        reason: str | None, prec: int, checked: int,
        binding: int | None = None,
    ) -> CriticalRho:
        return CriticalRho(
            region_id=record.region_id,
            split_id=record.split_id,
            lemma_id=record.lemma_id,
            outcome=outcome,
            crit_lo=lo,
            crit_hi=hi,
            reason=reason,
            prec=prec,
            vertices_checked=checked,
            binding_vertex=binding,
        )

    skip = _skip_reason(record, family, subcase)
    if skip is not None:
        return result("skipped", None, None, skip, 0, 0)
    if record.split_id <= 0:
        return result(
            "invalid", None, None,
            f"sentinel split_id {record.split_id} on a record no subcase "
            "filter skips", 0, 0,
        )
    split = splits[record.split_id - 1]
    problem = _validate_record(record, family, subcase, split)
    if problem is not None:
        return result("invalid", None, None, problem, 0, 0)

    outcome: Literal[
        "bounded", "unconstrained", "failed_all_rho", "inconclusive"
    ] = "inconclusive"
    lo: float | None = None
    hi: float | None = None
    reason: str | None = None
    checked = 0
    binding: int | None = None
    prec = prec_ladder[0]
    for prec in prec_ladder:
        set_precision(prec)
        outcome, lo, hi, reason, checked, binding = _vertex_critical(
            record, family, subcase, split
        )
        if outcome in ("bounded", "unconstrained"):
            return result(outcome, lo, hi, reason, prec, checked, binding)
    return result(outcome, lo, hi, reason, prec, checked, binding)


def critical_rho_adr0004(
    record: RegionRecord,
    family: CaseFamily,
    subcase: Subcase,
    splits: Sequence[Split],
    prec_ladder: Sequence[int] = DEFAULT_PREC_LADDER,
    fullbox_budget: int = DEFAULT_FULLBOX_BUDGET,
    *,
    drive_rho: fmpq,
) -> CriticalRho:
    """Vertex critical rho, plus a one-sided full-box certificate.

    The subdivision is driven at drive_rho (a rho the region is expected to
    close at — the incumbent bound, normally); on every closed leaf,
    F(rho) <= 0 holds for all rho up to the leaf's certified
    (L_S- - L_S+) / L_T* lower bound, so the min over the leaf partition
    certifies the whole box up to fullbox_lo. The partition depends on
    drive_rho; the resulting bound is valid regardless (each leaf's bound
    stands on its own and the leaves cover the box).
    """
    base = critical_rho_vertex_parity(
        record, family, subcase, splits, prec_ladder
    )
    if base.outcome in ("skipped", "invalid", "failed_all_rho", "inconclusive"):
        return base
    split = splits[record.split_id - 1]
    set_precision(prec_ladder[0])
    leaves: list[tuple[arb, arb]] = []
    outcome, _, used = _fullbox_attempt(
        record, family, subcase, split, fullbox_budget, drive_rho,
        leaf_parts=leaves,
    )
    if outcome != "closed":
        return replace(base, fullbox_outcome=outcome, subboxes_used=used)
    fullbox_lo = math.inf
    for t_star, s_net in leaves:
        # closing the leaf at drive_rho > 0 forces s_net <= 0 there, so the
        # ratio always yields a finite-or-infinite certified lower bound
        bounds = _ratio_bounds(t_star, s_net)
        if bounds is not None:
            fullbox_lo = min(fullbox_lo, bounds[0])
    return replace(
        base,
        fullbox_lo=fullbox_lo,
        fullbox_outcome="closed",
        subboxes_used=used,
    )

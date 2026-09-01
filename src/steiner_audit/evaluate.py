"""Splitting-function evaluation: F = rho * L_T* + L_S+ - L_S-.

The composition rule mirrors their checker exactly (their evaluate_split):
T* edges touching a trapped point price via the record's lemma table, other
T* edges price as exact distances; S- sums deleted-edge lengths (edge 0 is
the unit edge); S+ prices as a distance (2 points), a 3-point Steiner tree
length, or a 4-point lemma bound. A lemma condition that cannot be certified
is a failure of the record, never a silent skip.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from flint import arb, fmpq

from .arbcalc import dist, smt_length
from .case import CaseFamily, Point, Split


@dataclass(frozen=True)
class EvalFailure:
    """A lemma precondition could not be certified at this vertex."""

    reason: str


def evaluate_split(
    family: CaseFamily,
    split: Split,
    vars: Sequence[arb],
    lemma_id: int,
    f_val: int,
    *,
    rho: fmpq,
) -> arb | EvalFailure:
    # rho is a required keyword on purpose: every caller states which bound
    # it is certifying, so a forgotten thread can never mean "silently 0.8559"
    parts = evaluate_split_parts(family, split, vars, lemma_id, f_val)
    if isinstance(parts, EvalFailure):
        return parts
    t_star, s_net = parts
    return arb(rho) * t_star + s_net


def evaluate_split_parts(
    family: CaseFamily,
    split: Split,
    vars: Sequence[arb],
    lemma_id: int,
    f_val: int,
) -> tuple[arb, arb] | EvalFailure:
    """The two rho-affine components of F: (L_T*, L_S+ - L_S-).

    F(rho) = rho * L_T* + (L_S+ - L_S-), and nothing else in the evaluation
    (lemma conditions, skip rules) reads rho — the basis for the ceiling
    search's one-pass critical-rho computation (ticket #16).
    """
    pos = family.get_coordinates(vars)
    table = family.lemma_tables[lemma_id]

    t_star = arb(0)
    for edge in split.t_star:
        u, v = edge
        if u in family.imp_nodes or v in family.imp_nodes:
            entry = table.get(edge)
            if entry is None:
                return EvalFailure(
                    f"lemma {lemma_id} has no bound for T* edge "
                    f"({family.nodes[u]},{family.nodes[v]})"
                )
            cond, bound = entry
            if not cond(pos, vars, f_val):
                return EvalFailure(
                    f"lemma {lemma_id} condition not certified for T* edge "
                    f"({family.nodes[u]},{family.nodes[v]})"
                )
            t_star += bound(pos, vars)
        else:
            t_star += dist(pos[u], pos[v])

    s_minus = arb(0)
    for edge_id in split.s_minus:
        s_minus += arb(1) if edge_id == 0 else vars[edge_id - 1]

    if len(split.s_plus) < 2:
        # Splittings that cut off enough terminals need no reconnection edges
        # (their evaluate_split falls through all branches, leaving 0).
        s_plus = arb(0)
    elif len(split.s_plus) == 2:
        s_plus = dist(pos[split.s_plus[0]], pos[split.s_plus[1]])
    elif len(split.s_plus) == 3:
        s_plus = smt_length(
            pos[split.s_plus[0]], pos[split.s_plus[1]], pos[split.s_plus[2]]
        )
    else:
        entry = table.get(split.s_plus)
        if entry is None:
            return EvalFailure(
                f"lemma {lemma_id} has no bound for S+ set "
                f"{[family.nodes[u] for u in split.s_plus]}"
            )
        cond, bound = entry
        if not cond(pos, vars, f_val):
            return EvalFailure(
                f"lemma {lemma_id} condition not certified for S+ set "
                f"{[family.nodes[u] for u in split.s_plus]}"
            )
        s_plus = bound(pos, vars)

    return t_star, s_plus - s_minus

"""Case vocabulary: splits, subcases, and case families.

A case family (d_regular, d_steiner) fixes the node/edge/variable alphabets,
the local-configuration geometry, and the nine lemma tables. A subcase fixes
which variables appear in each record's box and any derived substitution
(f := d on the f >= d boundary). splits.txt is consumed as untrusted external
configuration and parsed strictly.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

from flint import arb

Point = tuple[arb, arb]
# cond(pos, vars, f_val) -> certified bool; bound(pos, vars) -> upper bound
CondFn = Callable[[Sequence[Point], Sequence[arb], int], bool]
BoundFn = Callable[[Sequence[Point], Sequence[arb]], arb]
LemmaTable = Mapping[tuple[int, ...], tuple[CondFn, BoundFn]]

F_LE_D = 1  # their F_VAL for the f <= d subcase
F_GE_D = 2  # their F_VAL for the f >= d subcase


class SplitsParseError(Exception):
    """splits.txt violated the expected format or vocabulary."""


@dataclass(frozen=True)
class Split:
    line_no: int  # 1-based; equals the split_id records refer to
    v_star: tuple[int, ...]
    s_minus: tuple[int, ...]  # edge ids; edge 0 has length exactly 1
    s_plus: tuple[int, ...]  # node ids, sorted
    t_star: tuple[tuple[int, int], ...]  # normalized node pairs
    mono_vars: frozenset[int]


@dataclass(frozen=True)
class Subcase:
    name: str
    f_val: int
    box_vars: tuple[int, ...]  # variable index of each box coordinate
    # var substitutions applied after a vertex is assembled: (target, source)
    derived: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class CaseFamily:
    name: str
    nodes: tuple[str, ...]
    imp_nodes: frozenset[int]  # trapped points (X, Y): edges to these use lemmas
    edges: tuple[tuple[int, int], ...]
    var_names: tuple[str, ...]
    subcases: Mapping[str, Subcase]
    get_coordinates: Callable[[Sequence[arb]], tuple[Point, ...]]
    lemma_tables: tuple[LemmaTable, ...]
    # extra record-skip rules (box, subcase) -> reason, e.g. the d_steiner
    # symmetry filter; the generic f<=d filter lives in the kernel
    skip_rules: tuple[Callable[[tuple[tuple[float, float], ...], Subcase], str | None], ...] = ()

    def node_id(self, name: str) -> int:
        return self.nodes.index(name)

    def var_id(self, name: str) -> int:
        return self.var_names.index(name)


def _normalized(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


_REQUIRED_FIELDS = ("V_star", "S_minus", "S_plus", "T_star", "mono_vars")


def parse_splits(text: str, family: CaseFamily) -> tuple[Split, ...]:
    """Parse a splits.txt strictly against the family's vocabulary."""
    node_ids = {name: i for i, name in enumerate(family.nodes)}
    var_ids = {name: i for i, name in enumerate(family.var_names)}
    edge_ids = {
        _normalized(u, v): i for i, (u, v) in enumerate(family.edges)
    }

    def node(name: object, where: str) -> int:
        if not isinstance(name, str) or name not in node_ids:
            raise SplitsParseError(f"{where}: unknown node {name!r}")
        return node_ids[name]

    splits = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        where = f"splits.txt line {line_no}"
        fields: dict[str, object] = {}
        for segment in line.split(";"):
            if ":" not in segment:
                continue
            key, _, value = segment.partition(":")
            try:
                fields[key.strip()] = ast.literal_eval(value.strip())
            except (ValueError, SyntaxError) as exc:
                raise SplitsParseError(f"{where}: bad literal in {key.strip()!r}: {exc}") from exc
        missing = [k for k in _REQUIRED_FIELDS if k not in fields]
        if missing:
            raise SplitsParseError(f"{where}: missing fields {missing}")

        v_star_raw = fields["V_star"]
        s_minus_raw = fields["S_minus"]
        s_plus_raw = fields["S_plus"]
        t_star_raw = fields["T_star"]
        mono_raw = fields["mono_vars"]
        if not isinstance(v_star_raw, list) or not isinstance(s_minus_raw, list) \
                or not isinstance(s_plus_raw, tuple) or not isinstance(t_star_raw, list) \
                or not isinstance(mono_raw, list):
            raise SplitsParseError(f"{where}: field has wrong shape")

        s_minus = []
        for pair in s_minus_raw:
            edge = _normalized(node(pair[0], where), node(pair[1], where))
            if edge not in edge_ids:
                raise SplitsParseError(f"{where}: S_minus edge {pair!r} not a tree edge")
            s_minus.append(edge_ids[edge])
        for name in mono_raw:
            if name not in var_ids:
                raise SplitsParseError(f"{where}: unknown variable {name!r}")

        splits.append(
            Split(
                line_no=line_no,
                v_star=tuple(node(u, where) for u in v_star_raw),
                s_minus=tuple(s_minus),
                s_plus=tuple(sorted(node(u, where) for u in s_plus_raw)),
                t_star=tuple(
                    _normalized(node(u, where), node(v, where))
                    for (u, v) in t_star_raw
                ),
                mono_vars=frozenset(var_ids[name] for name in mono_raw),
            )
        )
    return tuple(splits)

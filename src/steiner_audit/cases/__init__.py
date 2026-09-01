"""Case families of the PKU certificate: d_regular (n=5/6), d_steiner (n=7/8)."""

from __future__ import annotations

from ..case import CaseFamily
from . import d_regular, d_steiner


def by_name(name: str) -> CaseFamily:
    if name == "d_regular":
        return d_regular.FAMILY
    if name == "d_steiner":
        return d_steiner.FAMILY
    raise KeyError(f"unknown case family {name!r}")

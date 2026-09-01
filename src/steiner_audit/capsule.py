"""Failing-region capsule generation (ADR-0005).

A capsule is the publication gate for any defect claim: a minimal,
self-contained directory a third party can replay in minutes. It carries the
region's data and split definition (capsule.json), a dependency-light replay
script (replay.py = the family's independent mpmath reference plus a driver
over the embedded record, needing only `pip install mpmath`), and a README.
The replay evaluates the designated splitting function at every finite box
vertex at 60 significant digits and confirms the defect only if some vertex
is unambiguously positive.
"""

from __future__ import annotations

import importlib.resources
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from flint import fmpq

from .arbcalc import rho_str
from .case import CaseFamily, Split, Subcase
from .records import RegionRecord

_DRIVER = '''

# ============================================================================
# Capsule replay driver (generated; data embedded below)
# ============================================================================

CAPSULE = json.loads(r"""{capsule_json}""")

# The capsule's exact rational rho, at the reference stack's 60 digits;
# passed to every splitting_function call rather than relying on the
# module-level RHO default (which stays the M1 bound 8559/10000).
_RHO_P, _RHO_Q = CAPSULE["rho"].split("/")
CAPSULE_RHO = mpf(int(_RHO_P)) / mpf(int(_RHO_Q))


class _Split:
    def __init__(self, d):
        self.t_star = [tuple(e) for e in d["t_star"]]
        self.s_minus = list(d["s_minus"])
        self.s_plus = tuple(d["s_plus"])


def _vertices(box):
    n = len(box)
    for mask in range(1 << n):
        vertex = []
        finite = True
        for i, pair in enumerate(box):
            low, high = float(pair[0]), float(pair[1])
            value = high if (mask >> i) & 1 else low
            if value == float("inf"):
                finite = False
                break
            vertex.append(value)
        if finite:
            yield mask, vertex


def main():
    split = _Split(CAPSULE["split"])
    lemma_id = CAPSULE["lemma_id"]
    box = CAPSULE["box"]
    f_from_d = CAPSULE["substitute_f_equals_d"]
    f_index = CAPSULE["f_index"]
    d_index = CAPSULE["d_index"]

    worst = None
    for mask, vertex in _vertices(box):
        w = [mpf(x) for x in vertex]
        while len(w) < CAPSULE["n_vars"]:
            w.append(mpf(0))
        if f_from_d:
            w[f_index] = w[d_index]
        value = splitting_function(split, w, lemma_id, rho=CAPSULE_RHO)
        if worst is None or value > worst[1]:
            worst = (mask, value)

    print("capsule:", CAPSULE["title"])
    print("region_id:", CAPSULE["region_id"], "split_id:", CAPSULE["split_id"],
          "lemma_id:", lemma_id, "rho:", CAPSULE["rho"])
    print("worst vertex mask:", worst[0])
    print("F at worst vertex (60 significant digits):")
    print("   ", mp.nstr(worst[1], 50))
    if worst[1] > mpf(10) ** -30:
        print("DEFECT CONFIRMED: splitting function is positive at a box vertex.")
        return 0
    print("NOT CONFIRMED: no vertex is unambiguously positive.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
'''

_README = """# Failing-region capsule: {title}

One region of the PKU Gilbert-Pollak certificate layer (arXiv:2601.22365,
dataset keyisi/steiner-ratio) whose designated splitting function, evaluated
at rho = {rho}, is claimed NOT to be non-positive at the box vertices.
(rho = 8559/10000 is the published bound; any other value makes this a
candidate-bound failure, not a defect claim against the published data.)

## Replay (minutes, one dependency)

    python3 -m pip install mpmath
    python3 replay.py

Exit code 0 and "DEFECT CONFIRMED" means a vertex of the region's box has a
positive splitting-function value at 60-significant-digit precision. The
mathematics in replay.py is an independent mpmath transcription of the
splitting function (geometry, lemma bounds); capsule.json carries the region
bounds and identities plus provenance (dataset file sha256, record index).

Rigorous confirmation (outward-rounded ball arithmetic) is available by
running the steiner-audit verifier on capsule.json's record; see the
MathProof release for instructions.
"""


@dataclass(frozen=True)
class CapsuleResult:
    directory: Path
    confirmed: bool
    output: str


def _refmath_source(family_name: str) -> str:
    source = (
        importlib.resources.files("steiner_audit.refmath")
        .joinpath(f"{family_name}.py")
        .read_text()
    )
    return source + "\nimport json\nimport sys\nfrom mpmath import mp, mpf\n"


def generate_capsule(
    record: RegionRecord,
    family: CaseFamily,
    subcase: Subcase,
    split: Split,
    out_dir: Path,
    provenance: dict[str, object] | None = None,
    *,
    rho: fmpq,
) -> Path:
    """Write the capsule directory for a suspect record at the given rho."""
    out_dir.mkdir(parents=True, exist_ok=True)
    title = f"{family.name}/{subcase.name} region {record.region_id}"
    f_index = family.var_id("f")
    d_index = family.var_id("d")
    capsule = {
        "schema": "steiner-audit/capsule/v1",
        "title": title,
        "family": family.name,
        "subcase": subcase.name,
        "region_id": record.region_id,
        "split_id": record.split_id,
        "lemma_id": record.lemma_id,
        # floats round-trip exactly through repr/JSON; unbounded tops are the
        # string "inf" so the file stays strict JSON (replay float()s them)
        "box": [
            [low, "inf" if math.isinf(high) else high]
            for (low, high) in record.box
        ],
        "box_vars": [family.var_names[i] for i in subcase.box_vars],
        "n_vars": len(family.var_names),
        "substitute_f_equals_d": bool(subcase.derived),
        "f_index": f_index,
        "d_index": d_index,
        "rho": rho_str(rho),
        "split": {
            "t_star": [list(e) for e in split.t_star],
            "s_minus": list(split.s_minus),
            "s_plus": list(split.s_plus),
            "mono_vars": sorted(split.mono_vars),
        },
        "provenance": provenance or {},
    }
    (out_dir / "capsule.json").write_text(json.dumps(capsule, indent=2) + "\n")
    replay = _refmath_source(family.name) + _DRIVER.format(
        capsule_json=json.dumps(capsule)
    )
    (out_dir / "replay.py").write_text(replay)
    (out_dir / "README.md").write_text(
        _README.format(title=title, rho=rho_str(rho))
    )
    return out_dir


def replay_capsule(directory: Path) -> CapsuleResult:
    """Run the capsule's replay script the way a third party would."""
    proc = subprocess.run(
        [sys.executable, "replay.py"],
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = proc.stdout + proc.stderr
    return CapsuleResult(
        directory=directory,
        confirmed=proc.returncode == 0 and "DEFECT CONFIRMED" in output,
        output=output,
    )

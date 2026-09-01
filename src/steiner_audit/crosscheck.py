"""Cross-check and triage machinery (ticket #11).

Their Julia checker runs as an untrusted external tool (ADR-0002) against
arbitrary record files — whole cases or single suspect regions — in a
scratch directory assembled from snapshot symlinks, so the snapshot itself
is never modified. Disagreements between the two stacks enter a triage queue
whose discipline is our-bug-first: an entry must survive a high-precision
re-run on our stack and a single-region re-run of their checker before it
can even be considered a finding, and nothing becomes reportable without a
passing failing-region capsule plus both-stack agreement (ADR-0005 — the
gate is structural: there is no other code path to the reportable state).
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Sequence

from flint import fmpq

from .arbcalc import RHO_M1
from . import acquisition as acq
from .capsule import CapsuleResult
from .case import CaseFamily, Split, Subcase
from .kernel import Verdict, verify_record_vertex_parity
from .records import RegionRecord, write_records

_CERT_NAME = "certificate_rho=0.8559_{subcase}.bin"
_HIGH_PREC_LADDER = (256, 512, 1024)


@dataclass(frozen=True)
class TheirVerdict:
    passed: bool
    verified_count: int | None
    raw_tail: str


def _scratch_case_dir(family_name: str, scratch: Path) -> Path:
    """Assemble a runnable copy of the snapshot case dir out of symlinks."""
    source = acq.SNAPSHOT_DIR / "certificate" / family_name
    env = acq.SNAPSHOT_DIR / "certificate" / "steiner"  # their Pkg env
    case_dir = scratch / family_name
    case_dir.mkdir(parents=True, exist_ok=True)
    if env.exists() and not (scratch / "steiner").exists():
        (scratch / "steiner").symlink_to(env)
    for item in source.iterdir():
        target = case_dir / item.name
        if item.name.endswith(".bin") or target.exists():
            continue
        target.symlink_to(item)
    return case_dir


def run_their_checker(
    family_name: str,
    subcase: str,
    cert_file: Path,
    timeout: float = 3600,
) -> TheirVerdict:
    """Run their verify_certificate.jl on an arbitrary certificate file."""
    flag = "--f-ge-d" if subcase == "f_ge_d" else "--f-le-d"
    with tempfile.TemporaryDirectory(prefix="steiner-crosscheck-") as tmp:
        case_dir = _scratch_case_dir(family_name, Path(tmp))
        (case_dir / _CERT_NAME.format(subcase=subcase)).symlink_to(
            cert_file.resolve()
        )
        proc = subprocess.run(
            ["julia", "--threads", "auto", "verify_certificate.jl", flag],
            cwd=case_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-15:])
    verified_count = None
    passed = False
    for line in (proc.stdout or "").splitlines():
        if line.startswith("All ") and line.endswith(" regions verified."):
            verified_count = int(line.split()[1])
            passed = proc.returncode == 0
    return TheirVerdict(passed=passed, verified_count=verified_count, raw_tail=tail)


def crosscheck_region(
    record: RegionRecord, family_name: str, subcase: str, work_dir: Path
) -> TheirVerdict:
    """Their checker's verdict on a single region."""
    work_dir.mkdir(parents=True, exist_ok=True)
    single = work_dir / f"region_{record.region_id}.bin"
    write_records(single, [record], n=record.n)
    return run_their_checker(family_name, subcase, single)


TriageKind = Literal["our-failure", "stack-disagreement"]
TriageStatus = Literal["open", "our_bug", "benign", "reportable"]


@dataclass
class TriageEntry:
    entry_id: str
    family: str
    subcase: str
    region_id: int
    kind: TriageKind
    ours: dict[str, Any]
    theirs: dict[str, Any] | None = None
    status: TriageStatus = "open"
    evidence: dict[str, Any] = field(default_factory=dict)


class TriageQueue:
    """JSONL-backed queue; every state change is appended, last state wins."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: dict[str, TriageEntry] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    entry = TriageEntry(**json.loads(line))
                    self.entries[entry.entry_id] = entry

    def _append(self, entry: TriageEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
        self.entries[entry.entry_id] = entry

    def open_from_verdict(
        self, family: CaseFamily, subcase: Subcase, verdict: Verdict
    ) -> TriageEntry:
        entry = TriageEntry(
            entry_id=uuid.uuid4().hex[:12],
            family=family.name,
            subcase=subcase.name,
            region_id=verdict.region_id,
            kind="our-failure",
            ours=asdict(verdict),
        )
        self._append(entry)
        return entry

    def apply_our_bug_first(
        self,
        entry: TriageEntry,
        record: RegionRecord,
        family: CaseFamily,
        subcase: Subcase,
        splits: Sequence[Split],
        their_verdict: TheirVerdict | None = None,
        *,
        rho: fmpq,
    ) -> TriageEntry:
        """Step 1 of triage: assume our verifier is wrong until re-proven.

        Re-runs the region on our stack at an escalated precision ladder and
        records their checker's single-region verdict when provided. If the
        high-precision re-run passes, the entry closes as our_bug. The rerun
        must state the rho under triage; their checker only speaks for the
        published 8559/10000, so a their_verdict at any other rho is refused.
        """
        if their_verdict is not None and rho != RHO_M1:
            raise ValueError(
                "their checker verifies at the published 8559/10000 only; "
                f"a their_verdict cannot inform triage at rho {rho}"
            )
        rerun = verify_record_vertex_parity(
            record, family, subcase, splits, prec_ladder=_HIGH_PREC_LADDER,
            rho=rho,
        )
        entry.evidence["our_high_prec_rerun"] = asdict(rerun)
        if their_verdict is not None:
            entry.theirs = asdict(their_verdict)
        if rerun.ok:
            entry.status = "our_bug"
        self._append(entry)
        return entry

    def mark_benign(self, entry: TriageEntry, why: str) -> TriageEntry:
        entry.status = "benign"
        entry.evidence["benign_reason"] = why
        self._append(entry)
        return entry

    def mark_reportable(
        self, entry: TriageEntry, capsule_result: CapsuleResult
    ) -> TriageEntry:
        """The ADR-0005 gate: the only path to the reportable state.

        Requires a passing capsule replay, a recorded high-precision re-run
        on our stack that still fails, and their checker's recorded agreement
        that the region fails.
        """
        rerun = entry.evidence.get("our_high_prec_rerun")
        if rerun is None or rerun.get("ok"):
            raise ValueError(
                "unreportable: no failing high-precision re-run on our stack "
                "(our-bug-first triage has not run or the region passed)"
            )
        if entry.theirs is None or entry.theirs.get("passed"):
            raise ValueError(
                "unreportable: their checker has not confirmed the region fails"
            )
        if not capsule_result.confirmed:
            raise ValueError(
                "unreportable: capsule replay did not confirm the defect "
                f"(output tail: {capsule_result.output[-300:]!r})"
            )
        entry.status = "reportable"
        entry.evidence["capsule_dir"] = str(capsule_result.directory)
        self._append(entry)
        return entry

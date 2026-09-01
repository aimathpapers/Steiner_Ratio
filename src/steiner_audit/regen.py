"""Regeneration harness: their C++ generator, built and run locally (ticket #9).

Ops layer (smoke tests only). The generator runs in an isolated work dir
under vendor/regen/<family>/ assembled from snapshot symlinks — never in the
snapshot case dir itself, where the generated .bin files would overwrite the
downloaded dataset through its symlinks. Per-case state lives in
vendor/regen/state.json so interrupted multi-hour runs resume at case
granularity (their generator has no internal checkpointing); per-case logs
stream to vendor/regen/<family>/<subcase>.log.

Their Makefile hardcodes `g++`, which on macOS is clang without
bits/stdc++.h; a PATH shim maps g++ to Homebrew's real GNU g++ so their
build system runs unmodified (ADR-0002).
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import acquisition as acq
from .manifest import Manifest, sha256_file

REGEN_ROOT = acq.VENDOR / "regen"
STATE_PATH = REGEN_ROOT / "state.json"

_SOURCES = (
    "Makefile", "splits.txt", "formulas", "lemmas",
    "plot_f_ge_d.cpp", "plot_f_le_d.cpp",
)
_RHO_CONSTANT = "const ld rho = 0.8559"
_RHO_TEXT_RE = r"0\.\d{1,6}"


def patch_rho_source(text: str, rho_text: str) -> str:
    """Their generator source with the rho constant patched, exactly once.

    The adaptive-ceiling probe (ticket #16): the generator's rho drives
    which partition gets generated (and, via their format() call, the
    output filenames); the certificate a patched run emits is then verified
    by our stack at the exact rational — their long-double rho never enters
    our verification semantics.
    """
    import re

    if not re.fullmatch(_RHO_TEXT_RE, rho_text):
        raise ValueError(f"rho for source patching must match {_RHO_TEXT_RE}")
    if text.count(_RHO_CONSTANT) != 1:
        raise ValueError(
            "expected exactly one rho constant in generator source"
        )
    return text.replace(_RHO_CONSTANT, f"const ld rho = {rho_text}")


def _load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        return dict(json.loads(STATE_PATH.read_text()))
    return {}


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def find_gnu_gxx() -> str | None:
    """A real GNU g++ (clang masquerades as g++ on macOS)."""
    candidates = sorted(glob.glob("/opt/homebrew/bin/g++-*"), reverse=True)
    for candidate in candidates + [shutil.which("g++") or ""]:
        if not candidate:
            continue
        probe = subprocess.run(
            [candidate, "--version"], capture_output=True, text=True
        )
        if probe.returncode == 0 and "clang" not in probe.stdout.lower():
            return candidate
    return None


def work_dir(family: str, rho_text: str | None = None) -> Path:
    """Assemble the isolated generator work dir (idempotent).

    With rho_text, a separate <family>@<rho> dir gets patched COPIES of the
    plot sources (never symlinks — the snapshot stays untouched) alongside
    symlinks to the rho-independent inputs.
    """
    source = acq.SNAPSHOT_DIR / "certificate" / family
    dest = REGEN_ROOT / (family if rho_text is None else f"{family}@{rho_text}")
    dest.mkdir(parents=True, exist_ok=True)
    for name in _SOURCES:
        target = dest / name
        if target.exists() or target.is_symlink():
            continue
        if rho_text is not None and name.startswith("plot_"):
            target.write_text(
                patch_rho_source((source / name).read_text(), rho_text)
            )
        else:
            target.symlink_to(source / name)
    return dest


def build(family: str, rho_text: str | None = None) -> dict[str, str]:
    """make in the work dir behind a g++ PATH shim; returns tool metadata."""
    gxx = find_gnu_gxx()
    if gxx is None:
        raise RuntimeError(
            "no GNU g++ found (their code needs bits/stdc++.h; brew install gcc)"
        )
    dest = work_dir(family, rho_text)
    shim = REGEN_ROOT / "bin"
    shim.mkdir(parents=True, exist_ok=True)
    gxx_link = shim / "g++"
    if gxx_link.is_symlink() or gxx_link.exists():
        gxx_link.unlink()
    gxx_link.symlink_to(gxx)
    env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}")
    proc = subprocess.run(
        ["make"], cwd=dest, env=env, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(f"their build failed:\n{proc.stdout}\n{proc.stderr}")
    version = subprocess.run(
        [gxx, "--version"], capture_output=True, text=True
    ).stdout.splitlines()[0]
    return {"g++": gxx, "g++ --version": version}


def run_case(
    family: str, subcase: str, resume: bool = True,
    rho_text: str | None = None,
) -> dict[str, Any]:
    """Run one generator case to completion, logging and recording state."""
    key = f"{family}/{subcase}" + (
        "" if rho_text is None else f"@rho={rho_text}"
    )
    state = _load_state()
    entry: dict[str, Any] = dict(state.get(key, {}))
    if resume and entry.get("status") == "done":
        return entry

    toolchain = build(family, rho_text)
    dest = work_dir(family, rho_text)
    log_path = dest / f"{subcase}.log"
    entry = {
        "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "toolchain": toolchain,
        "log": str(log_path),
    }
    state[key] = entry
    _save_state(state)

    started = time.monotonic()
    with log_path.open("a") as log:
        log.write(f"=== {datetime.now(timezone.utc).isoformat()} start {key} ===\n")
        log.flush()
        proc = subprocess.run(
            [f"./plot_{subcase}"], cwd=dest, stdout=log, stderr=log
        )
    entry["wall_seconds"] = round(time.monotonic() - started, 1)
    entry["exit_code"] = proc.returncode
    entry["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if proc.returncode == 0:
        entry["status"] = "done"
        entry["outputs"] = {
            path.name: {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in sorted(dest.glob(f"*_rho=*_{subcase}.bin"))
        }
    else:
        entry["status"] = "failed"
    state[key] = entry
    _save_state(state)
    return entry


def regen_manifest() -> Manifest:
    """Manifest of every regenerated output currently on disk."""
    relpaths = []
    for family_dir in sorted(REGEN_ROOT.glob("*/")):
        for name in ("certificate", "child"):
            for path in sorted(family_dir.glob(f"{name}_rho=*.bin")):
                if path.is_file() and not path.is_symlink():
                    relpaths.append(str(path.relative_to(REGEN_ROOT)))
    return Manifest.build(
        REGEN_ROOT,
        relpaths,
        source={
            "kind": "regeneration",
            "generator": "their plot_*.cpp from the pinned snapshot",
            "snapshot_commit": acq.PINNED_COMMIT,
            "state": _load_state(),
        },
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="steiner_audit.regen")
    parser.add_argument("--family", default="d_regular")
    parser.add_argument("--subcase", default="f_ge_d", choices=["f_ge_d", "f_le_d"])
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--rho", default=None,
                        help="patch their generator's rho constant and run "
                        "in an isolated <family>@<rho> work dir (#16)")
    parser.add_argument("--manifest", action="store_true",
                        help="write the regeneration manifest artifact and exit")
    args = parser.parse_args(argv)

    if args.manifest:
        manifest = regen_manifest()
        out = acq.ARTIFACTS / "acquisition" / "regen_manifest.json"
        manifest.write(out)
        print(f"{len(manifest.files)} regenerated files hashed -> {out}")
        return 0

    entry = run_case(
        args.family, args.subcase, resume=not args.no_resume,
        rho_text=args.rho,
    )
    print(json.dumps(entry, indent=2))
    return 0 if entry.get("status") == "done" else 1


if __name__ == "__main__":
    sys.exit(main())

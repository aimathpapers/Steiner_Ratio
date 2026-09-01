"""Day-one acquisition: snapshot the PKU repo and download the published dataset.

Ops layer (smoke tests only, per the M1 testing decisions): multi-hour network
transfers are not unit-testable. Everything acquired lands under vendor/
(gitignored, ADR-0002 — unlicensed third-party artifacts are consumed locally,
never redistributed); the committed record is the manifest artifact.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.hf_api import RepoFile

from .manifest import Manifest

REPO_URL = "https://github.com/keyisi2006/Steiner-Ratio.git"
# HEAD observed at day-one snapshot (2026-08-12); matches the commit history
# recorded in docs/research/gilbert-pollak-pku-pipeline.md ("figure label update").
PINNED_COMMIT = "709673a8926fed0ef981d7db36dafcdf6f4a8a1d"

DATASET_ID = "keyisi/steiner-ratio"

STEINER_ROOT = Path(__file__).resolve().parents[2]
VENDOR = STEINER_ROOT / "vendor"
SNAPSHOT_DIR = VENDOR / "Steiner-Ratio"
DATASET_DIR = VENDOR / "dataset"
ARTIFACTS = STEINER_ROOT / "artifacts"


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def snapshot_repo(dest: Path = SNAPSHOT_DIR, url: str = REPO_URL) -> str:
    """Clone the PKU repo (if absent) and return its HEAD commit.

    Raises if an existing snapshot sits at a different commit than the pin —
    the audit target must not silently change under us.
    """
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--quiet", url, str(dest)], check=True
        )
    head = _git(["rev-parse", "HEAD"], cwd=dest)
    if head != PINNED_COMMIT:
        raise RuntimeError(
            f"snapshot HEAD {head} != pinned day-one commit {PINNED_COMMIT}"
        )
    return head


def snapshot_manifest(dest: Path = SNAPSHOT_DIR) -> Manifest:
    """Manifest of every git-tracked file in the snapshot (untracked build
    residue from running their tools is deliberately excluded)."""
    head = snapshot_repo(dest)
    tracked = _git(["ls-files", "-z"], cwd=dest).split("\0")
    relpaths = [p for p in tracked if p]
    source: dict[str, Any] = {
        "kind": "git-snapshot",
        "url": REPO_URL,
        "commit": head,
    }
    return Manifest.build(dest, relpaths, source)


def dataset_listing(dataset_id: str = DATASET_ID) -> list[dict[str, Any]]:
    """The published dataset's file list with sizes and publisher LFS sha256s."""
    api = HfApi()
    out = []
    for entry in api.list_repo_tree(dataset_id, repo_type="dataset", recursive=True):
        if not isinstance(entry, RepoFile):
            continue
        lfs = getattr(entry, "lfs", None)
        out.append(
            {
                "path": entry.path,
                "bytes": getattr(entry, "size", None),
                "publisher_sha256": lfs.sha256 if lfs else None,
            }
        )
    return out


def download_dataset_files(
    relpaths: list[str],
    dest: Path = DATASET_DIR,
    dataset_id: str = DATASET_ID,
) -> None:
    """Resumable download of the named dataset files into vendor/dataset/."""
    dest.mkdir(parents=True, exist_ok=True)
    for rel in relpaths:
        hf_hub_download(
            dataset_id,
            rel,
            repo_type="dataset",
            local_dir=str(dest),
        )


def dataset_manifest(
    dest: Path = DATASET_DIR, dataset_id: str = DATASET_ID
) -> Manifest:
    """Hash every downloaded dataset file against the publisher's LFS sha256."""
    listing = dataset_listing(dataset_id)
    declared = {
        e["path"]: e["publisher_sha256"] for e in listing if e["publisher_sha256"]
    }
    present = [e["path"] for e in listing if (dest / e["path"]).is_file()]
    source: dict[str, Any] = {
        "kind": "huggingface-dataset",
        "dataset": dataset_id,
        "url": f"https://huggingface.co/datasets/{dataset_id}",
        "published_files": len(listing),
    }
    return Manifest.build(dest, present, source, publisher_sha256=declared)

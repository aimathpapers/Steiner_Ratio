"""CLI for acquisition ops: python -m steiner_audit.acquire <command>."""

from __future__ import annotations

import argparse
import fnmatch
import sys

from . import acquisition as acq


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="steiner_audit.acquire")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("snapshot", help="clone the PKU repo and write its manifest")

    p_dl = sub.add_parser("download", help="download published dataset files")
    p_dl.add_argument(
        "--include",
        action="append",
        default=None,
        help="glob over dataset paths (default: everything)",
    )

    sub.add_parser(
        "manifest", help="hash downloaded dataset files and write the manifest"
    )

    args = parser.parse_args(argv)
    acq_dir = acq.ARTIFACTS / "acquisition"

    if args.command == "snapshot":
        manifest = acq.snapshot_manifest()
        out = acq_dir / "repo_manifest.json"
        manifest.write(out)
        print(f"snapshot at {manifest.source['commit']}: "
              f"{len(manifest.files)} tracked files -> {out}")

    elif args.command == "download":
        listing = acq.dataset_listing()
        paths = [e["path"] for e in listing]
        if args.include:
            paths = [
                p
                for p in paths
                if any(fnmatch.fnmatch(p, pat) for pat in args.include)
            ]
        total = sum(
            e["bytes"] or 0 for e in listing if e["path"] in set(paths)
        )
        print(f"downloading {len(paths)} files ({total / 1e9:.2f} GB)")
        acq.download_dataset_files(paths)
        print("download complete")

    elif args.command == "manifest":
        manifest = acq.dataset_manifest()
        out = acq_dir / "dataset_manifest.json"
        manifest.write(out)
        mismatched = [
            f.path for f in manifest.files if f.matches_publisher is False
        ]
        print(f"{len(manifest.files)} files hashed -> {out}")
        if mismatched:
            print(f"PUBLISHER HASH MISMATCH: {mismatched}", file=sys.stderr)
            return 1
        print("all downloaded files match publisher LFS sha256")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Smoke tests for the acquisition manifest (ops layer gets smoke tests only)."""

import hashlib
import json
from pathlib import Path

from steiner_audit.manifest import Manifest, sha256_file


def _make_tree(root: Path) -> None:
    (root / "sub").mkdir(parents=True)
    (root / "a.bin").write_bytes(b"\x00\x01\x02")
    (root / "sub" / "b.txt").write_text("hello")


def test_build_write_load_verify_roundtrip(tmp_path: Path) -> None:
    _make_tree(tmp_path)
    m = Manifest.build(
        tmp_path, ["a.bin", "sub/b.txt"], source={"kind": "test"}
    )
    assert [f.path for f in m.files] == ["a.bin", "sub/b.txt"]
    assert m.files[0].sha256 == hashlib.sha256(b"\x00\x01\x02").hexdigest()

    out = tmp_path / "manifest.json"
    m.write(out)
    doc = json.loads(out.read_text())
    assert doc["file_count"] == 2
    assert doc["total_bytes"] == 8

    loaded = Manifest.load(out)
    assert loaded.files == m.files
    assert loaded.verify(tmp_path) == []


def test_verify_reports_tamper_and_missing(tmp_path: Path) -> None:
    _make_tree(tmp_path)
    m = Manifest.build(tmp_path, ["a.bin", "sub/b.txt"], source={"kind": "test"})

    (tmp_path / "a.bin").write_bytes(b"\x00\x01\x03")  # same size, new content
    (tmp_path / "sub" / "b.txt").unlink()

    problems = m.verify(tmp_path)
    assert any(p.startswith("sha256 mismatch: a.bin") for p in problems)
    assert "missing: sub/b.txt" in problems


def test_publisher_hash_comparison(tmp_path: Path) -> None:
    _make_tree(tmp_path)
    right = sha256_file(tmp_path / "a.bin")
    m = Manifest.build(
        tmp_path,
        ["a.bin", "sub/b.txt"],
        source={"kind": "test"},
        publisher_sha256={"a.bin": right},
    )
    assert m.files[0].matches_publisher is True
    assert m.files[1].matches_publisher is None  # no declared hash

    wrong = Manifest.build(
        tmp_path, ["a.bin"], source={"kind": "test"},
        publisher_sha256={"a.bin": "0" * 64},
    )
    assert wrong.files[0].matches_publisher is False

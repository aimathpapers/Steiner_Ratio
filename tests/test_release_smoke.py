"""Smoke test for release staging: the ADR-0002 curation rules hold.

Runs against a real staging pass (needs the repository's committed
artifacts, not the dataset), so it is cheap but marked real_data because it
reads the working tree rather than fixtures.
"""

import gzip
import json
from pathlib import Path

import pytest

from steiner_audit.release import stage

pytestmark = pytest.mark.real_data


def test_staged_bundle_obeys_curation_rules(tmp_path: Path) -> None:
    manifest = stage(tmp_path / "staging")
    paths = [f.path for f in manifest.files]

    # nothing from the unlicensed upstream artifacts
    assert not any(p.startswith("vendor") for p in paths)
    assert not any("Steiner-Ratio" in p for p in paths)

    # the license and claim-scoped README ship
    assert "LICENSE" in paths
    readme = (tmp_path / "staging" / "README.md").read_text()
    assert "CERTIFICATE LAYER" in readme

    # diff artifacts are counts-only: no embedded upstream region records
    diffs = [p for p in paths if "semantic_diff_" in p]
    assert len(diffs) == 4
    for rel in diffs:
        doc = json.loads((tmp_path / "staging" / rel).read_text())
        assert doc["findings_localized"] == []
        assert "curation_note" in doc
        # the counts survive curation
        assert doc["published_records"] > 0

    # the spot-check verdict stream is present and parseable
    sample = [p for p in paths if p.startswith("verdicts_sample/")]
    if sample:  # present only when the full run exists locally
        with gzip.open(tmp_path / "staging" / sample[0], "rt") as f:
            row = json.loads(next(f))
        assert row["mode"] in ("vertex_parity", "full_box", "skipped")

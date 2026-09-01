"""Their checker as a per-region cross-check oracle (ADR-0002 test-oracle use).

Needs the snapshot, the dataset, and a working julia; ~1 minute.
"""

import shutil
from pathlib import Path

import pytest

from steiner_audit import acquisition as acq
from steiner_audit.crosscheck import crosscheck_region
from steiner_audit.records import RegionRecord, read_record_at

from test_kernel_boundary import BAD_BOX

pytestmark = [
    pytest.mark.real_data,
    pytest.mark.skipif(shutil.which("julia") is None, reason="no julia"),
]

CERT = acq.DATASET_DIR / "d_regular" / "certificate_rho=0.8559_f_ge_d.bin"


def test_their_checker_passes_a_real_region(tmp_path: Path) -> None:
    record = read_record_at(CERT, index=0, n=5)
    verdict = crosscheck_region(record, "d_regular", "f_ge_d", tmp_path)
    assert verdict.passed, verdict.raw_tail
    assert verdict.verified_count == 1


def test_their_checker_fails_the_sign_flipped_fixture(tmp_path: Path) -> None:
    record = RegionRecord(region_id=999, box=BAD_BOX, split_id=1, lemma_id=0)
    verdict = crosscheck_region(record, "d_regular", "f_ge_d", tmp_path)
    assert not verdict.passed
    assert "failed" in verdict.raw_tail

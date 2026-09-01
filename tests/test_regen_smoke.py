"""Smoke tests for the regeneration harness (ops layer)."""

import pytest

from steiner_audit import acquisition as acq
from steiner_audit.regen import patch_rho_source, work_dir

pytestmark = pytest.mark.real_data  # needs the vendored snapshot

_M1_OUTPUTS = (
    "certificate_rho=0.8559_f_ge_d.bin", "child_rho=0.8559_f_ge_d.bin",
    "certificate_rho=0.8559_f_le_d.bin", "child_rho=0.8559_f_le_d.bin",
)


def test_work_dir_is_isolated_from_dataset_symlinks() -> None:
    """The generator must never see the snapshot's dataset .bin symlinks:
    its outputs land in the work dir, or they would overwrite the downloaded
    dataset through the links."""
    dest = work_dir("d_regular")
    assert dest != acq.SNAPSHOT_DIR / "certificate" / "d_regular"
    for name in _M1_OUTPUTS:
        path = dest / name
        assert not path.is_symlink(), f"{name} is a symlink into the dataset"


def test_patch_rho_source_replaces_exactly_once() -> None:
    source = "const ld rho = 0.8559, INF = 1e18, eps = 1e-6;\n"
    patched = patch_rho_source(source, "0.856")
    assert "const ld rho = 0.856," in patched
    assert "0.8559" not in patched
    with pytest.raises(ValueError, match="exactly one"):
        patch_rho_source(source + source, "0.856")
    with pytest.raises(ValueError, match="exactly one"):
        patch_rho_source("no constant here", "0.856")
    for bad in ("1.5", "0.85591234567", "0.856; int x", "-0.5"):
        with pytest.raises(ValueError):
            patch_rho_source(source, bad)


def test_rho_work_dir_patches_copies_never_snapshot(tmp_path) -> None:
    dest = work_dir("d_regular", "0.856")
    assert dest.name == "d_regular@0.856"
    for name in ("plot_f_ge_d.cpp", "plot_f_le_d.cpp"):
        patched = dest / name
        assert not patched.is_symlink()  # a symlink would edit the snapshot
        assert "const ld rho = 0.856," in patched.read_text()
        original = acq.SNAPSHOT_DIR / "certificate" / "d_regular" / name
        assert "const ld rho = 0.8559," in original.read_text()
    assert (dest / "splits.txt").is_symlink()  # rho-independent inputs shared
    # sources are linked read-only from the snapshot
    assert (dest / "Makefile").is_symlink()
    assert (dest / "splits.txt").is_symlink()
    assert (dest / "formulas").is_symlink()

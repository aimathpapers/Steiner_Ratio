"""Verifier-boundary seam, decode half: malformed records must die at the door.

Fixtures are hand-crafted miniature certificate files in the PKU wire format
(little-endian: int32 region_id, n x (float64 low, float64 high), int32
split_id, int32 lemma_id).
"""

import math
import struct
from pathlib import Path

import pytest

from steiner_audit.records import DecodeError, RegionRecord, iter_records, write_records

N = 5  # d_regular f>=d layout used throughout these fixtures


def pack(region_id: int, box: list[tuple[float, float]], split_id: int, lemma_id: int) -> bytes:
    parts = [struct.pack("<i", region_id)]
    for low, high in box:
        parts.append(struct.pack("<dd", low, high))
    parts.append(struct.pack("<ii", split_id, lemma_id))
    return b"".join(parts)


GOOD_BOX = [(0.0, 1.0), (0.5, 1.0), (0.0, math.inf), (1.0, 2.0), (0.25, 0.375)]


def _write(path: Path, blob: bytes) -> Path:
    path.write_bytes(blob)
    return path


def test_roundtrip_write_then_iter(tmp_path: Path) -> None:
    records = [
        RegionRecord(region_id=1, box=tuple(GOOD_BOX), split_id=3, lemma_id=0),
        RegionRecord(
            region_id=2,
            box=tuple((float(i), float(i + 1)) for i in range(N)),
            split_id=160,
            lemma_id=8,
        ),
    ]
    path = tmp_path / "cert.bin"
    write_records(path, records, n=N)
    back = list(iter_records(path, n=N, n_splits=160))
    assert back == records


def test_empty_file_yields_nothing(tmp_path: Path) -> None:
    path = _write(tmp_path / "cert.bin", b"")
    assert list(iter_records(path, n=N)) == []


def test_truncated_final_record_rejected(tmp_path: Path) -> None:
    blob = pack(1, GOOD_BOX, 1, 0)
    path = _write(tmp_path / "cert.bin", blob + blob[:-3])
    with pytest.raises(DecodeError, match="truncated"):
        list(iter_records(path, n=N))


def test_low_above_high_rejected(tmp_path: Path) -> None:
    box = list(GOOD_BOX)
    box[2] = (2.0, 1.0)
    path = _write(tmp_path / "cert.bin", pack(7, box, 1, 0))
    with pytest.raises(DecodeError, match="region 7.*low > high"):
        list(iter_records(path, n=N))


def test_nan_bound_rejected(tmp_path: Path) -> None:
    box = list(GOOD_BOX)
    box[0] = (0.0, math.nan)
    path = _write(tmp_path / "cert.bin", pack(7, box, 1, 0))
    with pytest.raises(DecodeError, match="NaN"):
        list(iter_records(path, n=N))


def test_negative_low_rejected(tmp_path: Path) -> None:
    box = list(GOOD_BOX)
    box[1] = (-0.5, 1.0)
    path = _write(tmp_path / "cert.bin", pack(7, box, 1, 0))
    with pytest.raises(DecodeError, match="negative"):
        list(iter_records(path, n=N))


def test_infinite_low_rejected(tmp_path: Path) -> None:
    box = list(GOOD_BOX)
    box[3] = (math.inf, math.inf)
    path = _write(tmp_path / "cert.bin", pack(7, box, 1, 0))
    with pytest.raises(DecodeError, match="infinite low"):
        list(iter_records(path, n=N))


@pytest.mark.parametrize("split_id", [-2, 161])
def test_split_id_out_of_range_rejected(tmp_path: Path, split_id: int) -> None:
    path = _write(tmp_path / "cert.bin", pack(7, GOOD_BOX, split_id, 0))
    with pytest.raises(DecodeError, match="split_id"):
        list(iter_records(path, n=N, n_splits=160))


@pytest.mark.parametrize("split_id,lemma_id", [(0, 0), (-1, -1)])
def test_other_subcase_sentinels_are_decodable(
    tmp_path: Path, split_id: int, lemma_id: int
) -> None:
    # Both sentinel encodings exist in the wild: published data uses 0/0,
    # the snapshot's generator emits -1/-1. The kernel is responsible for
    # skipping or failing them, not the decoder.
    path = _write(tmp_path / "cert.bin", pack(7, GOOD_BOX, split_id, lemma_id))
    (record,) = iter_records(path, n=N, n_splits=160)
    assert record.split_id == split_id
    assert record.lemma_id == lemma_id


def test_negative_lemma_rejected_on_real_split(tmp_path: Path) -> None:
    path = _write(tmp_path / "cert.bin", pack(7, GOOD_BOX, 1, -1))
    with pytest.raises(DecodeError, match="lemma_id"):
        list(iter_records(path, n=N))


@pytest.mark.parametrize("lemma_id", [-1, 9])
def test_lemma_id_out_of_range_rejected(tmp_path: Path, lemma_id: int) -> None:
    path = _write(tmp_path / "cert.bin", pack(7, GOOD_BOX, 1, lemma_id))
    with pytest.raises(DecodeError, match="lemma_id"):
        list(iter_records(path, n=N))


def test_error_reports_record_index_and_offset(tmp_path: Path) -> None:
    good = pack(1, GOOD_BOX, 1, 0)
    bad_box = list(GOOD_BOX)
    bad_box[0] = (3.0, 2.0)
    blob = good + good + pack(9, bad_box, 1, 0)
    path = _write(tmp_path / "cert.bin", blob)
    with pytest.raises(DecodeError, match=r"record 2 at byte 184"):
        list(iter_records(path, n=N))


def test_writer_refuses_malformed(tmp_path: Path) -> None:
    bad = RegionRecord(
        region_id=1,
        box=tuple([(2.0, 1.0)] + GOOD_BOX[1:]),
        split_id=1,
        lemma_id=0,
    )
    with pytest.raises(DecodeError):
        write_records(tmp_path / "cert.bin", [bad], n=N)

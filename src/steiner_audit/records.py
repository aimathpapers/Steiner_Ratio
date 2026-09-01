"""Decoder for the PKU per-region certificate records.

The wire format is external and untrusted: little-endian, no padding —
int32 region_id, n x (float64 low, float64 high), int32 split_id, int32
lemma_id (certificate/README.md in the snapshot). Structure is validated as
records are read so malformed or truncated data is caught at the boundary,
never inside a verdict.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

N_LEMMAS = 9  # lemma_0.jl .. lemma_8.jl in every case directory


class DecodeError(Exception):
    """A certificate file violated the wire format."""


@dataclass(frozen=True)
class RegionRecord:
    region_id: int
    box: tuple[tuple[float, float], ...]  # (low, high) per variable
    split_id: int  # 1-based index into the case's splits.txt
    lemma_id: int  # 0-based index into the case's lemmas/

    @property
    def n(self) -> int:
        return len(self.box)


def _validate(record: RegionRecord, n_splits: int | None, where: str) -> None:
    for i, (low, high) in enumerate(record.box):
        if math.isnan(low) or math.isnan(high):
            raise DecodeError(f"{where}: NaN bound in variable {i}")
        if math.isinf(low):
            raise DecodeError(f"{where}: infinite low bound in variable {i}")
        if low < 0.0:
            raise DecodeError(f"{where}: negative bound in variable {i}")
        if low > high:
            raise DecodeError(f"{where}: low > high in variable {i}")
    # Undocumented generator sentinels for "box belongs to the other
    # f-subcase": the published datasets use split_id 0, the snapshot's
    # generator source emits split_id -1 / lemma_id -1 (a recorded
    # provenance finding — the published data and the shipped code disagree).
    # Their checker skips such records before indexing the split table; ours
    # does the same in the kernel, so both sentinels are decodable.
    if record.split_id < -1 or (n_splits is not None and record.split_id > n_splits):
        raise DecodeError(
            f"{where}: split_id {record.split_id} outside -1..{n_splits}"
        )
    lemma_low = -1 if record.split_id <= 0 else 0
    if not lemma_low <= record.lemma_id < N_LEMMAS:
        raise DecodeError(
            f"{where}: lemma_id {record.lemma_id} outside "
            f"{lemma_low}..{N_LEMMAS - 1}"
        )


def record_struct(n: int) -> struct.Struct:
    return struct.Struct("<i" + "dd" * n + "ii")


def _decode_blob(
    blob: bytes, fmt: struct.Struct, n: int, index: int, n_splits: int | None
) -> RegionRecord:
    where = f"record {index} at byte {index * fmt.size}"
    if len(blob) < fmt.size:
        raise DecodeError(f"{where}: truncated ({len(blob)} of {fmt.size} bytes)")
    fields = fmt.unpack(blob)
    record = RegionRecord(
        region_id=fields[0],
        box=tuple((fields[1 + 2 * i], fields[2 + 2 * i]) for i in range(n)),
        split_id=fields[1 + 2 * n],
        lemma_id=fields[2 + 2 * n],
    )
    _validate(record, n_splits, f"{where}: region {record.region_id}")
    return record


def iter_records(
    path: Path,
    n: int,
    n_splits: int | None = None,
    start: int = 0,
) -> Iterator[RegionRecord]:
    """Stream records from a certificate file, validating each.

    ``start`` skips that many leading records without validation (resume
    support); everything yielded is validated.
    """
    fmt = record_struct(n)
    with path.open("rb") as f:
        if start:
            f.seek(start * fmt.size)
        index = start
        while blob := f.read(fmt.size):
            yield _decode_blob(blob, fmt, n, index, n_splits)
            index += 1


def read_record_at(
    path: Path, index: int, n: int, n_splits: int | None = None
) -> RegionRecord:
    """Read and validate the record at a given index (records are fixed-size)."""
    fmt = record_struct(n)
    with path.open("rb") as f:
        f.seek(index * fmt.size)
        blob = f.read(fmt.size)
    return _decode_blob(blob, fmt, n, index, n_splits)


def count_records(path: Path, n: int) -> int:
    size = record_struct(n).size
    total = path.stat().st_size
    if total % size:
        raise DecodeError(
            f"file size {total} is not a multiple of record size {size}"
        )
    return total // size


def write_records(path: Path, records: Iterable[RegionRecord], n: int) -> int:
    """Write records (fixtures, capsules). As strict as the reader."""
    fmt = record_struct(n)
    count = 0
    with path.open("wb") as f:
        for record in records:
            if record.n != n:
                raise DecodeError(
                    f"record {count}: has {record.n} variables, expected {n}"
                )
            _validate(record, None, f"record {count}")
            flat: list[float] = []
            for low, high in record.box:
                flat.extend((low, high))
            f.write(
                fmt.pack(record.region_id, *flat, record.split_id, record.lemma_id)
            )
            count += 1
    return count

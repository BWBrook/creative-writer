"""Reading and windowing of the committed Phase 2B passage partitions."""

from __future__ import annotations

import json
from typing import Iterable

from pydantic import ValidationError

from creative_writer.exceptions import CreativeWriterError
from creative_writer.source_analysis_models import PassageRecord


def _validate_partition_records(records: list[PassageRecord]) -> None:
    """Validate identities and strict global reading order for one partition."""

    if not records:
        raise CreativeWriterError("passage partition must contain at least one passage")
    seen_ids: set[str] = set()
    previous_key: tuple[int, int] | None = None
    witness_ordinals: dict[str, int] = {}
    ordinal_witnesses: dict[int, str] = {}
    for record in records:
        if record.passage_id in seen_ids:
            raise CreativeWriterError(f"duplicate passage ID: {record.passage_id}")
        seen_ids.add(record.passage_id)
        if witness_ordinals.setdefault(record.witness_id, record.witness_ordinal) != record.witness_ordinal:
            raise CreativeWriterError(
                f"witness {record.witness_id} maps to multiple witness ordinals"
            )
        if ordinal_witnesses.setdefault(record.witness_ordinal, record.witness_id) != record.witness_id:
            raise CreativeWriterError(
                f"witness ordinal {record.witness_ordinal} maps to multiple witnesses"
            )
        key = (record.witness_ordinal, record.source_ordinal)
        if previous_key is not None and key <= previous_key:
            raise CreativeWriterError(
                "passage partition records must have strictly increasing global ordinals"
            )
        previous_key = key


def serialize_passage_partition(records: Iterable[PassageRecord]) -> bytes:
    """Serialize one physical partition as canonical compact UTF-8 JSONL."""

    try:
        validated = [
            PassageRecord.model_validate(
                record.model_dump(mode="json")
                if isinstance(record, PassageRecord)
                else record
            )
            for record in records
        ]
    except (ValidationError, TypeError) as exc:
        raise CreativeWriterError(f"Invalid passage record: {exc}") from exc
    validated.sort(key=lambda item: (item.witness_ordinal, item.source_ordinal))
    _validate_partition_records(validated)
    return b"".join(
        (
            json.dumps(
                record.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
        for record in validated
    )


def parse_passage_partition(data: bytes) -> list[PassageRecord]:
    """Parse and strictly validate canonical bytes for one physical partition."""

    if not isinstance(data, bytes):
        raise CreativeWriterError("passage partition must be supplied as bytes")
    if not data or data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise CreativeWriterError("passage partition must be non-empty UTF-8 JSONL without BOM or CR")
    if not data.endswith(b"\n") or b"\n\n" in data:
        raise CreativeWriterError("passage partition must contain exactly one LF per record")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CreativeWriterError(f"passage partition is not valid UTF-8: {exc}") from exc
    records: list[PassageRecord] = []
    for line_number, line in enumerate(text.split("\n")[:-1], start=1):
        if not line or line.startswith("\ufeff"):
            raise CreativeWriterError(f"Malformed passage partition line {line_number}: blank or BOM")
        try:
            payload = json.loads(line)
            record = PassageRecord.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise CreativeWriterError(
                f"Malformed passage partition line {line_number}: {exc}"
            ) from exc
        canonical_line = json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if line != canonical_line:
            raise CreativeWriterError(
                f"Malformed passage partition line {line_number}: non-canonical JSON"
            )
        records.append(record)
    _validate_partition_records(records)
    return records


def _same_boundary(left: PassageRecord, right: PassageRecord) -> bool:
    return left.witness_id == right.witness_id and left.heading_path == right.heading_path


def context_window(
    passages: list[PassageRecord], passage_id: str, radius: int = 2
) -> list[PassageRecord]:
    """Return a focal passage and bounded neighbours in reading order."""

    if radius < 0 or radius > 2:
        raise CreativeWriterError("context radius must be between 0 and 2")
    matches = [index for index, passage in enumerate(passages) if passage.passage_id == passage_id]
    if not matches:
        raise CreativeWriterError(f"Unknown passage ID: {passage_id}")
    if len(matches) != 1:
        raise CreativeWriterError(f"duplicate passage ID in context input: {passage_id}")
    focal_index = matches[0]
    start = focal_index
    for _ in range(radius):
        candidate = start - 1
        if candidate < 0 or not _same_boundary(passages[candidate], passages[focal_index]):
            break
        start = candidate
    end = focal_index
    for _ in range(radius):
        candidate = end + 1
        if candidate >= len(passages) or not _same_boundary(passages[candidate], passages[focal_index]):
            break
        end = candidate
    return passages[start : end + 1]

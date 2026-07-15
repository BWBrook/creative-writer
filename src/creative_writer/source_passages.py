"""Deterministic passage extraction and indexing for retained Markdown witnesses."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from creative_writer.exceptions import CreativeWriterError
from creative_writer.source_analysis_models import (
    PassageRecord,
    WitnessDescriptor,
    _heading_slug,
)


_HORIZONTAL_WHITESPACE = re.compile(r"[^\S\n]+")
_OPENING_QUOTES = frozenset('"\'“‘«„‚‹')
_CONTAINER_INLINES = frozenset(
    {
        "Emph",
        "Strong",
        "Strikeout",
        "Superscript",
        "Subscript",
        "SmallCaps",
        "Underline",
        "Span",
    }
)
_LIST_BLOCKS = frozenset({"OrderedList", "BulletList"})
_NON_PASSAGE_BLOCKS = frozenset(
    {"Image", "HorizontalRule", "CodeBlock", "RawBlock", "Table", "Null"}
)


class _MalformedAst(ValueError):
    pass


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise _MalformedAst(f"{label} must be a list")
    return value


def _node_type(node: Any) -> str:
    if not isinstance(node, dict) or not isinstance(node.get("t"), str):
        raise _MalformedAst("AST node must contain a string t constructor")
    return node["t"]


def _inline_text(inlines: Any) -> str:
    result: list[str] = []
    for inline in _require_list(inlines, "inline content"):
        kind = _node_type(inline)
        content = inline.get("c")
        if kind == "Str":
            if not isinstance(content, str):
                raise _MalformedAst("Str content must be a string")
            result.append(content)
        elif kind in {"Space", "SoftBreak"}:
            result.append(" ")
        elif kind == "LineBreak":
            result.append("\n")
        elif kind in _CONTAINER_INLINES:
            if kind == "Span":
                parts = _require_list(content, "Span content")
                if len(parts) != 2:
                    raise _MalformedAst("Span content must contain attributes and inlines")
                result.append(_inline_text(parts[1]))
            else:
                result.append(_inline_text(content))
        elif kind == "Quoted":
            parts = _require_list(content, "Quoted content")
            if len(parts) != 2 or not isinstance(parts[0], dict):
                raise _MalformedAst("Quoted content must contain a tagged quote type and inlines")
            quote_type = parts[0].get("t")
            if quote_type not in {"SingleQuote", "DoubleQuote"}:
                raise _MalformedAst("Quoted content must contain a tagged quote type")
            quote = {"SingleQuote": "'", "DoubleQuote": '"'}[quote_type]
            result.append(f"{quote}{_inline_text(parts[1])}{quote}")
        elif kind == "Cite":
            parts = _require_list(content, "Cite content")
            if len(parts) != 2:
                raise _MalformedAst("Cite content must contain citations and inlines")
            result.append(_inline_text(parts[1]))
        elif kind == "Code":
            parts = _require_list(content, "Code content")
            if len(parts) != 2 or not isinstance(parts[1], str):
                raise _MalformedAst("Code content must contain attributes and text")
            result.append(parts[1])
        elif kind == "Math":
            parts = _require_list(content, "Math content")
            if len(parts) != 2 or not isinstance(parts[1], str):
                raise _MalformedAst("Math content must contain a type and text")
            result.append(parts[1])
        elif kind in {"Link", "Image"}:
            parts = _require_list(content, f"{kind} content")
            if len(parts) != 3:
                raise _MalformedAst(f"{kind} content must contain attributes, inlines, and target")
            # Image alt text is metadata, not analytical prose. A surrounding
            # paragraph remains indexable through its other inline content.
            if kind == "Link":
                result.append(_inline_text(parts[1]))
        elif kind == "Note":
            note_blocks = _require_list(content, "Note content")
            result.append(_blocks_text(note_blocks))
        elif kind == "RawInline":
            # Raw markup is apparatus, not retained analytical text.
            continue
        else:
            raise _MalformedAst(f"unsupported inline constructor: {kind}")
    return "".join(result)


def _block_text(blocks: Any) -> str:
    """Extract text from blocks without emitting nested passage records."""

    result: list[str] = []
    for block in _require_list(blocks, "block content"):
        kind = _node_type(block)
        content = block.get("c")
        if kind in {"Para", "Plain"}:
            result.append(_inline_text(content))
        elif kind == "LineBlock":
            result.append(_line_block_text(content))
        elif kind == "BlockQuote":
            result.append(_block_text(content))
        elif kind in _LIST_BLOCKS:
            result.append(_list_text(block))
        elif kind == "Header":
            parts = _require_list(content, "Header content")
            if len(parts) != 3:
                raise _MalformedAst("Header content must contain level, attributes, and inlines")
            result.append(_inline_text(parts[2]))
        elif kind in _NON_PASSAGE_BLOCKS or kind in {"Div", "DefinitionList"}:
            if kind == "Div":
                parts = _require_list(content, "Div content")
                if len(parts) != 2:
                    raise _MalformedAst("Div content must contain attributes and blocks")
                result.append(_block_text(parts[1]))
            elif kind == "DefinitionList":
                result.append(_definition_list_text(content))
        else:
            raise _MalformedAst(f"unsupported block constructor: {kind}")
    return "\n".join(part for part in result if part)


def _blocks_text(blocks: Any) -> str:
    return _block_text(blocks)


def _line_block_text(content: Any) -> str:
    return "\n".join(_inline_text(line) for line in _require_list(content, "LineBlock content"))


def _list_items(content: Any, kind: str) -> list[Any]:
    if not isinstance(content, list):
        raise _MalformedAst("list content must be a list")
    if kind == "OrderedList":
        if len(content) != 2 or not isinstance(content[1], list):
            raise _MalformedAst("OrderedList content must contain attributes and items")
        return content[1]
    return content


def _list_item_text(item: Any) -> str:
    blocks = _require_list(item, "list item")
    direct: list[str] = []
    for block in blocks:
        kind = _node_type(block)
        if kind in _LIST_BLOCKS:
            continue
        if kind in _NON_PASSAGE_BLOCKS:
            continue
        direct.append(_block_text([block]))
    return "\n".join(part for part in direct if part)


def _nested_lists(item: Any) -> Iterable[Any]:
    for block in _require_list(item, "list item"):
        if _node_type(block) in _LIST_BLOCKS:
            yield block


def _list_text(block: dict[str, Any]) -> str:
    result: list[str] = []
    kind = _node_type(block)
    for item in _list_items(block.get("c"), kind):
        result.append(_list_item_text(item))
        result.extend(_list_text(nested) for nested in _nested_lists(item))
    return "\n".join(part for part in result if part)


def _definition_list_text(content: Any) -> str:
    result: list[str] = []
    for definition in _require_list(content, "DefinitionList content"):
        parts = _require_list(definition, "definition")
        if len(parts) != 2:
            raise _MalformedAst("definition must contain term and definitions")
        result.append(_inline_text(parts[0]))
        for definition in _require_list(parts[1], "definition blocks"):
            result.append(_block_text(definition))
    return "\n".join(part for part in result if part)


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\ufeff", "")
    text = text.replace("\u00a0", " ").replace("\u200a", " ")
    lines = [_HORIZONTAL_WHITESPACE.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def _dialogue_classification(text: str) -> str:
    stripped = text.lstrip()
    if not stripped:
        return "unknown"
    opening_positions: list[int] = []
    for index, character in enumerate(stripped):
        if character not in _OPENING_QUOTES:
            continue
        if character == "'" and index > 0 and stripped[index - 1].isalnum():
            continue
        opening_positions.append(index)
    if not opening_positions:
        return "none"
    return "direct" if opening_positions[0] == 0 else "mixed"


def _passage(
    *,
    witness: WitnessDescriptor,
    heading_path: tuple[str, ...],
    block_type: str,
    source_ordinal: int,
    heading_ordinal: int,
    original_text: str,
) -> PassageRecord | None:
    normalized_text = _normalize_text(original_text)
    if not normalized_text:
        return None
    content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    heading_label = heading_path[-1]
    passage_id = (
        f"{witness.witness_id}:{_heading_slug(heading_label)}:"
        f"{source_ordinal}:{content_hash[:12]}"
    )
    return PassageRecord(
        witness_id=witness.witness_id,
        witness_ordinal=witness.witness_ordinal,
        source_id=witness.source_id,
        selection_id=witness.selection_id,
        source_fingerprint=witness.source_fingerprint,
        heading_path=list(heading_path),
        heading_label=heading_label,
        block_type=block_type,
        source_ordinal=source_ordinal,
        heading_ordinal=heading_ordinal,
        normalized_text=normalized_text,
        original_text=original_text,
        word_count=len(re.findall(r"\S+", normalized_text)),
        direct_dialogue=_dialogue_classification(normalized_text),
        content_hash=content_hash,
        passage_id=passage_id,
    )


def parse_markdown_witness(
    path: Path, witness: WitnessDescriptor | dict[str, Any], pandoc: str = "pandoc"
) -> list[PassageRecord]:
    """Parse one retained Markdown witness through Pandoc's JSON AST."""

    try:
        witness = WitnessDescriptor.model_validate(witness)
    except ValidationError as exc:
        raise CreativeWriterError(f"Invalid witness descriptor: {exc}") from exc
    try:
        completed = subprocess.run(
            [pandoc, "--from=gfm", "--to=json", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CreativeWriterError(f"Pandoc executable not found: {pandoc}") from exc
    except OSError as exc:
        raise CreativeWriterError(f"Unable to invoke Pandoc: {exc}") from exc
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        detail = f": {stderr}" if stderr else ""
        raise CreativeWriterError(f"Pandoc failed with exit code {completed.returncode}{detail}")
    try:
        ast = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeWriterError(f"Malformed Pandoc AST: {exc}") from exc
    if not isinstance(ast, dict) or not isinstance(ast.get("blocks"), list):
        raise CreativeWriterError("Malformed Pandoc AST: blocks must be a list")

    passages: list[PassageRecord] = []
    heading_stack: list[tuple[int, str]] = []
    previous_path: tuple[str, ...] | None = None
    source_ordinal = 0
    heading_ordinal = 0

    def add(block_type: str, original_text: str) -> None:
        nonlocal heading_ordinal, previous_path, source_ordinal
        path_value = tuple(label for _, label in heading_stack) or ("Untitled",)
        next_heading_ordinal = 1 if path_value != previous_path else heading_ordinal + 1
        candidate = _passage(
            witness=witness,
            heading_path=path_value,
            block_type=block_type,
            source_ordinal=source_ordinal + 1,
            heading_ordinal=next_heading_ordinal,
            original_text=original_text,
        )
        if candidate is not None:
            source_ordinal += 1
            heading_ordinal = next_heading_ordinal
            previous_path = path_value
            passages.append(candidate)

    def process_list(block: dict[str, Any]) -> None:
        for item in _list_items(block.get("c"), _node_type(block)):
            original = _list_item_text(item)
            add("list_item", original)
            for nested in _nested_lists(item):
                process_list(nested)

    def process_blocks(blocks: list[Any]) -> None:
        for block in blocks:
            kind = _node_type(block)
            content = block.get("c")
            if kind == "Header":
                parts = _require_list(content, "Header content")
                if len(parts) != 3 or not isinstance(parts[0], int) or parts[0] < 1:
                    raise _MalformedAst("Header content must contain level, attributes, and inlines")
                label = _normalize_text(_inline_text(parts[2]))
                if label:
                    while heading_stack and heading_stack[-1][0] >= parts[0]:
                        heading_stack.pop()
                    heading_stack.append((parts[0], label))
                continue
            if kind in {"Para", "Plain"}:
                add("paragraph", _inline_text(content))
            elif kind == "BlockQuote":
                add("block_quote", _blocks_text(content))
            elif kind == "LineBlock":
                add("verse", _line_block_text(content))
            elif kind in _LIST_BLOCKS:
                process_list(block)
            elif kind == "Div":
                parts = _require_list(content, "Div content")
                if len(parts) != 2:
                    raise _MalformedAst("Div content must contain attributes and blocks")
                process_blocks(_require_list(parts[1], "Div blocks"))
            elif kind in _NON_PASSAGE_BLOCKS or kind == "DefinitionList":
                continue
            else:
                raise _MalformedAst(f"unsupported block constructor: {kind}")

    try:
        process_blocks(ast["blocks"])
    except _MalformedAst as exc:
        raise CreativeWriterError(f"Malformed Pandoc AST: {exc}") from exc
    if not passages:
        raise CreativeWriterError(f"Pandoc produced no substantive passages for {path}")
    return passages


def _validate_index_records(
    records: list[PassageRecord], *, require_reading_order: bool
) -> None:
    if not records:
        raise CreativeWriterError("passage index must contain at least one passage")

    seen_ids: set[str] = set()
    witness_ordinals: dict[str, int] = {}
    ordinal_witnesses: dict[int, str] = {}
    for record in records:
        if record.passage_id in seen_ids:
            raise CreativeWriterError(f"duplicate passage ID: {record.passage_id}")
        seen_ids.add(record.passage_id)
        existing_ordinal = witness_ordinals.setdefault(record.witness_id, record.witness_ordinal)
        if existing_ordinal != record.witness_ordinal:
            raise CreativeWriterError(
                f"witness {record.witness_id} maps to multiple witness ordinals"
            )
        existing_witness = ordinal_witnesses.setdefault(
            record.witness_ordinal, record.witness_id
        )
        if existing_witness != record.witness_id:
            raise CreativeWriterError(
                f"witness ordinal {record.witness_ordinal} maps to multiple witnesses"
            )

    expected_ordinals = set(range(1, len(witness_ordinals) + 1))
    if set(ordinal_witnesses) != expected_ordinals:
        raise CreativeWriterError("witness ordinals must be contiguous from 1")

    if require_reading_order:
        keys = [(record.witness_ordinal, record.source_ordinal) for record in records]
        if keys != sorted(keys):
            raise CreativeWriterError(
                "passage index records must be ordered by witness_ordinal then source_ordinal"
            )

    current_witness: str | None = None
    expected_source_ordinal = 1
    previous_heading_path: tuple[str, ...] | None = None
    expected_heading_ordinal = 0
    for record in records:
        if record.witness_id != current_witness:
            current_witness = record.witness_id
            expected_source_ordinal = 1
            previous_heading_path = None
            expected_heading_ordinal = 0

        if record.source_ordinal != expected_source_ordinal:
            raise CreativeWriterError(
                f"source ordinals for witness {record.witness_id} must be exactly 1..n"
            )
        expected_source_ordinal += 1

        heading_path = tuple(record.heading_path)
        expected_heading_ordinal = (
            1
            if heading_path != previous_heading_path
            else expected_heading_ordinal + 1
        )
        if record.heading_ordinal != expected_heading_ordinal:
            raise CreativeWriterError(
                f"heading ordinals for witness {record.witness_id} must reset to 1 when "
                "heading_path changes and increment by one while unchanged"
            )
        previous_heading_path = heading_path


def serialize_passage_index(passages: Iterable[PassageRecord]) -> bytes:
    """Validate and serialize passage records as deterministic JSON Lines."""
    try:
        records = [
            PassageRecord.model_validate(
                passage.model_dump(mode="json")
                if isinstance(passage, PassageRecord)
                else passage
            )
            for passage in passages
        ]
    except (ValidationError, TypeError) as exc:
        raise CreativeWriterError(f"Invalid passage record: {exc}") from exc
    records.sort(key=lambda item: (item.witness_ordinal, item.source_ordinal))
    _validate_index_records(records, require_reading_order=True)
    return "".join(
        json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for record in records
    ).encode("utf-8")


def write_passage_index(path: Path, passages: Iterable[PassageRecord]) -> None:
    """Write validated passage records as deterministic UTF-8 JSON Lines."""

    serialized = serialize_passage_index(passages)

    temporary_path: Path | None = None
    write_error: CreativeWriterError | None = None
    try:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CreativeWriterError(
                f"Unable to create passage index directory {path.parent}: {exc}"
            ) from exc
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(serialized.decode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    except CreativeWriterError as exc:
        write_error = exc
    except OSError as exc:
        write_error = CreativeWriterError(f"Unable to write passage index {path}: {exc}")

    cleanup_error: OSError | None = None
    if temporary_path is not None:
        try:
            temporary_path.unlink()
        except OSError as exc:
            cleanup_error = exc

    if cleanup_error is not None:
        residual = temporary_path
        detail = (
            f"temporary passage index remains at {residual}; "
            f"temporary cleanup failed: {cleanup_error}"
        )
        if write_error is not None:
            detail = f"{write_error}; {detail}"
        raise CreativeWriterError(detail) from cleanup_error
    if write_error is not None:
        raise write_error


def read_passage_index(path: Path) -> list[PassageRecord]:
    """Read and strictly validate a JSON Lines passage index."""

    records: list[PassageRecord] = []
    seen: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise CreativeWriterError(f"Unable to read passage index {path}: {exc}") from exc
    if not lines:
        raise CreativeWriterError(f"Passage index {path} is empty")
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise CreativeWriterError(f"Malformed passage index line {line_number}: blank line")
        try:
            payload = json.loads(line)
            record = PassageRecord.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise CreativeWriterError(
                f"Malformed passage index line {line_number}: {exc}"
            ) from exc
        if record.passage_id in seen:
            raise CreativeWriterError(f"duplicate passage ID: {record.passage_id}")
        seen.add(record.passage_id)
        records.append(record)
    _validate_index_records(records, require_reading_order=True)
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


def partition_windows(
    passages: list[PassageRecord], max_blocks: int = 5
) -> list[list[PassageRecord]]:
    """Partition reading-order passages into non-overlapping section windows."""

    if type(max_blocks) is not int or not 1 <= max_blocks <= 5:
        raise CreativeWriterError("max_blocks must be a strict integer between 1 and 5")
    windows: list[list[PassageRecord]] = []
    current: list[PassageRecord] = []
    for passage in passages:
        if current and not _same_boundary(current[-1], passage):
            windows.append(current)
            current = []
        current.append(passage)
        if len(current) == max_blocks:
            windows.append(current)
            current = []
    if current:
        windows.append(current)
    return windows

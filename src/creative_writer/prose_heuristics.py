"""Shared, location-aware prose surface heuristics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from creative_writer.models import LintSettings


_CONTRASTIVE_PATTERN = re.compile(
    r"\b(?:not only\b[^.!?\n]{0,80}\bbut also|not\b[^.!?\n]{0,80}\bbut)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class SurfaceHeuristicWarning:
    rule_id: Literal["em-dash-overuse", "contrastive-parallelism"]
    observed: str
    line_start: int
    line_end: int


def _line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def run_surface_heuristics(
    text: str,
    lint: LintSettings,
) -> list[SurfaceHeuristicWarning]:
    """Return configured warnings in the legacy check order."""

    warnings: list[SurfaceHeuristicWarning] = []
    em_dash_positions = [
        position for position, character in enumerate(text) if character == "—"
    ]
    em_dash_limit = lint.em_dash.max_per_chapter
    if lint.em_dash.enabled and len(em_dash_positions) > em_dash_limit:
        warnings.append(
            SurfaceHeuristicWarning(
                rule_id="em-dash-overuse",
                observed=(
                    f"Em dash count {len(em_dash_positions)} exceeds configured "
                    f"limit {em_dash_limit}."
                ),
                line_start=_line_number(text, em_dash_positions[0]),
                line_end=_line_number(text, em_dash_positions[-1]),
            )
        )

    contrastive_matches = list(_CONTRASTIVE_PATTERN.finditer(text))
    contrastive_limit = lint.contrastive_parallelism.max_instances_per_chapter
    if (
        lint.contrastive_parallelism.enabled
        and len(contrastive_matches) > contrastive_limit
    ):
        warnings.append(
            SurfaceHeuristicWarning(
                rule_id="contrastive-parallelism",
                observed=(
                    f"Contrastive parallelism count {len(contrastive_matches)} "
                    f"exceeds configured limit {contrastive_limit}."
                ),
                line_start=_line_number(text, contrastive_matches[0].start()),
                line_end=_line_number(text, contrastive_matches[-1].end() - 1),
            )
        )

    return warnings

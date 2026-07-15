# Task 5 final audit fixes

## Completed action

Implemented the final Task 5 remediation for source-analysis lifecycle,
provenance, leakage, jurisdiction, Markdown grammar, and post-metric
diagnostics. Production changes are limited to `source_analysis.py` and
`source_evidence.py`; no schema change was required.

## Changed files

- `src/creative_writer/source_analysis.py`
- `src/creative_writer/source_evidence.py`
- `tests/test_source_analysis.py`
- `.superpowers/sdd/task-5-final-audit-fixes.md`

## Implementation notes

- Development now requires all five canonical evidence artifacts and the
  registry-derived retained-source dossiers.
- Structured artifact study identities are checked against `analysis.yml`.
  Populated protocol ledger, quantitative, and validation artifacts are
  rejected; genuinely empty protocol templates may remain during development.
- Populated quantitative profiles always receive current JSON/CSV provenance,
  hash/path, witness-set, and dotted scalar equality checks.
- Leakage validation scans forbidden witness IDs, forbidden passage IDs with
  boundary-safe matching, and normalized full-passage text across tracked and
  generated development artifacts.
- Counterexample references/searches and observation comparisons must exercise
  the claim or observation's declared jurisdiction role.
- Observation and profile grammar now rejects duplicate sections, stray or
  rogue record content, and unbackticked claim IDs. Profile findings require
  exact classification/confidence declarations matching their linked claims,
  with sorted deterministic disagreement diagnostics.
- Post-metric schema, read, and grammar failures atomically replace
  `development-report.md` with deterministic diagnostics before re-raising.
- Synthetic fixtures now include all mandatory canonical artifacts, and the
  holdout-locator test includes an actual within-witness holdout passage ID.

## TDD and verification

Focused adversarial tests were added and run before production edits:

```text
uv run pytest tests/test_source_analysis.py tests/test_source_analysis_models.py -q
23 failed, 124 passed in 20.24s
```

The RED failures reproduced the requested bypasses: missing canonical files,
structured identity mismatches, populated protocol artifacts, missing
post-metric diagnostics, role-A versus role-B jurisdiction acceptance,
duplicate or malformed Markdown grammar, profile classification/provenance
mismatches, stage-gated quantitative validation, and passage-ID leakage.

Final verification:

```text
uv run pytest tests/test_source_analysis.py tests/test_source_analysis_models.py -q
147 passed in 20.29s

uv run pytest -q
321 passed in 29.85s

uv run python -m compileall -q src tests
passed (exit 0)

git diff --check
passed (exit 0)
```

## Remaining caveats

The existing leakage rule continues to identify exact normalized full-passage
copies; short, edited, or paraphrased holdout material remains a human-review
risk by design. No changes were made to source texts, manuscript prose,
Phase 2C/style-card files, Permian planning, real holdouts, or real
interpretive artifacts.

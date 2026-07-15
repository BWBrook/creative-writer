# Task 6A review fixes

## 1. Completed action and changed files

Fixed the assigned Task 6A review findings on current `main`.

Changed files:

- `src/creative_writer/source_analysis.py`
- `tests/test_source_analysis.py`
- `tests/test_source_passages.py`
- `.superpowers/sdd/task-6a-review-fixes.md`

No real prepare/source/holdout/control access was performed. No raw source,
holdout, manuscript, or out-of-scope artefact was changed.

## 2. Implementation notes

- Transitional `heldout_assessed` and `complete` validation now loads the
  held-out Wells index, validates every held-out result's declared claim,
  witness, authority tier, role, and passage IDs against that partition, and
  only then opens the Tier 4 controls. A present-but-wrong-partition passage
  therefore fails before the control bound reader is called.
- Replaced weak partition-union coverage with an independently parsed retained
  Markdown witness ID set. Prepare rerun coverage now compares exact bytes for
  the corpus lock and all three indexes, plus exact manifest index bindings.
- Added a parameterized bound-index tamper matrix for mutate, truncate,
  reorder/swap, duplicate, and append across development, held-out Wells, and
  Tier 4 control indexes. Each case proves SHA-256 rejection before partition
  parsing.
- Added explicit canonical partition parser coverage for BOM, blank lines,
  noncanonical JSON, duplicate records/IDs, reordered and non-increasing
  ordinals, and invalid `PassageRecord` identity/hash fields.
- Develop and frozen validation tests now use direct `_read_bound_partition`
  spies and remove forbidden indexes/retained Markdown, proving only the
  permitted partition is opened.
- Task 6B caveat recorded: a managed `validation/current` symlink resolver and
  publication hardening remain required; publication is not implemented here.

## 3. Verification performed and results

RED evidence before the source change:

```text
uv run pytest tests/test_source_analysis.py -q -k 'present_wrong_partition_result or reads_only_development_partition or validate_frozen_pass'
2 passed, 1 failed
Failure: read trace was ['heldout_wells', 'tier4_controls'] instead of ['heldout_wells'].
```

Focused review GREEN:

```text
uv run pytest tests/test_source_analysis.py tests/test_source_passages.py -q -k 'present_wrong_partition_result or reads_only_development_partition or validate_frozen_pass or bound_partition_tampering or holdout_manifest_has_all_fingerprints or prepare_rerun_is_byte_stable or partition_parser or canonical_partition'
28 passed, 195 deselected in 5.73s
```

Required suite checks:

```text
uv run pytest tests/test_source_analysis.py tests/test_source_passages.py tests/test_source_analysis_models.py -q
284 passed in 40.03s

uv run pytest -q
420 passed in 48.82s

uv run python -m compileall -q src tests
passed

git diff --check
passed
```

## 4. Remaining caveats, assumptions, or escalation

The real corpus workflow remains intentionally unexecuted in this remediation
unit. Task 6B must implement and verify the managed `validation/current`
symlink resolver and publication path before any real validation packet is
published. No escalation is required for the assigned Task 6A fixes.

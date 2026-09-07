# Forensic Source Study

This directory stores source-study evidence and method, never manuscript prose.

`admission.yml` is the exact corpus gate. Admission is complete and the corpus
is closed at twelve retained, admitted records plus one excluded, unacquired
metadata record. No records remain approved or proposed.

`original/sources.yml` contains exactly the twelve retained records. *The Lost
World* remains Tier 5 and intentionally has no retained artifact.

The admitted corpus passed its admission gate, the deterministic Phase 2B
partition is locked in `holdouts.yml`, and the analysis is complete.

## Phase 2B evidence layer

The study is closed. The staged pipeline that produced it (`source-admission`
and `source-analysis prepare/develop/validate`) was retired from the codebase
once the evidence layer was approved; its last version is in Git history at
commit `59ab51a`. The `build/` paths recorded inside the frozen YAML files
below are where that pipeline wrote its outputs and are kept as historical
record.

The three physically separate, hash-bound passage indexes are committed here:

- `indexes/development.jsonl` for Tier 1-3 development material;
- `indexes/heldout-wells.jsonl` for held-out Wells material;
- `indexes/tier4-controls.jsonl` for Tier 4 comparative controls.

The real partition contains twelve retained sources and fifteen analytical
witnesses. *The Star* is held out in full; the other Tier 1-3 witnesses use
deterministic within-work holdouts, while all Tier 4 material remains outside
the development index. Re-running `prepare` reproduces the tracked manifest
and generated indexes byte for byte.

`develop` can read only the development index and is available only before the
candidate freeze, while analysis status is `protocol` or `development`.
Validation follows the strict
two-pass sequence `frozen -> heldout_assessed -> complete`: the frozen pass
reads held-out Wells only; after complete held-out assessments are committed,
the held-out-only `heldout_assessed` record authorises a pass that reads Tier 4
and generates the control-inclusive metrics and packet. Control comparisons,
reviewer records, and claim transitions are authored from that output and
committed only for the `complete` pass, which checks final outcomes and
compiles the final report.

The candidate freeze records a reachable Git commit and exact hashes for the
candidate `analysis.yml`, `holdouts.yml`, profile, and evidence ledger.
Candidate `analysis.yml` and `holdouts.yml` are immutable authorities for the
entire validation lifecycle, as are the candidate Git objects for the profile
and ledger. At `complete`, the writer-facing profile and ledger may contain
reviewed final forms. Each is read from a trusted Git blob and checked against
its separately recorded final SHA-256; the profile is then semantically
validated against the final ledger and analysis contract before use. Generated
validation outputs publish through the managed `validation/current` generation
pointer.

## Phase 2B result

The final evidence layer contains ten frozen candidate claims. Held-out Wells
assessment produced 21 supporting and four qualifying target results. Tier 4
comparison found nine broad features shared with neighbouring prose and one
local non-match in the Haggard journey ending. Root synthesis of the distributed
assessments retained six claims as `validated` and four as `qualified`; none was
rejected or assigned strong confidence. An independent acceptance audit first
requested completion-gate repairs, then approved the repaired evidence layer on
re-review.

The writer-facing synthesis is `wells-profile.md`, the claim store is
`evidence-ledger.yml`, and the negative-control analysis is
`period-controls.md`.

This workflow remains descriptive and source-bound. Phase 2B did not author
style guidance, alter a style card, plan the Permian material, or change
manuscript prose. Barry gave substantive approval to the Phase 2B evidence
layer on 23 July 2026.

## Phase 2C operational handoff

The approved Phase 2C consumer is `../style-profile.yml`, version `1.0.0`. It
binds the final analysis, source registry, holdout manifest, ledger, validation
record, and all three generated indexes by SHA-256. It may operationalise only
claims whose final status is `validated` or `qualified`, and every rule retains
the linked claim's exact scope, limits, and prohibited overgeneralisation.

Six manifests under `../style-reference-packets/` select the approved focal
locators for deliberate role-matched comparison. Tier 4 passages remain
negative controls and may appear only under `Negative comparisons`; the
`traveller-account` packet intentionally uses Wells variation without a Tier 4
control. The writer-facing `../style-guide.md` and `../style-card.md` distil
this evidence but do not supersede it. Phase 2C adds no historical or scientific
research and changes no manuscript prose.

## Approved handoff

The agreed order is Permian story ideation, Phase 2C operational distillation,
then the Permian research dossier before manuscript drafting. That dossier must
distinguish current scientific nomenclature and interpretation from the names,
geological concepts, climatic vocabulary, and biological classifications
available to an informed writer and traveller in the late 1890s.

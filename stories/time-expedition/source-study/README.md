# Forensic Source Study

This directory stores source-study evidence and method, never manuscript prose.

`admission.yml` is the exact corpus gate. Admission is complete and the corpus
is closed at twelve retained, admitted records plus one excluded, unacquired
metadata record. No records remain approved or proposed.

`original/sources.yml` contains exactly the twelve retained records. *The Lost
World* remains Tier 5 and intentionally has no retained artifact.

The generated review surface is
`build/time-expedition/reports/source-admission-report.md`. It reconciles the
admission record with retained-source metadata and shows authority, permitted
and prohibited uses, selected subworks, edition risks, and retained
fingerprints, derivation, provenance, and rights. The admitted corpus has now
passed this gate and the deterministic Phase 2B partition is locked in
`holdouts.yml`. Detailed evidentiary analysis has not yet begun.

## Phase 2B staged analysis

The public interface is:

```bash
make source-analysis STORY=time-expedition STAGE=prepare
make source-analysis STORY=time-expedition STAGE=develop
make source-analysis STORY=time-expedition STAGE=validate
```

`prepare` is the only stage allowed to parse retained source Markdown. It
locks the corpus and writes three physically separate, hash-bound indexes:

- `build/time-expedition/source-study/indexes/development.jsonl` for Tier 1-3 development material;
- `build/time-expedition/source-study/indexes/heldout-wells.jsonl` for held-out Wells material;
- `build/time-expedition/source-study/indexes/tier4-controls.jsonl` for Tier 4 comparative controls.

The real partition contains twelve retained sources and fifteen analytical
witnesses. *The Star* is held out in full; the other Tier 1-3 witnesses use
deterministic within-work holdouts, while all Tier 4 material remains outside
the development index. Re-running `prepare` reproduces the tracked manifest
and generated indexes byte for byte.

`develop` can read only the development index. Validation follows the strict
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
reviewed final forms, but each is read from trusted Git content and checked
against its separately recorded final SHA-256 before use. Generated validation
outputs publish through the managed `validation/current` generation pointer.

This workflow remains descriptive and source-bound. It does not author style
guidance, alter a style card, plan the Permian material, or change manuscript
prose. Phase 2C is an explicit stop boundary requiring separate design
approval and human approval of Phase 2B.

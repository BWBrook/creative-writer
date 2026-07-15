# Task 6 remediation contract

This contract supersedes any Task 6 behavior that relies on a mixed passage
index, boolean control access, sequential multi-file publication, or
post-read filtering as quarantine.

## Physical partitions

`AnalysisConfig` moves to schema version 2. Its generated paths replace the
mixed `passage_index` with:

- `development_passage_index` -> `indexes/development.jsonl`
- `heldout_wells_passage_index` -> `indexes/heldout-wells.jsonl`
- `tier4_control_passage_index` -> `indexes/tier4-controls.jsonl`

Validation paths resolve through one managed pointer:

- `validation/current/validation-metrics.json`
- `validation/current/validation-packet.md`
- `validation/current/analysis-report.md`

`HoldoutManifest` moves to schema version 2 and binds the corpus lock plus
each partition index by repository-relative path, exact SHA-256, partition
name, passage count, and ordered unique witness IDs.

`prepare` is the only stage permitted to parse retained source Markdown. It
must prove that the three passage-ID sets are pairwise disjoint, their union
equals the retained corpus, development and held-out contain only Tier 1-3,
and controls contain every and only Tier 4 passage. It serializes each index
canonically and records hashes over the exact bytes.

Post-prepare access is strict:

- `develop` reads only the development index;
- `validate/frozen` reads only held-out Wells;
- `validate/heldout_assessed` reads held-out Wells, validates complete
  treatment, then may read controls;
- `validate/complete` follows the same ordered boundary;
- no post-prepare stage reparses retained source Markdown.

Schema-v1 mixed indexes fail closed in `develop` and `validate`. Because the
real manifest does not yet exist, no real migration or prepare run occurs in
this task.

## Canonical partition bytes

Partition records are sorted by `(witness_ordinal, source_ordinal)` and use
compact, sorted-key UTF-8 JSON with one LF per record, no blank lines, and no
BOM. Parsed records must have strictly increasing global ordinals, valid
content hashes and passage IDs, exact partition tiers, and identities matching
the manifest binding.

## Capability boundary

Create `source_validation.py` with sealed frozen capability objects:

```python
verify_candidate_freeze(...) -> VerifiedFreeze
open_heldout_wells(VerifiedFreeze) -> HeldoutCorpus
authorize_control_access(VerifiedFreeze, HeldoutCorpus) -> VerifiedControlAccess
open_tier4_controls(VerifiedControlAccess) -> ControlCorpus
```

`VerifiedFreeze` contains no control path or binding. A frozen caller cannot
open controls with its capability. `VerifiedControlAccess` is minted only
after validation step and complete held-out treatment pass.

Filesystem reads belong to the capability-owning module. Passage helpers
provide only pure byte serialization and parsing.

## Git trust order

All Git subprocesses are argument arrays with no shell and set:

- `GIT_NO_REPLACE_OBJECTS=1`
- `GIT_TERMINAL_PROMPT=0`
- `GIT_PAGER=cat`
- `GIT_CONFIG_NOSYSTEM=1`
- empty `GIT_EXTERNAL_DIFF`

Require tracked, clean, stage-0 regular blobs. Resolve an exact full lowercase
commit for the repository object format, require it to be an ancestor and not
`HEAD`, inspect modes with `ls-tree -z`, and read candidate bytes by object ID
with `cat-file blob`.

Recorded candidate hashes are checked before any current profile or ledger
body is read. Candidate-frozen equality uses clean paths and equality of
`HEAD` and candidate blob IDs. Final files are read from verified `HEAD` blobs,
not untrusted worktree bodies.

## Exact targets and treatment

Validation expectations use explicit target records:

```text
target id + witness id + role
```

Each expectation has nonempty held-out targets and control targets. Held-out
results and control comparisons name exactly one expectation target. For every
non-rejected claim:

- result target IDs equal expected held-out target IDs exactly;
- comparison target IDs equal expected control target IDs exactly;
- claim, witness, role, tier, partition, and cited passage all match the
  retained registry and target;
- no result satisfies two targets;
- controls remain Tier 4 and comparative only.

Every reviewer record links the complete held-out and control result sets for
its claim. Links must exist, remain within the claim, be nonempty, and contain
no partial or extra evidence. Duplicate `(claim_id, reviewer_id)` records are
forbidden. Transition links equal the complete result/reviewer registries for
that claim. Pre-rejected claims remain rejected and receive no validation
evidence.

## Atomic publication

Publish through:

```text
validation/
  generations/<content-set-sha256>/
    validation-metrics.json
    validation-packet.md
    analysis-report.md
    manifest.json
  current -> generations/<content-set-sha256>
```

Under an exclusive lock, render all payloads in memory, write and fsync a
same-filesystem staging directory, write a canonical file hash/size manifest,
derive the generation ID, rename staging to the immutable generation, then
atomically replace one relative `current` symlink and fsync its parent.

Before the pointer swap, readers see the old complete generation or no first
generation. After it, readers see the complete new generation. Failed runs
remove their staging path and leave `current` unchanged. Identical reruns reuse
the verified generation. Complete generations are retained.

## Module boundary

- `source_analysis.py`: prepare, partition selection, develop, public dispatch
- `source_validation.py`: Git preflight, capabilities, matching, final checks,
  rendering
- `source_analysis_common.py`: hashes, safe paths, canonical serialization,
  publication transaction; imports neither orchestrator
- `source_passages.py`: pure passage parse/serialize functions
- `source_analysis_models.py`: strict schemas only
- `source_metrics.py`: deterministic metrics only

## Required negative tests

- partition disjointness, union, tiers, deterministic bytes, bindings
- partition tamper/truncate/reorder/swap/duplicate/append
- mixed v1 rejection
- forged/wrong capability and premature control authorization
- malformed/short/uppercase/noncommit/equal/unreachable/descendant commit
- missing/symlink/gitlink/dirty/staged/drifted candidate files
- active replacement refs and malicious filters/textconv
- hash mismatch before index or body reads
- unreadable control index/source during frozen validation
- unreadable held-out/control index/source during develop
- no Tier 4 key, ID, text, path, hash, or metric in frozen generation
- expectation target missing/extra/duplicate/wrong witness/role/tier/partition
- dangling/cross-claim/partial/extra reviewer and transition links
- publication failure at every staging/rename/pointer boundary
- concurrent readers observe only old or new triples
- deterministic rerun and stale-staging cleanup

The real protocol-only `analysis.yml` may receive schema-v2 path declarations,
but this task must not run real `prepare`, create real `holdouts.yml`, or open
or interpret Wells holdout/control prose.

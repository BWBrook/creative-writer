# Forensic Source Study Method

## Target

Reconstruct H. G. Wells's fictional practice circa 1897-1899 for a recovered-manuscript anthology, without reducing it to generic Victorian prose.

## Authority

The five-tier hierarchy in the approved design governs every claim. *The Time Machine* alone supplies continuity and primary voice authority. Period controls are negative evidence only.

## Admission rule

Only records marked `admitted` may be analysed. Admission is complete and the
corpus is closed at twelve retained, admitted records plus one excluded,
unacquired Tier 5 record. No records remain `approved` or `proposed`, and the
excluded record has no source artifact or positive authority.

## Phase 2B lifecycle

This section records the method as it was run. The command-line interface it
describes was retired after the study closed; see `README.md` in this
directory. The interface was:

```bash
creative-writer source-analysis --story time-expedition --stage prepare
creative-writer source-analysis --story time-expedition --stage develop
creative-writer source-analysis --story time-expedition --stage validate
```

Preparation freezes the admitted corpus and writes three canonical physical
indexes: a Tier 1-3 development index, a held-out Wells index, and a Tier 4
control index. Their passage IDs, ordered records, partition membership, and
SHA-256 bindings are checked as separate artifacts. No later stage reparses
retained source Markdown.

The real-corpus preparation is complete and its tracked partition manifest is
locked. It covers twelve retained sources and fifteen analytical witnesses,
with *The Star* reserved as a whole-work holdout. The remaining Tier 1-3
witnesses have deterministic within-work development and holdout windows; all
Tier 4 passages are isolated in the control index. A second preparation run
reproduced the manifest, corpus lock, and all three indexes byte for byte.
Observation, interpretation, claim development, candidate freeze, and
validation are now complete.

Development reads only the development index and keeps measurements and
observations per witness. The candidate freeze then records a reachable Git
commit plus exact hashes for `analysis.yml`, `holdouts.yml`, the candidate
profile, and the candidate evidence ledger. The candidate `analysis.yml` and
holdout manifest are immutable authorities; validation cannot replace them or
their bound indexes under the same candidate.

Validation is a two-pass quarantine boundary. The validation record must move
from `frozen` to `heldout_assessed` to `complete`:

1. `frozen` opens and assesses held-out Wells passages only.
2. `heldout_assessed` is committed only after the held-out treatment is complete;
   it contains no control comparisons, reviewer records, or claim transitions.
   Its validation run authorises the separate Tier 4 pass and generates the
   control-inclusive metrics and packet for human assessment.
3. `complete` is committed after those generated controls are assessed. It
   requires exact control comparisons, reviewer treatment, claim transitions,
   final claim outcomes, and the final compiled report.

The candidate profile and ledger remain available from their immutable Git
objects throughout validation. At `complete`, the writer-facing
`wells-profile.md` and `evidence-ledger.yml` may be reviewed final versions;
they are read from trusted Git blobs and checked against separately recorded
final SHA-256 values before parsing. The profile is also semantically validated
against the final ledger and analysis contract. The generated validation triple
is published atomically through `validation/current`.

## Phase 2B outcome

The frozen candidate contained ten descriptive claims. Twenty-one held-out
targets supported their expected tendency and four qualified its scope; none
disconfirmed it. Nine Tier 4 comparisons found a broad shared occurrence,
while the Haggard journey ending supplied one local non-match. Independent
delegated reading supplied the held-out and most control assessments. Root
synthesis produced six validated and four qualified final claims, no rejections,
and no strong-confidence result. A separate independent acceptance audit
requested completion-gate repairs and approved the repaired evidence layer on
re-review.

These outcomes describe the admitted corpus only. Role and work often remain
aliased, control coverage is one declared target per claim, and the held-out
*Time Machine* ending window does not include its terminal frame. The final
report therefore makes no authorship attribution, pooled inferential test, or
period-wide claim.

## Phase 2C stop

Phase 2B remains descriptive. It does not produce style guidance, style-card
changes, phrase banks, Permian research or planning, operational instructions,
or manuscript prose. The complete validation report is the explicit Phase 2C
stop boundary. Barry approved the Phase 2B evidence layer on 23 July 2026;
Phase 2C still requires its own design approval.

# Wells Phase 2B Analysis Plan

## Protocol state

Status: **protocol**. This story-local contract adopts the approved Phase 2B
design for the closed Phase 2A corpus. No measurements, observations, claims,
or validation outcomes have been adopted at this stage.

## Corpus and authority

The admission registry and retained-source registry are immutable inputs and
are fingerprinted in `analysis.yml`. *The Time Machine* is the sole Tier 1
continuity authority. Tier 2 and Tier 3 sources are used only within their
declared analytical roles. Tier 4 sources are quarantined negative controls;
Tier 5 material remains excluded.

The four selected short stories are independent witnesses with witness IDs of
`selected-short-fiction/<selection-id>`. No source-level results are replaced
by a pooled Wells target.

## Execution sequence

1. Run source admission and verify the declared registry fingerprints.
2. Parse retained Markdown witnesses through the Pandoc JSON AST without
   rewriting them.
3. Record stable passage IDs and create the deterministic holdout manifest.
4. Generate transparent per-witness development measurements using only the
   declared measurements and lexicons.
5. Record human-authored observations and descriptive candidate claims with
   passage locators, authority jurisdiction, variation, and limitations.
6. Freeze the candidate profile and evidence ledger before opening holdouts or
   Tier 4 controls.
7. Validate against held-out Wells material, period controls, and independent
   review, retaining qualified and rejected claims in the historical ledger.

## Partition and evidence rules

Within-work windows contain at most five substantive blocks and do not cross
heading boundaries. The holdout fraction is `0.2`; selection uses the declared
seed, algorithm version, hash ranking, and whole-work holdout in `analysis.yml`.

Evidence references use passage IDs as canonical locators. A development claim
cannot cite a held-out passage or a Tier 4 passage. Tier 4 references use only
the `control` evidence role, and validation references are opened only after
the candidate freeze. Every non-rejected claim records scope, limitations, and
counterexample treatment.

## Boundary

This protocol is descriptive. It does not edit style guidance, generate prose
instructions, create a phrase bank, score authenticity, or alter manuscript
planning or prose.

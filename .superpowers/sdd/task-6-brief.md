### Task 6: Implement Candidate Freeze and Staged Validation

## Governing methodological amendment

This amendment supersedes conflicting one-pass wording below.

- Validation uses two passes while `analysis.yml` remains
  `candidate_frozen`:
  - `validation_step: frozen` opens held-out Wells only;
  - after tracked held-out assessments are recorded,
    `validation_step: heldout_assessed` may open Tier 4 controls.
- `validation_step: complete` is required with `study_status: validated` for
  the final compiled report.
- The frozen candidate ledger remains a `development` ledger. Validation
  verifies its exact bytes from the recorded Git commit and forbids current
  profile/ledger drift; it does not relabel or mutate candidate evidence.
- Preflight verifies the candidate commit and hashes before reading the passage
  index, holdout manifest, source text, or control material.
- Candidate Git verification requires a full lowercase commit object that is
  reachable from and older than `HEAD`; the frozen files must be regular Git
  blobs, tracked, and clean. Read them with non-interactive, no-filter Git
  commands and hash their exact bytes.
- `validation.md` uses structured expectations, held-out claim results,
  control comparisons, reviewer records, and explicit claim transitions.
- Final validation requires exact candidate claim-ID preservation, permitted
  transitions, complete held-out/control/reviewer treatment for every original
  non-rejected claim, retained rejected claims, and current final profile and
  ledger SHA-256 values. No final claim may remain `candidate`.
- Generated validation metrics keep `heldout_wells` and `tier4_controls`
  separate by witness. The first pass must contain no Tier 4 IDs, text,
  metrics, or keys.
- No aggregate authenticity score, authorship probability, significance test,
  or automatic status/confidence promotion is permitted.
- Candidate and validation runs never mutate tracked evidence files. Generated
  outputs are staged and committed atomically.

**Files:**
- Modify: `src/creative_writer/source_analysis.py`
- Modify: `src/creative_writer/source_analysis_models.py`
- Modify: `src/creative_writer/source_metrics.py`
- Modify: `tests/test_source_analysis.py`

**Interfaces:**
- `validate` refuses to open holdouts or controls unless `analysis.yml` has `study_status: candidate_frozen` or `validated` and `validation.md` records a reachable candidate Git commit plus exact SHA-256 hashes for the candidate `wells-profile.md` and `evidence-ledger.yml` at that commit.
- At `candidate_frozen`, `validate` verifies the freeze, measures held-out Wells and Tier 4 witnesses separately, and writes `validation-metrics.json`, `validation-packet.md`, and a provisional `analysis-report.md`; it does not promote claims automatically.
- At `validated`, `validate` additionally requires permitted final claim transitions, control and reviewer treatment for every non-rejected candidate claim, a current final profile hash, and complete tracked `period-controls.md`/`validation.md`; it then writes the final compiled report.
- Validation packets include witness/tier/role labels and context windows. Control evidence is clearly quarantined as negative/comparative material; no aggregate authenticity score is present.

- [ ] Add RED tests for missing/unreachable commit, changed profile/ledger hash, candidate files absent from the recorded commit, premature holdout/control output, missing claim expectation, illegal claim deletion, invalid status/confidence transition, unaddressed control comparison, missing reviewer result, and stale final profile hash.
- [ ] Add passing tests for candidate freeze, held-out/control packet generation, `validated`/`qualified`/`rejected` outcomes, retained rejected claims, and final compiled report.
- [ ] Run `uv run pytest tests/test_source_analysis.py -k 'freeze or validate or transition or compiled' -q` and confirm RED.
- [ ] Implement Git-object reads with non-interactive `git show <commit>:<path>` and SHA-256 verification; never mutate candidate evidence during validation.
- [ ] Generate separate source-wise effect summaries and limitations without significance tests or a composite score.
- [ ] Run focused tests and all source-analysis tests GREEN.
- [ ] Commit the freeze/validation implementation.

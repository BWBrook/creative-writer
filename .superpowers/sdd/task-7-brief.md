### Task 7: Wire the Public Interface and Synthetic End-to-End Test

**Files:**
- Modify: `src/creative_writer/cli.py`
- Modify: `Makefile`
- Modify: `README.md`
- Modify: `tests/test_source_analysis.py`
- Modify: `stories/time-expedition/source-study/README.md`
- Modify: `stories/time-expedition/source-study/method.md`

**Interfaces:**
- CLI: `creative-writer source-analysis --story <slug> --stage prepare|develop|validate`.
- Make: `make source-analysis STORY=<slug> STAGE=<prepare|develop|validate>`.
- CLI returns `0` only when the requested stage completes without blocking issues; errors use the existing `CreativeWriterError` path and non-zero exit.

- [ ] Add RED parser and command tests for all three stages, invalid stage handling, output-path messages, and non-zero blocking failures.
- [ ] Add a synthetic Git-backed mini-corpus scenario that runs `prepare`, commits holdouts, runs `develop`, commits/fingerprints a candidate, runs held-out-only frozen validation, commits complete held-out assessments, runs the control-authorising `heldout_assessed` pass, records final outcomes, and runs complete validation.
- [ ] Confirm RED before wiring the parser/Make target.
- [ ] Implement CLI/Make integration and concise command documentation, including the three physical passage indexes, candidate-freeze sequence, two-pass validation boundary, immutable candidate `analysis.yml`/`holdouts.yml`, separately hash-checked final profile/ledger, and explicit Phase 2C stop boundary.
- [ ] Run `uv run pytest tests/test_source_analysis.py -q`, `uv run creative-writer source-analysis --help`, and `make -n source-analysis STORY=time-expedition STAGE=prepare` GREEN.
- [ ] Run `uv run pytest -q` for repository regression coverage.
- [ ] Commit the complete tooling interface.

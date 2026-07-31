# Authenticity Reviews

This directory stores tracked judgements made after a Wells style-lint run.
Completed reviews preserve editorial reasoning; they do not certify authorship,
change the profile automatically, or replace direct reading of the manuscript
and cited source packets.

## Validation and gates

- Any review present here is validated by `make check STORY=time-expedition`.
- An absent chapter, story, or anthology milestone review does not block a
  build.
- An AI reviewer may close a chapter review as `accepted`, `qualified`, or
  `revise` when the rationale is recorded.
- Story and anthology acceptance requires a human reviewer. AI may prepare or
  qualify those reviews but cannot record an accepted milestone.

## Workflow

1. Run `make style-lint STORY=time-expedition` or a chapter-targeted run.
2. Inspect every finding in manuscript context and against the active reference
   packets.
3. Assign `dismiss`, `revise`, `monitor`, or `escalate` during AI triage.
4. Escalate only ambiguous, consequential cases; a human calibration pack
   normally contains three to five passages and one precise question per case.
5. Copy `_template.md` to a descriptive slug, replace every placeholder, record
   the JSON lint report's SHA-256, and complete every body section.

Generated reports under `build/` are disposable and may be absent later. The
tracked review therefore retains the stable report path and its fingerprint.
Proposed profile changes belong in the review record first, then require an
explicit versioned profile edit supported by review evidence.

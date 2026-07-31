# Wells Style Reference Packets

These manifests select small, role-matched comparison sets from the approved
Phase 2B evidence catalog. They are drafting and review aids, not phrase banks,
imitation prompts, training data, or independent style authorities.

## Authority and use

- Tier 1, *The Time Machine*, controls story-world continuity and primary voice
  evidence.
- Tier 2 Wells sources provide bounded comparison only in their admitted
  analytical roles.
- Tier 3 nonfiction provides bounded explanatory or period-language comparison,
  never fictional continuity or direct narrative-voice prescription.
- Tier 4 controls appear only under `Negative comparisons`. They test whether a
  feature is shared or locally contrasting and never supply positive Wells
  guidance.
- Every claim remains subject to the status, jurisdiction, scope, limits, and
  prohibited overgeneralisation in `source-study/evidence-ledger.yml`.

The `traveller-account` packet deliberately has no Tier 4 control. It compares
role-shaped distance and local syntax within admitted Wells evidence; adding a
neighbouring author would answer a different question.

## Compile a packet

```bash
make style-reference STORY=time-expedition PACK=frame-and-testimony
make style-reference STORY=time-expedition PACK=traveller-account
make style-reference STORY=time-expedition PACK=observation-and-exposition
make style-reference STORY=time-expedition PACK=dialogue-and-social-friction
make style-reference STORY=time-expedition PACK=danger-and-action
make style-reference STORY=time-expedition PACK=reflection-and-closure
```

Generated packets land under
`build/time-expedition/style/reference-packets/`. Read the claim limits and
selection rationale before each excerpt, compare narrative function across the
set, and follow the anti-copying instruction in every manifest.

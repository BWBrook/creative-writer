---
schema_version: 1
study_id: time-expedition-wells-phase-2b
stage: candidate_frozen
validation_step: heldout_assessed
candidate_commit: a8f658d5b107cbd90e8e2e59b37e21e7042b3ca1
candidate_analysis_sha256: a1b6c8a50e1527b587fa3861413cc78d87f02f9d2773768859ac629ba5258a6f
candidate_manifest_sha256: 7ff1aaa6c96209ce8a22511840018d6e21580658d1421d4a8e76baef21690d67
candidate_profile_sha256: a78c766eaeac350c32f25ab30ff76d089981dee733a6a44e47dd610ea2ab3caf
candidate_ledger_sha256: 7c5e5022ab295a1178b06876398b955afda74ecdceafb63144c55bda4d8b48c7
holdout_summary: All 25 predeclared held-out Wells targets have been assessed; 21 support the candidate tendency and 4 qualify its scope, with none disconfirming it.
control_summary: Tier 4 controls remain quarantined until this complete held-out assessment is committed and a subsequent validation pass authorises access.
reviewer_summary: Development evidence and the candidate profile received independent tier-specific and cross-work review before freeze; held-out assessments are complete and final validation review remains pending.
heldout_claim_results:
  - id: heldout-tm-frame
    claim_id: mediated-testimony-frame
    expectation_target_id: tm-frame
    witness_id: the-time-machine
    role: frame architecture
    passage_ids:
      - the-time-machine:ii:79:3f712a420f66
      - the-time-machine:xii:279:e22b90a63db0
      - the-time-machine:xii:281:79b2dfd62435
    assessment: supports
    observed_tendency: The frame makes belief an explicit social and evidentiary problem, embeds the extraordinary account in a present act of telling, and leaves its status open as lie, prophecy, dream, fiction, or truth.
    notes: Mediation changes across the held-out witness from the frame narrator's recollection of collective scepticism to the Traveller's direct address and invitation to judge his story. The passages strongly show coexisting credibility claims and uncertainty, but they do not establish how consistently that mechanism operates outside the sampled frame passages.
  - id: heldout-star-testimony
    claim_id: mediated-testimony-frame
    expectation_target_id: star-testimony
    witness_id: selected-short-fiction/the-star
    role: testimony
    passage_ids:
      - selected-short-fiction/the-star:the-star:1:87d94783269e
      - selected-short-fiction/the-star:the-star:3:1fc2aa605250
      - selected-short-fiction/the-star:the-star:27:4c0c9024ccfe
    assessment: supports
    observed_tendency: The extraordinary event reaches the public through observatory announcements, attributed scientific opinion, newspapers, and contested interpretation, with provisional observations and sceptical alternatives remaining visible.
    notes: This is distributed institutional and public reporting rather than a personal testimony frame. That role-specific variation still fits the frozen alternatives of visible testimony or evidentiary assessment, while the progression from suspicion and probability to dismissal and later confirmation keeps uncertainty and credibility in view.
  - id: heldout-tm-reported
    claim_id: role-shaped-narrator-distance
    expectation_target_id: tm-reported
    witness_id: the-time-machine
    role: reported first-person account
    passage_ids:
      - the-time-machine:xii:276:23b26487ff8e
      - the-time-machine:xii:279:e22b90a63db0
      - the-time-machine:xii:281:79b2dfd62435
    assessment: supports
    observed_tendency: The Traveller repeatedly marks the present telling from within the remembered journey, then steps back from asserted experience to offer competing present-tense accounts of what his narrative might be.
    notes: >-
      The distance is overtly performative and audience-facing: recollection is
      organised by what has already been told, the return converges on "now I am
      telling you," and the truth claim is reopened for judgement. These passages
      support the reported-account contrast, though they sample the return and
      frame rather than the full range of immersive narration.
  - id: heldout-moreau-retrospective
    claim_id: role-shaped-narrator-distance
    expectation_target_id: moreau-retrospective
    witness_id: the-island-of-doctor-moreau
    role: retrospective first-person narration
    passage_ids:
      - the-island-of-doctor-moreau:iv:89:c6d8e37d14d3
      - the-island-of-doctor-moreau:v:116:4ff1d7cf8db3
    assessment: supports
    observed_tendency: The later narrator addresses the reader and corrects or limits the experiencing self's knowledge with explicit hindsight markers such as not knowing or not seeing something then.
    notes: Documentary distance is clearest where present narration distinguishes later knowledge from the original perception. Much surrounding narration remains scene-immersive, so the held-out evidence shows a recurrent retrospective layer rather than continuous detachment.
  - id: heldout-matters-essay
    claim_id: role-shaped-narrator-distance
    expectation_target_id: matters-essay
    witness_id: certain-personal-matters
    role: essay voice
    passage_ids:
      - certain-personal-matters:through-a-microscope:343:6b1078e0ddf2
      - certain-personal-matters:through-a-microscope:344:ca27427f4173
    assessment: supports
    observed_tendency: The essay persona reports his own discomfort and imaginative response while comic comparisons recast him as a public moralist, a voyeur, and the victim of his own "abominable imagination."
    notes: Self-account and self-mockery are layered within the same speaking persona rather than separated by documentary hindsight. The evidence is decisive for this bounded essay-voice contrast, without implying that every held-out essay passage uses the same comic distance.
  - id: heldout-tm-ending
    claim_id: short-form-evidentiary-closure
    expectation_target_id: tm-ending
    witness_id: the-time-machine
    role: frame architecture
    passage_ids:
      - the-time-machine:xii:279:e22b90a63db0
      - the-time-machine:xii:281:79b2dfd62435
      - the-time-machine:xii:282:6802974ee5e9
    assessment: qualifies
    observed_tendency: The Traveller closes the narrated journey by returning to the room and declaring the present telling, after which the frame shifts to competing truth statuses and an audience whose judgement remains unresolved.
    notes: The held-out segment supports local evidentiary closure of the testimony and unresolved credibility and implications. It does not include the work's terminal frame, so it cannot by itself establish that the complete ending preserves the same closure relation.
  - id: heldout-star-ending
    claim_id: short-form-evidentiary-closure
    expectation_target_id: star-ending
    witness_id: selected-short-fiction/the-star
    role: short-form architecture
    passage_ids:
      - selected-short-fiction/the-star:the-star:39:de14ba922638
      - selected-short-fiction/the-star:the-star:40:22207290428c
    assessment: supports
    observed_tendency: The story explicitly restricts its record to the star's coming and passing, leaves human reconstruction and migration untold, and closes by replacing the human account with a radically distant Martian assessment.
    notes: The immediate astronomical event is resolved, but the social aftermath is excluded from the record and the final change of scale exposes unresolved interpretive significance. This is strong support for ended evidence with larger implications left open, through a different mechanism from the framed testimony.
  - id: heldout-tm-speculation
    claim_id: qualified-speculative-inference
    expectation_target_id: tm-speculation
    witness_id: the-time-machine
    role: speculative method
    passage_ids:
      - the-time-machine:x:249:b3fbc6d18ae6
      - the-time-machine:x:252:9a6f001f723c
    assessment: supports
    observed_tendency: >-
      Earlier conclusions are explicitly revised after further observation, and the
      replacement explanation is presented as the narrator's current construction
      and allowed to be wholly wrong.
    notes: >-
      This is a strong instance of revisable inference, but it is one retrospective
      sequence within the witness and does not show that all of its speculative
      explanations are similarly qualified.
  - id: heldout-war-inference
    claim_id: qualified-speculative-inference
    expectation_target_id: war-inference
    witness_id: the-war-of-the-worlds
    role: evidence-to-speculation movement
    passage_ids:
      - the-war-of-the-worlds:x:901:6e2377df9693
      - the-war-of-the-worlds:x:902:27228a904e12
    assessment: supports
    observed_tendency: >-
      Post-war examinations and spectrum analysis are linked to explanations, but
      the narrator distinguishes probability and possibility from proof and marks
      several questions as unresolved.
    notes: >-
      The passages strongly match the declared tendency. They occur together in one
      epilogue sequence, so they are not independent replications within the witness.
  - id: heldout-tm-exposition
    claim_id: qualified-scientific-exposition
    expectation_target_id: tm-exposition
    witness_id: the-time-machine
    role: speculative method
    passage_ids:
      - the-time-machine:iii:107:38612a49f372
      - the-time-machine:v:176:f2eb71491f26
    assessment: supports
    observed_tendency: >-
      Unfamiliar physical claims are made intelligible through molecular and vapour
      analogy and through alternative astronomical explanations, with possibility,
      uncertainty, and an explicit inability to account for the observation retained.
    notes: >-
      The two passages use different local qualifications, but both belong to one
      witness and mix fictional physical premises with explanation; they establish a
      held-out tendency, not scientific validity or frequency.
  - id: heldout-moreau-argument
    claim_id: qualified-scientific-exposition
    expectation_target_id: moreau-argument
    witness_id: the-island-of-doctor-moreau
    role: scientific argument
    passage_ids:
      - the-island-of-doctor-moreau:xiv:389:f8f2e4347536
    assessment: qualifies
    observed_tendency: >-
      Moreau links the unfamiliar result to known surgical procedures and secondary
      changes, but his qualification mainly bounds earlier work as small efforts;
      the argument otherwise uses confident assertions rather than sustained
      epistemic uncertainty.
    notes: >-
      The observable procedural link recurs, while the expected local qualification
      is weaker and different in kind from the development passage. One decisive
      held-out passage was available for the argument itself.
  - id: heldout-biology-instruction
    claim_id: qualified-scientific-exposition
    expectation_target_id: biology-instruction
    witness_id: text-book-of-biology-part-1
    role: instructional exposition
    passage_ids:
      - text-book-of-biology-part-1:preface:20:4cfb986f88ee
      - text-book-of-biology-part-1:2-the-alimentary-canal-of-the-rabbit:47:76042bf2613e
    assessment: supports
    observed_tendency: >-
      Instruction is tied to experienced procedure, diagrams, and anatomical
      relations while retaining bounded recommendations and explicit uncertainty
      about the inferred action of the caecum.
    notes: >-
      The passages vary between pedagogical procedure and anatomical exposition.
      Their qualifications are local and do not imply that the textbook is generally
      tentative.
  - id: heldout-biology-comparison
    claim_id: qualified-scientific-exposition
    expectation_target_id: biology-comparison
    witness_id: text-book-of-biology-part-1
    role: comparison and classification
    passage_ids:
      - text-book-of-biology-part-1:note-on-making-comparisons:523:529d1ed729fd
    assessment: supports
    observed_tendency: >-
      Comparison is presented as an explicit method based on corresponding positions
      and homologous parts, while the recommendation is qualified as a preference
      and made conditional on what the student can do.
    notes: >-
      This directly supports the declared comparison role, but it is a methodological
      instruction rather than an independently replicated biological explanation.
  - id: heldout-invisible-dialogue
    claim_id: dialogue-pressure-varies-by-context
    expectation_target_id: invisible-dialogue
    witness_id: the-invisible-man
    role: sustained dialogue
    passage_ids:
      - the-invisible-man:vii:223:04a2271ebbf5
      - the-invisible-man:vii:224:d522bd5a3676
      - the-invisible-man:xii:394:2055cda3c024
    assessment: supports
    observed_tendency: >-
      The held-out witness contains markedly different local organisations under
      sustained social pressure: a long, repetitive demand is cut off by one
      violent command, while another exchange is rendered through whispers,
      pauses, movement, and renewed silence.
    notes: >-
      This is bounded within-witness variation, not evidence that pressure causes
      the organisation. The transcription-sensitive paragraph boundaries and the
      selection of two scenes limit any inference about a stable dialogue rhythm.

  - id: heldout-moreau-stress
    claim_id: dialogue-pressure-varies-by-context
    expectation_target_id: moreau-stress
    witness_id: the-island-of-doctor-moreau
    role: dialogue under stress
    passage_ids:
      - the-island-of-doctor-moreau:v:115:8ddf9cdc824d
      - the-island-of-doctor-moreau:xiii:358:8b0cee88645a
      - the-island-of-doctor-moreau:xiii:379:cd9125e6d0fc
    assessment: supports
    observed_tendency: >-
      Stress dialogue varies between a narratively compressed three-cornered
      altercation with a repeated refrain, silent gesture, and broken threat, and
      a confrontation bounded by Moreau's short demand for a hearing and a
      contemptuous close followed by silence.
    notes: >-
      These passages contribute a contrast to the held-out Invisible Man target,
      but they also show variation within Moreau. Scene, speaker, work, and role
      remain aliased, so the passages do not identify pressure as the cause.

  - id: heldout-tm-rhythm
    claim_id: role-shaped-syntax
    expectation_target_id: tm-rhythm
    witness_id: the-time-machine
    role: reported first-person account
    passage_ids:
      - the-time-machine:iii:107:38612a49f372
      - the-time-machine:iii:112:141c8f14a27a
    assessment: supports
    observed_tendency: >-
      The reported account moves from extended causal reconstruction, using
      semicolons, qualifications, and dashes, into shorter sequential crisis
      clauses as perception and action accelerate.
    notes: >-
      The two passages show local modulation within one reported account rather
      than a fixed rhythm. They support comparison with the other declared
      targets but cannot separate role from event type, narrator, or work.

  - id: heldout-invisible-rhythm
    claim_id: role-shaped-syntax
    expectation_target_id: invisible-rhythm
    witness_id: the-invisible-man
    role: sustained dialogue
    passage_ids:
      - the-invisible-man:vii:223:04a2271ebbf5
      - the-invisible-man:vii:224:d522bd5a3676
    assessment: supports
    observed_tendency: >-
      A long turn accumulates coordinated demands and repeated "I want to know"
      constructions before ending unfinished; the answering beat contracts to
      gesture and a single imperative that stops the speaker.
    notes: >-
      This supplies a clear local turn-and-interruption rhythm, but one exchange
      cannot define sustained dialogue generally. Paragraph interpretation is
      additionally limited by the witness's transcription sensitivity.

  - id: heldout-matters-rhythm
    claim_id: role-shaped-syntax
    expectation_target_id: matters-rhythm
    witness_id: certain-personal-matters
    role: essay voice
    passage_ids:
      - certain-personal-matters:of-conversation:52:1173fcf494ca
      - certain-personal-matters:of-conversation:53:7afb7b6a133d
    assessment: supports
    observed_tendency: >-
      The essay voice develops through self-qualification, direct assertion,
      cumulative analogy, lists, and a rhetorical question, with occasional
      short declaratives punctuating much longer explanatory sequences.
    notes: >-
      This movement is locally distinguishable from the selected reported account
      and dialogue targets, while still varying within the essay passage pair.
      Work and role are confounded, so no role effect is identified.

  - id: heldout-invisible-comic
    claim_id: humour-through-social-friction
    expectation_target_id: invisible-comic
    witness_id: the-invisible-man
    role: comic friction
    passage_ids:
      - the-invisible-man:ii:65:6c8bf47dcf78
      - the-invisible-man:ii:66:0854f4deef39
      - the-invisible-man:ii:67:836fcde0dc88
    assessment: supports
    observed_tendency: >-
      Comic friction recurs when Henfrey's tentative conversational overture is
      framed as an aimed shot, meets disproportionate suppressed rage, and ends
      in a deferential, unfinished retreat.
    notes: >-
      The humour depends on both the social mismatch and narratorial framing;
      these passages do not show that mismatch is the witness's dominant or only
      comic mechanism.

  - id: heldout-matters-humour
    claim_id: humour-through-social-friction
    expectation_target_id: matters-humour
    witness_id: certain-personal-matters
    role: humour
    passage_ids:
      - certain-personal-matters:the-veteran-cricketer:159:d66bde07fa09
    assessment: supports
    observed_tendency: >-
      The humour turns on a declared failure of mutual understanding: the vicar's
      condescending small talk violates the cricketer's sense of the game's
      seriousness, prompting pointed instruction and the field's sniggering.
    notes: >-
      Narratorial irony and analogy help make the mismatch comic, so social
      friction is not an exclusive mechanism. One held-out passage establishes
      recurrence, not prevalence across the essay witness.
  - id: heldout-war-landscape
    claim_id: selective-observed-description
    expectation_target_id: war-landscape
    witness_id: the-war-of-the-worlds
    role: landscape observation
    passage_ids:
      - the-war-of-the-worlds:vi:740:69af08a05e67
      - the-war-of-the-worlds:vi:742:48ba891f34c8
      - the-war-of-the-worlds:vi:743:57359c8954fa
    assessment: supports
    observed_tendency: >-
      The altered landscape is disclosed through a situated act of looking, with
      selected red-weed, ruined-wall, crimson-tree, flood, and meadow details
      organised into recognition of an unfamiliar environment and its cause.
    notes: >-
      The sequence varies from visual description to analogy, foraging, and causal
      exposition, so the support is local to this landscape encounter rather than
      evidence that all description in the witness follows the tendency.
  - id: heldout-matters-microscope
    claim_id: selective-observed-description
    expectation_target_id: matters-microscope
    witness_id: certain-personal-matters
    role: microscopic observation
    passage_ids:
      - certain-personal-matters:through-a-microscope:344:ca27427f4173
      - certain-personal-matters:through-a-microscope:345:d684330c7d30
    assessment: qualifies
    observed_tendency: >-
      Visible colour, shape, motion, transparency, and scale are selected around
      microscope observation and comparison, but repeatedly become premises for
      comic speculation and moral reflection.
    notes: >-
      The local observational organisation is discernible, yet it does not govern
      the passages exclusively: analogy and humour substantially redirect the
      description beyond the specimen-level comparison.
  - id: heldout-biology-terms
    claim_id: selective-observed-description
    expectation_target_id: biology-terms
    witness_id: text-book-of-biology-part-1
    role: biological terminology
    passage_ids:
      - text-book-of-biology-part-1:1-external-form-and-general-considerations:35:8b5d558cda68
      - text-book-of-biology-part-1:5-the-skeleton:113:5dba26ed6548
      - text-book-of-biology-part-1:5-the-skeleton:114:43b533bc86d1
    assessment: supports
    observed_tendency: >-
      Anatomical terms and concrete features are selected to distinguish mammalian
      characters and to compare thoracic, cervical, atlas, and axis vertebral
      categories.
    notes: >-
      The classificatory organisation is explicit in these passages, although
      adjacent instructional material can instead enumerate structures or procedures;
      the assessment is therefore restricted to the cited target evidence.
  - id: heldout-sea-danger
    claim_id: danger-through-observation
    expectation_target_id: sea-danger
    witness_id: selected-short-fiction/the-sea-raiders
    role: biological danger
    passage_ids:
      - selected-short-fiction/the-sea-raiders:i:11:e706bbe4a853
      - selected-short-fiction/the-sea-raiders:i:12:2c6fdfdb7585
      - selected-short-fiction/the-sea-raiders:i:13:df7e94ad65ec
    assessment: qualifies
    observed_tendency: >-
      Fison observes the creatures without recognising personal danger; their
      deliberate approach and unexpectedly rapid pursuit then accumulate before
      his explicit realisation of the threat.
    notes: >-
      The local encounter fits consequence-before-recognition, but the witness's
      retrospective opening has already named the species and linked it to fatalities.
      That advance framing weakens, without eliminating, the claimed delay in a
      complete explanatory account.
  - id: heldout-war-catastrophe
    claim_id: danger-through-observation
    expectation_target_id: war-catastrophe
    witness_id: the-war-of-the-worlds
    role: catastrophe
    passage_ids:
      - the-war-of-the-worlds:xi:243:e7d3b67be077
      - the-war-of-the-worlds:xi:244:0a6dc394b15b
      - the-war-of-the-worlds:xi:245:f121c0539b24
    assessment: supports
    observed_tendency: >-
      The catastrophe is assembled from a widening view of blackened woods, glowing
      ruins, a wrecked train, fires, smoke, and fleeing figures while the narrator
      still lacks a complete account of what happened and how the machines relate
      to the cylinder's occupants.
    notes: >-
      This is slower, retrospective survey rather than immediate pursuit, supporting
      the frozen tendency's stated variation in catastrophe tempo. The inference is
      local to the cited aftermath sequence.
control_comparisons: []
reviewer_records: []
claim_transitions: []
unresolved_uncertainty: Held-out Wells evidence supports or qualifies every candidate tendency, but role-work aliasing, limited replication, and period distinctiveness remain unresolved until the quarantined controls and independent validation review are complete.
final_profile_sha256: null
final_ledger_sha256: null
---

# Validation Record

## Held-out Wells assessment

The candidate profile, evidence ledger, analysis contract, and holdout manifest
remain bound to the recorded candidate Git commit and SHA-256 values. All 25
predeclared held-out Wells targets have now been assessed against that frozen
candidate: 21 support the expected tendency and four qualify its scope. No
target disconfirms the candidate tendency.

This record does not itself authorise control access while dirty. Once committed,
a subsequent validation pass may open the Tier 4 controls. Control comparison,
claim transitions, final classifications, and final profile reconciliation remain
pending.

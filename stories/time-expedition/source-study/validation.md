---
schema_version: 1
study_id: time-expedition-wells-phase-2b
stage: validated
validation_step: complete
candidate_commit: a8f658d5b107cbd90e8e2e59b37e21e7042b3ca1
candidate_analysis_sha256: a1b6c8a50e1527b587fa3861413cc78d87f02f9d2773768859ac629ba5258a6f
candidate_manifest_sha256: 7ff1aaa6c96209ce8a22511840018d6e21580658d1421d4a8e76baef21690d67
candidate_profile_sha256: a78c766eaeac350c32f25ab30ff76d089981dee733a6a44e47dd610ea2ab3caf
candidate_ledger_sha256: 7c5e5022ab295a1178b06876398b955afda74ecdceafb63144c55bda4d8b48c7
holdout_summary: All 25 predeclared held-out Wells targets have been assessed; 21 support the candidate tendency and 4 qualify its scope, with none disconfirming it.
control_summary: All 10 predeclared Tier 4 comparisons are complete; 9 share the bounded tendency and 1 does not, without granting controls positive authority or supporting a period-wide inference.
reviewer_summary: Independent delegated readers supplied all held-out and most control assessments; root completed the two Beetle controls and synthesized 6 validated and 4 qualified claim decisions, and the initial independent whole-study audit requested completion-gate repairs.
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
control_comparisons:
  - id: desert-group-dialogue
    claim_id: dialogue-pressure-varies-by-context
    expectation_target_id: desert-group
    witness_id: a-desert-drama
    role: group dialogue
    passage_ids:
    - a-desert-drama:chapter-i:33:21d52f787067
    - a-desert-drama:chapter-i:34:331b0501e05f
    - a-desert-drama:chapter-i:35:031d52d8dbf3
    comparison: The control scene distributes group conversation across successive contributions from Sadie,
      her aunt, and Stephens, with Stephens's reply also carried by a document handoff and Sadie's laughter.
      This shares the frozen claim's local organisation of group talk through multiple voices and reactions,
      although the selected turns are not uniformly brief.
    result: shared
    notes: This comparison is restricted to the declared group-dialogue role and the three cited passages.
      A single control scene cannot establish that social pressure causes turn length or that the control
      reproduces Wells's full cross-context variation. Shared dialogue distribution may be a role or period
      convention; it is not evidence against historical plausibility, a positive profile of the control
      author, or an authorship claim.
  - id: desert-danger-pacing
    claim_id: danger-through-observation
    expectation_target_id: desert-danger
    witness_id: a-desert-drama
    role: danger pacing
    passage_ids:
    - a-desert-drama:stoppa-backa-cried-the-native-pilot-to-the-european-engineer:217:c5a008af45d1
    - a-desert-drama:stoppa-backa-cried-the-native-pilot-to-the-european-engineer:219:9315b8d586ce
    - a-desert-drama:chapter-iv:227:8c3a290209ac
    comparison: The control first presents approaching camel riders as a picturesque sight, then records
      a collective hush and involuntary physical reactions, and only afterward gives the Colonel's explicit
      recognition that the riders are hostile. This shares the frozen claim's consequence-before-explanatory-closure
      pacing at a local adventure scale.
    result: shared
    notes: The sequence is bounded to one approach scene, and an earlier contextual warning about Dervishes
      makes the danger less wholly unexplained than the initial misrecognition alone suggests. The comparison
      shows that the local pacing can occur under generic adventure pressure; it does not establish a universal
      or period-wide suspense law, diminish historical plausibility, profile the control author positively,
      or support an authorship inference.
  - id: solomon-journey-closure
    claim_id: short-form-evidentiary-closure
    expectation_target_id: solomon-journey
    witness_id: king-solomons-mines
    role: journey architecture
    passage_ids:
    - king-solomons-mines:xx:1521:b6ceb2d61e7f
    - king-solomons-mines:xx:1522:fccb8920e6ba
    - king-solomons-mines:xx:1525:a22ed968478c
    comparison: The control explicitly ends the history, compresses the repetitive return journey, confirms
      the travellers' safe arrival, and closes with the narrator's concrete decision to sail and supervise
      publication. It closes a journey record, but unlike the frozen claim it does not leave the expedition's
      larger invoked implications unresolved; the principal outcomes are settled and the final sentence
      opens a practical next action.
    result: not_shared
    notes: This distinction is local to the cited terminal sequence and depends on treating unresolved event
      implications as different from ordinary continuation after a completed journey. The comparison does
      not prove that generic journey endings cannot preserve epistemic uncertainty, establish period distinctiveness,
      create a positive profile of the control author, or support an authorship claim.
  - id: beetle-mediated-narrators
    claim_id: mediated-testimony-frame
    expectation_target_id: beetle-narrators
    witness_id: the-beetle
    role: multiple narrators
    passage_ids:
    - the-beetle:book-i-the-house-with-the-open-window:54:8440a05cc8de
    - the-beetle:book-iv-in-pursuit:2249:a031a184a704
    - the-beetle:chapter-xlviii:3234:45875e9c723b
    comparison: The control makes mediation overt by labelling Holt's contribution a narration, presenting
      Champnell's conclusion as an extract from a case-book, and finally disclosing that Holt's apparent
      first-person record was compiled from statements made to two other participants. This shares the frozen
      Wells claim's visible chain of testimony, transcription, and evidentiary access, although it distributes
      that chain across a multi-narrator novel.
    result: shared
    notes: The comparison is confined to the declared multiple-narrator role and to explicit documentary
      signals; it does not establish how continuously credibility and uncertainty operate between those
      signals. Shared mediation in this control prevents a claim of corpus-level Wells distinctiveness,
      but does not create a positive profile of Marsh, a period-wide rule, stylistic equivalence, or authorship
      evidence.
  - id: beetle-role-shaped-distance
    claim_id: role-shaped-narrator-distance
    expectation_target_id: beetle-multiple
    witness_id: the-beetle
    role: multiple narrators
    passage_ids:
    - the-beetle:chapter-ix:396:ff76f6bcefc4
    - the-beetle:chapter-xviii:1235:b508bc2e1193
    - the-beetle:chapter-xxiii:1752:eec3779ebde5
    comparison: Three narrators place represented experience at different retrospective distances. Holt
      separates possible fact from imagination and marks the continuing force of memory; Atherton recasts
      his experience as a doubtful sworn statement; and Marjorie corrects her earlier understanding from
      later hindsight. The control therefore shares the broad frozen tendency for narrator-specific relations
      between experience, present judgement, and self-presentation.
    result: shared
    notes: Narrator, book division, episode, and rhetorical purpose are completely confounded, and the control
      does not reproduce the Wells claim's essay-voice comparison. Shared marks only a bounded occurrence
      outside Wells. It does not establish causal role-shaping, a general Victorian convention, a positive
      control-author profile, stylistic equivalence, or authorship.
  - id: barbarians-romance-qualified-inference
    claim_id: qualified-speculative-inference
    expectation_target_id: barbarians-romance
    witness_id: the-british-barbarians
    role: scientific-romance control
    passage_ids:
    - the-british-barbarians:i:37:087b5c821b52
    comparison: The frozen Wells claim concerns observed detail moving into an explanation that remains
      provisional, revisable, or perception-limited. Here Philip inventories the stranger's sudden appearance
      and the visible approaches, poses competing explanations, and leaves his hedgerow explanation conditional
      on a socially biased assumption; the movement from observation to explanation is therefore explicitly
      limited by his viewpoint.
    result: shared
    notes: This is one local opening passage in the declared scientific-romance control, not evidence of
      prevalence across the witness. Qualification is confounded with satirical focalisation through Philip's
      snobbery and with the unexplained visitor premise. It neither establishes a general late-Victorian
      convention nor supports a positive profile, stylistic attribution, or authorship claim.
  - id: barbarians-satire-social-friction
    claim_id: humour-through-social-friction
    expectation_target_id: barbarians-satire
    witness_id: the-british-barbarians
    role: social satire
    passage_ids:
    - the-british-barbarians:ii:130:dc2c2c7ed9db
    - the-british-barbarians:ii:132:3690dd63c4ac
    - the-british-barbarians:ii:133:4e2614c49812
    comparison: The frozen Wells claim locates humour in a mismatch between social manner and incompatible
      understandings of the situation. Here Bertram's courteous, literal treatment of respectability as
      taboo collides with Frida's sense that he has carried the joke too far and Philip's stiff insistence
      that civilised England has no taboos; Bertram's polite catalogue then sharpens that mismatch.
    result: shared
    notes: The comparison is confined to this adjacent exchange in the declared social- satire role. Humour
      also depends on narratorial irony, conceptual reversal, and the visitor premise, so social friction
      is not isolated as the sole cause. One control work cannot establish period generality, a control-author
      style profile, stylistic attribution, or authorship.
  - id: days-qualified-scientific-exposition
    claim_id: qualified-scientific-exposition
    expectation_target_id: days-technical
    witness_id: the-days-work
    role: technical-work control
    passage_ids:
    - the-days-work:the-bridge-builders:72:c8e7cc2f7612
    comparison: 'The engineer tests the bridge''s capacity against the observed flood by remembering, comparing,
      estimating, and recalculating its components. His conclusion is locally qualified: the present load
      is near the bridge''s limit, an embankment weakness remains possible, and river scour is an explicitly
      unknown quantity. This supplies outside the declared Wells roles the frozen claim''s combination of
      technical explanation, observable procedure, comparison, and bounded uncertainty.'
    result: shared
    notes: The observation is confined to one crisis passage in one technical-work control witness. Engineering
      subject matter, professional focalisation, and immediate plot danger are confounded, so the passage
      does not estimate frequency or separate author, genre, role, or period. Shared means only that the
      bounded feature occurs in this control; it neither makes a positive profile of the control author
      nor supports period-wide, stylistic-equivalence, historical-implausibility, or authorship claims.
  - id: days-role-shaped-syntax
    claim_id: role-shaped-syntax
    expectation_target_id: days-dialogue
    witness_id: the-days-work
    role: professional dialogue
    passage_ids:
    - the-days-work:the-bridge-builders:17:204f12e196af
    - the-days-work:the-bridge-builders:18:e96545431969
    - the-days-work:the-bridge-builders:21:6b4843e20220
    comparison: Within the professional exchange, a warning develops through a coordinated statement and
      a qualified question, the reply contracts to two short declaratives, and a later turn expands through
      technical contrast, comparison with a ship and gang-plank, and successive questions. The resulting
      turn-to-turn sentence and paragraph movement is locally varied rather than a uniform cadence, sharing
      the broad observable tendency in the frozen Wells claim without reproducing its three-role comparison.
    result: shared
    notes: These adjacent turns are one exchange, not independent replications, and their movement is confounded
      with speaker, turn function, technical topic, represented speech, and scene. A single professional-dialogue
      role cannot establish that role causes syntax or reproduce the frozen claim's cross-role design. Shared
      therefore marks local occurrence outside Wells, not a positive control-author profile, a general late-Victorian
      rule, stylistic equivalence, historical implausibility, or authorship evidence.
  - id: days-selective-observed-description
    claim_id: selective-observed-description
    expectation_target_id: days-machinery
    witness_id: the-days-work
    role: machinery
    passage_ids:
    - the-days-work:the-bridge-builders:2:e421ff64ab2a
    comparison: The bridge survey selects dimensions, materials, structural categories, spatial relations,
      moving equipment, labour, sound, colour, and flame around the observable state and operation of the
      works. The details are organised by spatial inspection and functional classification rather than offered
      as an unstructured inventory, so the machinery control shares the frozen claim's broad descriptive
      selectivity.
    result: shared
    notes: This is one long opening survey in one machinery-authorised witness; scale, engineering subject,
      omniscient narration, spectacle, and narrative placement are confounded. Selection is inferred from
      the organisation of stated details, not from evidence about omitted details. The comparison does not
      establish frequency, causal role-shaping, a period-wide convention, stylistic equivalence, historical
      implausibility, a positive profile of the control author, or authorship.
reviewer_records:
  - id: review-mediated-testimony-frame
    claim_id: mediated-testimony-frame
    reviewer_id: root-claim-synthesis
    outcome: approved
    review_run_ids:
    - heldout-frame-narrator-closure
    - control-beetle-root
    - root-claim-synthesis
    heldout_result_ids:
    - heldout-tm-frame
    - heldout-star-testimony
    control_comparison_ids:
    - beetle-mediated-narrators
    notes: Both held-out roles retain visible evidentiary mediation, while the control establishes that
      overt narrative records also occur outside Wells. The bounded Wells finding is retained without a
      distinctiveness claim.
  - id: review-role-shaped-narrator-distance
    claim_id: role-shaped-narrator-distance
    reviewer_id: root-claim-synthesis
    outcome: approved
    review_run_ids:
    - heldout-frame-narrator-closure
    - control-beetle-root
    - root-claim-synthesis
    heldout_result_ids:
    - heldout-tm-reported
    - heldout-moreau-retrospective
    - heldout-matters-essay
    control_comparison_ids:
    - beetle-role-shaped-distance
    notes: All three held-out role targets reproduce the declared forms of distance. Multiple control narrators
      also separate experience from later judgement, so the contrasts are characteristic but not discriminating.
  - id: review-qualified-speculative-inference
    claim_id: qualified-speculative-inference
    reviewer_id: root-claim-synthesis
    outcome: approved
    review_run_ids:
    - heldout-inference-exposition
    - control-british-barbarians
    - root-claim-synthesis
    heldout_result_ids:
    - heldout-tm-speculation
    - heldout-war-inference
    control_comparison_ids:
    - barbarians-romance-qualified-inference
    notes: Both held-out targets retain revisable or explicitly bounded explanation. The control supplies
      the same broad observation-to-qualified-explanation movement under satirical focalisation.
  - id: review-qualified-scientific-exposition
    claim_id: qualified-scientific-exposition
    reviewer_id: root-claim-synthesis
    outcome: qualified
    review_run_ids:
    - heldout-inference-exposition
    - control-days-work
    - root-claim-synthesis
    heldout_result_ids:
    - heldout-tm-exposition
    - heldout-moreau-argument
    - heldout-biology-instruction
    - heldout-biology-comparison
    control_comparison_ids:
    - days-qualified-scientific-exposition
    notes: Three held-out targets support the claim, but Moreau's argument is less epistemically qualified
      than expected. The technical-work control shares procedural explanation and bounded uncertainty.
  - id: review-dialogue-pressure-varies-by-context
    claim_id: dialogue-pressure-varies-by-context
    reviewer_id: root-claim-synthesis
    outcome: approved
    review_run_ids:
    - heldout-dialogue-syntax-humour
    - control-adventure
    - root-claim-synthesis
    heldout_result_ids:
    - heldout-invisible-dialogue
    - heldout-moreau-stress
    control_comparison_ids:
    - desert-group-dialogue
    notes: Held-out scenes confirm substantial within- and cross-work variation under pressure. The group-dialogue
      control shares distributed turns and reactions, preventing a distinctiveness inference.
  - id: review-role-shaped-syntax
    claim_id: role-shaped-syntax
    reviewer_id: root-claim-synthesis
    outcome: approved
    review_run_ids:
    - heldout-dialogue-syntax-humour
    - control-days-work
    - root-claim-synthesis
    heldout_result_ids:
    - heldout-tm-rhythm
    - heldout-invisible-rhythm
    - heldout-matters-rhythm
    control_comparison_ids:
    - days-role-shaped-syntax
    notes: All three held-out targets show the expected local movements, and the professional-dialogue control
      also varies turn length and syntactic expansion. The result is descriptive rather than a role-effect
      estimate.
  - id: review-selective-observed-description
    claim_id: selective-observed-description
    reviewer_id: root-claim-synthesis
    outcome: qualified
    review_run_ids:
    - heldout-description-danger
    - control-days-work
    - root-claim-synthesis
    heldout_result_ids:
    - heldout-war-landscape
    - heldout-matters-microscope
    - heldout-biology-terms
    control_comparison_ids:
    - days-selective-observed-description
    notes: Landscape and biological terminology support local observational organisation, but the microscope
      target is substantially redirected by humour and analogy. The machinery control shares functional
      selection.
  - id: review-danger-through-observation
    claim_id: danger-through-observation
    reviewer_id: root-claim-synthesis
    outcome: qualified
    review_run_ids:
    - heldout-description-danger
    - control-adventure
    - root-claim-synthesis
    heldout_result_ids:
    - heldout-sea-danger
    - heldout-war-catastrophe
    control_comparison_ids:
    - desert-danger-pacing
    notes: Catastrophe supports consequence-before-explanation, while the biological target is weakened
      by retrospective advance warning. The adventure control shares local recognition-after-observation
      pacing.
  - id: review-humour-through-social-friction
    claim_id: humour-through-social-friction
    reviewer_id: root-claim-synthesis
    outcome: approved
    review_run_ids:
    - heldout-dialogue-syntax-humour
    - control-british-barbarians
    - root-claim-synthesis
    heldout_result_ids:
    - heldout-invisible-comic
    - heldout-matters-humour
    control_comparison_ids:
    - barbarians-satire-social-friction
    notes: Both held-out targets reproduce humour through incompatible social understandings. The social-satire
      control shares the mechanism, alongside narratorial irony and conceptual reversal.
  - id: review-short-form-evidentiary-closure
    claim_id: short-form-evidentiary-closure
    reviewer_id: root-claim-synthesis
    outcome: qualified
    review_run_ids:
    - heldout-frame-narrator-closure
    - control-adventure
    - root-claim-synthesis
    heldout_result_ids:
    - heldout-tm-ending
    - heldout-star-ending
    control_comparison_ids:
    - solomon-journey-closure
    notes: The Star supports resolved event record with open implications, but the Time Machine sample omits
      the terminal frame. Haggard's journey closure settles its principal outcomes, yet one negative control
      cannot establish distinctiveness.
review_run_provenance:
  - run_id: heldout-frame-narrator-closure
    reviewer_id: delegated-heldout-reader-frame-narrator-closure
    role_id: delegated-heldout-reader
    stage: heldout_review
    assigned_claim_ids:
    - mediated-testimony-frame
    - role-shaped-narrator-distance
    - short-form-evidentiary-closure
    method: Independent delegated reading of the assigned held-out Wells packet with source and witness IDs visible.
    materials_seen:
    - frozen candidate claim assignments
    - held-out Wells packet
    - passage context windows
    independent_of_candidate_authorship: true
    anonymisation_status: not_anonymised
    outcome: Held-out assessments recorded for the assigned frame, narrator-distance, and closure claims.
    produced_record_ids:
    - heldout-tm-frame
    - heldout-star-testimony
    - heldout-tm-reported
    - heldout-moreau-retrospective
    - heldout-matters-essay
    - heldout-tm-ending
    - heldout-star-ending
    limitations: The delegated reviewer and source IDs were not anonymised; the opaque delegated-agent ID was not retained.
  - run_id: heldout-inference-exposition
    reviewer_id: delegated-heldout-reader-inference-exposition
    role_id: delegated-heldout-reader
    stage: heldout_review
    assigned_claim_ids:
    - qualified-speculative-inference
    - qualified-scientific-exposition
    method: Independent delegated reading of the assigned held-out Wells packet with source and witness IDs visible.
    materials_seen:
    - frozen candidate claim assignments
    - held-out Wells packet
    - passage context windows
    independent_of_candidate_authorship: true
    anonymisation_status: not_anonymised
    outcome: Held-out assessments recorded for inference and exposition claims.
    produced_record_ids:
    - heldout-tm-speculation
    - heldout-war-inference
    - heldout-tm-exposition
    - heldout-moreau-argument
    - heldout-biology-instruction
    - heldout-biology-comparison
    limitations: The delegated reviewer and source IDs were not anonymised; the opaque delegated-agent ID was not retained.
  - run_id: heldout-dialogue-syntax-humour
    reviewer_id: delegated-heldout-reader-dialogue-syntax-humour
    role_id: delegated-heldout-reader
    stage: heldout_review
    assigned_claim_ids:
    - dialogue-pressure-varies-by-context
    - role-shaped-syntax
    - humour-through-social-friction
    method: Independent delegated reading of the assigned held-out Wells packet with source and witness IDs visible.
    materials_seen:
    - frozen candidate claim assignments
    - held-out Wells packet
    - passage context windows
    independent_of_candidate_authorship: true
    anonymisation_status: not_anonymised
    outcome: Held-out assessments recorded for dialogue, syntax, and humour claims.
    produced_record_ids:
    - heldout-invisible-dialogue
    - heldout-moreau-stress
    - heldout-tm-rhythm
    - heldout-invisible-rhythm
    - heldout-matters-rhythm
    - heldout-invisible-comic
    - heldout-matters-humour
    limitations: The delegated reviewer and source IDs were not anonymised; the opaque delegated-agent ID was not retained.
  - run_id: heldout-description-danger
    reviewer_id: delegated-heldout-reader-description-danger
    role_id: delegated-heldout-reader
    stage: heldout_review
    assigned_claim_ids:
    - selective-observed-description
    - danger-through-observation
    method: Independent delegated reading of the assigned held-out Wells packet with source and witness IDs visible.
    materials_seen:
    - frozen candidate claim assignments
    - held-out Wells packet
    - passage context windows
    independent_of_candidate_authorship: true
    anonymisation_status: not_anonymised
    outcome: Held-out assessments recorded for description and danger claims.
    produced_record_ids:
    - heldout-war-landscape
    - heldout-matters-microscope
    - heldout-biology-terms
    - heldout-sea-danger
    - heldout-war-catastrophe
    limitations: The delegated reviewer and source IDs were not anonymised; the opaque delegated-agent ID was not retained.
  - run_id: control-adventure
    reviewer_id: delegated-control-reader-adventure
    role_id: delegated-control-reader
    stage: control_review
    assigned_claim_ids:
    - dialogue-pressure-varies-by-context
    - danger-through-observation
    - short-form-evidentiary-closure
    method: Independent delegated reading of the assigned Tier 4 control packet with source and witness IDs visible.
    materials_seen:
    - frozen candidate claim assignments
    - Tier 4 control packet
    - passage context windows
    independent_of_candidate_authorship: true
    anonymisation_status: not_anonymised
    outcome: Comparative control assessments recorded for dialogue, danger, and closure claims.
    produced_record_ids:
    - desert-group-dialogue
    - desert-danger-pacing
    - solomon-journey-closure
    limitations: The delegated reviewer and source IDs were not anonymised; controls have negative/comparative jurisdiction only, and the opaque delegated-agent ID was not retained.
  - run_id: control-british-barbarians
    reviewer_id: delegated-control-reader-british-barbarians
    role_id: delegated-control-reader
    stage: control_review
    assigned_claim_ids:
    - qualified-speculative-inference
    - humour-through-social-friction
    method: Independent delegated reading of the assigned Tier 4 control packet with source and witness IDs visible.
    materials_seen:
    - frozen candidate claim assignments
    - Tier 4 control packet
    - passage context windows
    independent_of_candidate_authorship: true
    anonymisation_status: not_anonymised
    outcome: Comparative control assessments recorded for inference and humour claims.
    produced_record_ids:
    - barbarians-romance-qualified-inference
    - barbarians-satire-social-friction
    limitations: The delegated reviewer and source IDs were not anonymised; controls have negative/comparative jurisdiction only, and the opaque delegated-agent ID was not retained.
  - run_id: control-days-work
    reviewer_id: delegated-control-reader-days-work
    role_id: delegated-control-reader
    stage: control_review
    assigned_claim_ids:
    - qualified-scientific-exposition
    - role-shaped-syntax
    - selective-observed-description
    method: Independent delegated reading of the assigned Tier 4 control packet with source and witness IDs visible.
    materials_seen:
    - frozen candidate claim assignments
    - Tier 4 control packet
    - passage context windows
    independent_of_candidate_authorship: true
    anonymisation_status: not_anonymised
    outcome: Comparative control assessments recorded for exposition, syntax, and description claims.
    produced_record_ids:
    - days-qualified-scientific-exposition
    - days-role-shaped-syntax
    - days-selective-observed-description
    limitations: The delegated reviewer and source IDs were not anonymised; controls have negative/comparative jurisdiction only, and the opaque delegated-agent ID was not retained.
  - run_id: control-beetle-root
    reviewer_id: root-local-control-reader-beetle
    role_id: root-control-reader
    stage: control_review
    assigned_claim_ids:
    - mediated-testimony-frame
    - role-shaped-narrator-distance
    method: Local root completion of the Beetle control comparison after the delegated Beetle reader was timeboxed.
    materials_seen:
    - frozen candidate claim assignments
    - Beetle control passages
    - passage context windows
    independent_of_candidate_authorship: false
    anonymisation_status: not_anonymised
    outcome: Comparative control assessments recorded for mediation and narrator-distance claims.
    produced_record_ids:
    - beetle-mediated-narrators
    - beetle-role-shaped-distance
    limitations: This run was completed locally by root after the delegated Beetle reader was timeboxed; it was not independent of candidate authorship, and source and witness IDs were visible.
  - run_id: root-claim-synthesis
    reviewer_id: root-claim-synthesis
    role_id: root-claim-synthesis
    stage: claim_synthesis
    assigned_claim_ids:
    - mediated-testimony-frame
    - role-shaped-narrator-distance
    - qualified-speculative-inference
    - qualified-scientific-exposition
    - dialogue-pressure-varies-by-context
    - role-shaped-syntax
    - selective-observed-description
    - danger-through-observation
    - humour-through-social-friction
    - short-form-evidentiary-closure
    method: Root synthesis of claim decisions from the independently authored held-out and control results, plus the two locally completed Beetle comparisons.
    materials_seen:
    - held-out result records
    - control comparison records
    - candidate and final ledger/profile artifacts
    independent_of_candidate_authorship: false
    anonymisation_status: not_anonymised
    outcome: Final statuses and classifications synthesized; no fresh blind review was performed.
    produced_record_ids:
    - review-mediated-testimony-frame
    - review-role-shaped-narrator-distance
    - review-qualified-speculative-inference
    - review-qualified-scientific-exposition
    - review-dialogue-pressure-varies-by-context
    - review-role-shaped-syntax
    - review-selective-observed-description
    - review-danger-through-observation
    - review-humour-through-social-friction
    - review-short-form-evidentiary-closure
    limitations: Root synthesis was not an independent fresh reviewer; it converted distributed validation results into the ten ReviewerRecord decisions.
  - run_id: final-audit-initial
    reviewer_id: codex-task-019f68e6-2a2e-7812-9536-b50984f45aaa
    role_id: independent-whole-study-auditor
    stage: whole_study_audit
    assigned_claim_ids:
    - mediated-testimony-frame
    - role-shaped-narrator-distance
    - qualified-speculative-inference
    - qualified-scientific-exposition
    - dialogue-pressure-varies-by-context
    - role-shaped-syntax
    - selective-observed-description
    - danger-through-observation
    - humour-through-social-friction
    - short-form-evidentiary-closure
    method: Independent whole-study audit of the approved design and plan, full Git range, final artifacts, and generated report.
    materials_seen:
    - approved design
    - approved implementation plan
    - full Git range
    - final artifacts
    - generated analysis report
    independent_of_candidate_authorship: true
    anonymisation_status: not_anonymised
    outcome: changes_requested
    produced_record_ids: []
    limitations: Reviewed repository evidence rather than independently rereading the complete literary corpus; this was a non-blind audit, and completion approval remains an external final gate.
claim_transitions:
  - claim_id: mediated-testimony-frame
    from_status: candidate
    to_status: validated
    from_confidence: moderate
    to_confidence: moderate
    reason: Two supporting held-out targets validate recurrence, and the shared control corrects classification
      without contradicting the bounded claim.
    heldout_result_ids:
    - heldout-tm-frame
    - heldout-star-testimony
    control_comparison_ids:
    - beetle-mediated-narrators
    reviewer_record_ids:
    - review-mediated-testimony-frame
  - claim_id: role-shaped-narrator-distance
    from_status: candidate
    to_status: validated
    from_confidence: tentative
    to_confidence: moderate
    reason: Complete held-out support raises confidence, while the shared control removes any plausible
      Wells-distinctive interpretation.
    heldout_result_ids:
    - heldout-tm-reported
    - heldout-moreau-retrospective
    - heldout-matters-essay
    control_comparison_ids:
    - beetle-role-shaped-distance
    reviewer_record_ids:
    - review-role-shaped-narrator-distance
  - claim_id: qualified-speculative-inference
    from_status: candidate
    to_status: validated
    from_confidence: tentative
    to_confidence: moderate
    reason: The predeclared Wells tendency recurs twice without contradiction; control sharing corrects
      classification rather than weakening historical recurrence.
    heldout_result_ids:
    - heldout-tm-speculation
    - heldout-war-inference
    control_comparison_ids:
    - barbarians-romance-qualified-inference
    reviewer_record_ids:
    - review-qualified-speculative-inference
  - claim_id: qualified-scientific-exposition
    from_status: candidate
    to_status: qualified
    from_confidence: tentative
    to_confidence: moderate
    reason: The tendency survives validation but requires explicit allowance for assertive scientific argument
      and cannot be classified as distinctive.
    heldout_result_ids:
    - heldout-tm-exposition
    - heldout-moreau-argument
    - heldout-biology-instruction
    - heldout-biology-comparison
    control_comparison_ids:
    - days-qualified-scientific-exposition
    reviewer_record_ids:
    - review-qualified-scientific-exposition
  - claim_id: dialogue-pressure-varies-by-context
    from_status: candidate
    to_status: validated
    from_confidence: tentative
    to_confidence: moderate
    reason: Both held-out targets support the bounded contrast; the shared control narrows classification
      but does not contradict it.
    heldout_result_ids:
    - heldout-invisible-dialogue
    - heldout-moreau-stress
    control_comparison_ids:
    - desert-group-dialogue
    reviewer_record_ids:
    - review-dialogue-pressure-varies-by-context
  - claim_id: role-shaped-syntax
    from_status: candidate
    to_status: validated
    from_confidence: tentative
    to_confidence: moderate
    reason: Three supporting held-out roles justify moderate confidence in the bounded contrast, with shared
      control evidence correcting classification.
    heldout_result_ids:
    - heldout-tm-rhythm
    - heldout-invisible-rhythm
    - heldout-matters-rhythm
    control_comparison_ids:
    - days-role-shaped-syntax
    reviewer_record_ids:
    - review-role-shaped-syntax
  - claim_id: selective-observed-description
    from_status: candidate
    to_status: qualified
    from_confidence: tentative
    to_confidence: tentative
    reason: The claim remains useful only with the microscope qualification visible and with tentative confidence
      after a shared control occurrence.
    heldout_result_ids:
    - heldout-war-landscape
    - heldout-matters-microscope
    - heldout-biology-terms
    control_comparison_ids:
    - days-selective-observed-description
    reviewer_record_ids:
    - review-selective-observed-description
  - claim_id: danger-through-observation
    from_status: candidate
    to_status: qualified
    from_confidence: tentative
    to_confidence: tentative
    reason: Mixed held-out assessment and a shared control require qualification without rejecting the bounded
      local tendency.
    heldout_result_ids:
    - heldout-sea-danger
    - heldout-war-catastrophe
    control_comparison_ids:
    - desert-danger-pacing
    reviewer_record_ids:
    - review-danger-through-observation
  - claim_id: humour-through-social-friction
    from_status: candidate
    to_status: validated
    from_confidence: tentative
    to_confidence: moderate
    reason: Complete held-out recurrence supports moderate confidence, while the shared control rules out
      a Wells-distinctive classification.
    heldout_result_ids:
    - heldout-invisible-comic
    - heldout-matters-humour
    control_comparison_ids:
    - barbarians-satire-social-friction
    reviewer_record_ids:
    - review-humour-through-social-friction
  - claim_id: short-form-evidentiary-closure
    from_status: candidate
    to_status: qualified
    from_confidence: moderate
    to_confidence: moderate
    reason: One supportive and one scope-limited held-out result justify qualification; the non-shared control
      preserves role specificity but cannot prove uniqueness.
    heldout_result_ids:
    - heldout-tm-ending
    - heldout-star-ending
    control_comparison_ids:
    - solomon-journey-closure
    reviewer_record_ids:
    - review-short-form-evidentiary-closure
unresolved_uncertainty: Role-work aliasing, limited within-role replication, transcription sensitivity, one-control discrimination, and the absence of the terminal Time Machine frame from its held-out window remain material limits; no result supports an authorship verdict or period-wide rule.
final_profile_sha256: 975b29b86bf174f03d65ed843514b9340cc99493f1b48857add9c0023eb100e3
final_ledger_sha256: c9d01946ca8c68492369a9962c1953ffb1c83948d61863c152fc8514d51b54e1
---

# Validation Record

## Final Phase 2B validation

The candidate profile, evidence ledger, analysis contract, and holdout manifest
remain bound to the recorded candidate Git commit and SHA-256 values. All 25
predeclared held-out Wells targets were assessed against that frozen candidate:
21 support the expected tendency and four qualify its scope. No target
disconfirms its candidate tendency.

All ten predeclared Tier 4 comparisons were then assessed within their negative
or comparative roles. Nine show that the bounded feature also occurs outside
Wells; the Haggard journey ending provides one local non-match. These controls
correct classification but supply no positive style authority.

Independent delegated readers supplied all held-out assessments and most control
comparisons. Root completed the two Beetle controls and synthesized six validated
and four qualified claim decisions; none is rejected or assigned strong
confidence. The initial independent whole-study audit requested the profile,
report, and review-provenance completion-gate repairs now recorded here. The final
descriptive profile and evidence ledger remain bound to their recorded SHA-256
values. Operational guidance, linting, story planning, and prose generation remain
outside this record's authority.

# Human annotation intake

Status: intake complete; see [the provisional report](expressibility-report.md).

## Source and provenance

The user supplied a 16-task annotation in chat and attributed it to a friend.
The user reports that the friend used no AI and did not receive the user's
previous answers. This is a participant-provenance report relayed by the user.
The assistant transcribed the submitted task section into
`data/milestone-2/submissions/friend-01/original.md`. Formatting whitespace
was normalized; the submitted prompts, fact labels, verdicts and rationales
were preserved in their original language, including apparent errors.
The surrounding chat discussion is not part of that task-section transcription.

The submission is separate from exploratory annotator A and from the user's
previous AI-assisted judgments. No independent authorship is attributed to
the user's earlier judgments. The user subsequently confirmed the current v2
instructions. The completion timestamp was not supplied. The completed record's
`created_utc` denotes serialization time, not participant completion time;
this departure is disclosed in the report and protocol confirmation.

## Completion checks

- All task IDs 0 through 15 have a verdict and at least one source label.
- Task 15 had no rationale in the initial submission. The user subsequently
  supplied it in response to a neutral request for the friend's rationale.
  It is preserved separately in `task-15-supplement.md` in the same directory.
- The user confirmed the current v2 instructions, including the authorization
  filter. This answer is preserved in `protocol-confirmation.json`.
- Preserve the original submission. Save any later clarification separately,
  with its receipt time and whether feedback preceded it.

No labels have been corrected or replaced. Schema validation cannot establish
that an annotator applied the rubric correctly. The report must distinguish
rubric disagreements from missing fields; it must not silently replace
human judgments with the assistant's preferred answers.

The original intake is outside `annotations/`. The completed, protocol-linked
set is `data/milestone-2/annotations/annotator-B-friend.json`.

## Remaining report work

The completed set was serialized, all 16 tasks validated, and analysis output
saved before writing the report. Remaining work concerns a second independent
rater and the rubric-adherence issues recorded there.

One eligible independent human set permits a single-annotator report under
Task 6. Agreement remains unavailable until a second independent human set
exists. The older log sentence requiring two people for any headline rate
overstates the frozen protocol; two people are required for agreement.

Report each annotator's results separately. Do not use exploratory A or the
user's assisted judgments to manufacture independent agreement. Any
preregistered branch is a within-study decision about a follow-up experiment,
not proof of novelty, a general impossibility theorem, or prevention efficacy.

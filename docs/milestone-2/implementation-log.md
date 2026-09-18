# Milestone 2 implementation log

Plan: `docs/superpowers/plans/2026-09-18-contract-expressibility-study.md`
Started: 2026-09-18

## Task 0: complete

`docs/milestone-2/pre-registration.md` frozen and hashed.
SHA-256: `ec1a13a426f009cfeface62f86e3b456a086acda49494a80f9d16fdc2bfde07e`
Hash reproduced on re-run; matches the stored `.sha256` file.

## Task 1: complete

`src/tbm/expressibility.py` created: `AuthoritySource`, `Expressibility`,
`AuthorityFact`, `TaskAnnotation`, `AnnotationSet`. 5/5 tests passed on first
green run (failed first with `ModuleNotFoundError` as expected). Ruff check
and format-check both clean. No import of `agentdojo` or any other `tbm`
module.

## Task 2: complete

`src/tbm/annotate.py` created: `build_prompt_fixture`, `load_prompt_fixture`,
`save_annotation_set`, `load_annotation_set`. 6/6 tests passed (failed first
with `ModuleNotFoundError` as expected). `ruff format` reflowed two lines
past the plan's verbatim listing (line-length rule); `ruff check` and
`format --check` both clean afterward, tests re-ran green. Real fixture
generated at `data/milestone-2/task-prompts.json`, SHA-256
`f10c0fd8ecc2475fa4eaaeeaed7c89ae3925052e31307eb28a0ee43ddc74d2a3`, confirmed
ignored by the root `/*` rule in `.gitignore`.

## Task 3: complete

`src/tbm/expressibility_report.py` created: `compute_rates`, `cohens_kappa`,
`compare_annotators`, `decision`. 8/8 new tests passed (failed first with
`ModuleNotFoundError` as expected). Full suite: 143 passed (previous 124 +
19 added across Tasks 1-3), ruff check and format-check both clean across
`src` and `tests`. No pre-existing test changed behavior. `decision()`
raises `ValueError` for any total other than 16.

## Task 4: complete

`data/milestone-2/annotations/annotator-A.json` created and validated: 16
annotations, `contaminated=True`. Exploratory rates (annotator A only, never
a headline number):

```
{'total': 16, 'counts': {'partially_expressible': 11, 'expressible': 2, 'inexpressible': 3},
 'expressibility_rate': 0.125, 'unresolved_authority_rate': 0.875,
 'unresolved_authority_count': 14, 'untrusted_provenance_rate': 0.75}
```

`compare_annotators` over `[A]` alone returned `uncontaminated_annotators: []`
and `agreement_verdict: None`, confirming the guard.

## Task 5: complete

`docs/milestone-2/annotation-instructions.md` created: self-contained, all
16 prompts pasted inline, both classification tables copied from the
pre-registration, JSON shape with one filled example, save paths for
annotators B (user) and C (professor), and the no-conferring statement.
Leak check printed `clean`.

## Task 6: BLOCKED — awaiting human annotation

No file exists yet at `data/milestone-2/annotations/annotator-B.json` or
`annotator-C.json`. Only the contaminated annotator A exists. Per the plan,
this task does not run until at least one uncontaminated annotation set
exists. `docs/milestone-2/expressibility-report.md` is not written.
**Human annotation (user as B, and ideally the professor as C, using
`docs/milestone-2/annotation-instructions.md`) is the gating input for the
rest of this study.**

## Task 7: complete

All six previously-unverified identifiers were fetched from
`https://arxiv.org/abs/<id>` and confirmed real:

- `2512.11147` — confirmed, "MiniScope: A Least Privilege Framework for
  Authorizing Tool Calling Agents"
- `2605.05868` — confirmed, "SkillScope: Toward Fine-Grained Least-Privilege
  Enforcement for Agent Skills"
- `2606.22916` — confirmed, "Intent-Governed Tool Authorization for AI
  Agents"
- `2602.16708` — confirmed, "Formal Policy Enforcement for Real-World
  Agentic Systems"
- `2606.03518` — confirmed, "Overlaying Governance: A Compositional
  Authorization Framework for Delegation and Scope in Agentic AI"
- `2609.06500` — confirmed, "CAPMAS: Capability-Based Delegation of
  Privileges in Multi-Agent Systems"

None was `NOT FOUND`; none was deleted. `docs/milestone-2/related-work.md`
written with title, identifier, one-sentence claim and one-sentence
foreclosure for each, plus the restated ScopeGate and escalation-fatigue
foreclosures from the plan.

## Status after this session

Tasks 0-5 and 7 complete. Task 6 blocked on human annotation (see above).
No commit, push, PR, or contact with the professor was made, per Global
Constraints. Full test suite: 143 passed (unchanged since Task 3); no
existing test, contract, policy, gateway or runner file was modified.

## Amendment: pre-registration v2, before any uncontaminated annotation

Review of annotator A's exploratory output found two defects. Both were
repaired before annotator B or C annotated, so neither repair could move a
measured rate across a threshold. The decision-rule thresholds are untouched.

**Defect 1, ambiguous criteria.** v1 never distinguished a fact the gateway
needs in order to *authorize* an action from a fact the agent needs in order
to *complete* the task correctly. Annotator A classified `user_task_7` as
`inexpressible/agent_judgment` on interpretive difficulty alone, although it
authorizes no state change and is structurally identical to `user_task_1` and
`user_task_8`, which it called `expressible`. It also called `user_task_14`
`inexpressible` although the user names the exact permitted value there, with
only the trigger being subjective. Both errors ran in the direction that
favors the hypothesis. `docs/milestone-2/pre-registration-v2.md` adds the
authorization-fact filter, the read-only rule and the conditional-write rule.
SHA-256 `032e2059b2418281e6f6b5947c1756845f5949c048ed4f3e892c08c48dc8e477`.
v1 is retained unedited at `pre-registration.md` as the record of what
annotator A used; annotator A's stored file still cites the v1 hash, and its
annotation is not revised. The disagreement is itself evidence that the v1
criteria were underspecified.

**Defect 2, broken blinding.** `annotation-instructions.md` illustrated
`delegated` and `agent_judgment` by quoting the actual phrases of two of the
sixteen prompts, which pre-decided those two tasks for every human annotator.
The illustrative column was removed and the tables now define the categories
without quoting any prompt. Re-ran the leak check over the whole document and
over the instruction half specifically: both clean. The `preregistration_sha256`
example in the instructions now carries the v2 hash.

Impact on the exploratory figure: annotator A reported
`unresolved_authority_rate` 14/16. Correcting both disputed tasks would give
12/16, still at or above the pre-registered 8/16 threshold, so the branch is
unchanged. The exploratory number remains exploratory either way and no
headline rate exists until two uncontaminated annotators have finished.

## Task 6 continues to be BLOCKED — additional finding: live AI-facilitated annotation was tried and abandoned

An attempt was made to have the user annotate as B interactively, in
conversation with the assistant, task by task. It was abandoned partway
through (after tasks 0-6) at the user's own initiative, for a sound reason:
the assistant repeatedly steered the user toward specific classifications
instead of eliciting independent judgment. Concretely:

- For tasks with an unambiguous textual cue (0, 1, 4, 5's percentage, 6's
  recipient), the assistant pointed at the literal text. This narrows
  interpretation to something close to zero regardless of who is annotating,
  so it is a weak form of contamination at worst.
- For tasks with real interpretive latitude (2, 3), the assistant asked
  "Socratic" guiding questions that effectively pre-selected the resolving
  distinction (e.g., "does the sentence limit what may change, or hand
  everything to the file?") rather than letting the user surface that
  distinction unprompted.
- On task 6's recipient fact, the assistant stated the classification
  outright ("άρα user_explicit") instead of asking. This is the same defect
  as annotator A's self-contamination, reproduced live in the annotation of
  B.

None of the six partial answers from this session (tasks 0-6) are saved as
`data/milestone-2/annotations/annotator-B.json` or used anywhere as
evidence. They are not an uncontaminated annotation set and must not be
treated as one. Task 6 (the report) remains blocked exactly as before this
attempt.

**Recommendation carried forward:** annotator B (and C, if the professor
participates) should annotate solo, offline, from `annotation-instructions.md`
alone, with no conversational back-and-forth with the assistant during the
judgment step itself. The assistant's only legitimate post-hoc role is
mechanical schema validation of the finished file (`load_annotation_set`),
which involves no judgment. If a live-assisted process is used again in the
future, this transcript is the concrete evidence of why it tends to
collapse into the assistant's own view, and should be cited as a limitation
rather than repeated uncritically.

## Task 6: provisional single-annotator report completed, 2026-09-18

The user submitted a friend's 16-task annotation and reports that the friend
used no AI and saw no earlier answers. The user subsequently confirmed use
of the current v2 instructions. Independence is recorded on this relayed
account, not independently observed. The participant is `B_friend`, distinct
from both exploratory A and the user's previously assisted judgments.

The task-section transcription is preserved in
`data/milestone-2/submissions/friend-01/original.md`. Task 15 initially lacked
a rationale; the user supplied one after a neutral request. It is retained
as `task-15-supplement.md`. A structured intake, source hashes, and later
instruction confirmation are stored alongside them. No labels were revised.

The complete set is `data/milestone-2/annotations/annotator-B-friend.json`,
SHA-256 `9c7d08efda4ab528f876f411184c99dbc985c362973a8b8d40ac05ebc61e17c3`.
The actual annotation-completion time was not supplied. Its `created_utc`
records serialization time; that departure from the instruction format is
explicit in the report and confirmation metadata. Original Greek is retained
to avoid changing annotations through translation.

Computed output was saved before interpretation and copied to
`docs/milestone-2/evidence/friend-01-analysis.json`. Raw submitted human labels:
0 expressible, 11 partial, 5 inexpressible; unresolved authority 16/16;
untrusted provenance 16/16. The frozen decision returns `supported`.
Both agreement values are null because only one independent human set exists.
Exploratory A remains excluded from independent agreement and headline rates.

`expressibility-report.md` records rubric-adherence issues, including the
answer-data versus authorization-data distinction and Task 15's explicit
refund amount. The report is provisional: the raw-label branch does not
resolve those issues or prove novelty or defense efficacy. No criteria,
source labels, verdicts, or thresholds were changed. The report records that
many rationales paraphrase instead of quoting the decisive prompt phrase.

Correction to earlier log wording: the frozen protocol and Task 6 permit
a report with one independent annotator. Two are required for agreement,
not for any report. The next step is a second independent rater who sees
only the frozen instructions, followed by documented assessment of disagreements.

Verification performed:

```text
python -m pytest -q tests/test_annotate.py tests/test_expressibility.py tests/test_expressibility_report.py
19 passed in 4.05s

Source hashes, unchanged annotations, all 16 task IDs, non-empty rationales,
frozen v2 hash, recomputed rates/decision/agreement, evidence-copy equality,
and report counts: PASS.
git check-ignore: source submission, supplement, structured intake,
confirmation, analysis output, and completed human set remain ignored.
```

The report's Yan reference was reopened at https://arxiv.org/abs/2608.27443
and its title, author and abstract verified before citation. An initial
documentation patch failed its context check without changing files; the
corrected patch succeeded. No source code or tests were changed. No commit,
push, paid call, cloud resource or external message was made.

# Contract expressibility: single-annotator findings

Date: 2026-09-18

The human submission labels 11 of 16 tasks `partially_expressible` and 5
`inexpressible`. The frozen decision function returns `supported` for these
labels. Several rationales appear to conflict with the v2 authorization-fact
filter. This is a provisional annotation result, not validated evidence that
all 16 tasks have unresolved authority.

## Question and method

Can authorization constraints for a native banking task be specified from
the user prompt alone, and where do missing authorization facts come from?

The study covers 16 AgentDojo banking v1.2.2 prompts using
[pre-registration v2](pre-registration-v2.md), SHA-256
`032e2059b2418281e6f6b5947c1756845f5949c048ed4f3e892c08c48dc8e477`.
The instructions contain prompts and a rubric without environment fixtures
or reference traces. A stripped fixture limits supplied information; it
cannot prove what participants independently accessed.

Participant `B_friend` is a friend of the author. The author reports that this
participant used the current instructions, used no AI, and had no access to
earlier answers. This provenance was relayed by the author and was not
independently observed. Independence is recorded on that basis.

The initial submission has 16 verdicts and 15 rationales. The author relayed
the missing Task 15 rationale after a neutral request. The initial text and
supplement are preserved separately in their original Greek. The assistant
transcribed the records, checked their structure, calculated statistics, and
prepared this report. No submitted source label or verdict was changed.
The study as a whole is not described as having been conducted without AI.

The human record's `created_utc` is its serialization time. The annotator's
actual completion time was not supplied. This departure from the instructions'
requested completion timestamp is documented in
`data/milestone-2/submissions/friend-01/protocol-confirmation.json`, together
with the user's instruction-version confirmation and participant mapping.

Exploratory annotator A is a contaminated model annotation under v1. The
author's earlier assisted judgments are also not an independent human set.
Neither supplies a second independent rater.

## Counts and rates

| Task IDs | Submitted verdict | Count |
|---|---|---:|
| None | `expressible` | 0 |
| 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 15 | `partially_expressible` | 11 |
| 0, 2, 12, 13, 14 | `inexpressible` | 5 |

| Metric | B_friend |
|---|---:|
| Expressibility rate | 0/16 (0%) |
| Unresolved authority rate | 16/16 (100%) |
| Untrusted provenance rate | 16/16 (100%) |
| Verdict agreement | Unavailable |
| Source agreement | Unavailable |

These rates describe submitted labels, not independently established facts
about the tasks. For traceability only, excluded exploratory A has 2
expressible, 11 partial and 3 inexpressible tasks, unresolved authority 14/16
and untrusted provenance 12/16. Its v1 results are not pooled with the human
v2 results or treated as replication.

## Decision and disagreement

`decision(16, 16)` returns `supported` under the unchanged threshold of at
least 8 unresolved tasks. This is the preregistered branch for the submitted
labels. Interpretation remains subject to the rubric-adherence issues below.
No label or threshold was adjusted to obtain this branch.

Only one independent human set is available. Both Cohen's kappa measures are
unavailable. There are no independent rater pairs whose disagreements and
paired rationales can be reported yet. Comparing contaminated v1 annotator A
with this v2 submission would not fill that gap.

## Rubric adherence

These are post-submission observations by the report preparer, not replacement
labels or a second independent rating. Original labels remain unchanged.

- Tasks 1, 7 and 8 justify partial expressibility through retrieval needed
  for an answer. Under v2, answer-completion data alone do not establish a
  missing authorization constraint.
- Task 0 records `untrusted_document` values but an `inexpressible` verdict;
  its rationale describes delegation. The relationship between its source
  labels, rationale, and partial/inexpressible boundary needs clarification.
- Task 9 assigns the new amount to account history, although the prompt does
  not specify where to obtain it. This is an interpretation of the prompt.
- Task 10's annotation says "like last year" while the prompt says "like last
  month". The submitted wording is preserved.
- Task 14 treats the subjective trigger as governing authorization. The v2
  conditional-write rule distinguishes the trigger from the permitted effect.
  Whether that rule adequately models conditional authorization is itself a
  methodological limitation; it cannot be silently revised after annotation.
- Task 15 assigns the refund amount to history although the full prompt states
  10.00. Identifying the recipient or matching a transaction is a separate
  fact. Its supplemental rationale repeats the amount interpretation.

The instructions request a decisive prompt quotation in every rationale.
Many submitted rationales paraphrase instead. This departure is recorded;
schema validation does not test quotation compliance or semantic correctness.

Any adjudication must retain initial records and disclose preceding feedback.
A second rater should see only the frozen instructions, not this report or
the first rater's answers. Revisions after exposure to this analysis would
not be new blind annotations.

## Limits and next step

The sample is small, covers one suite and domain, and has one independently
reported human rater. Rubric adherence is unresolved. It cannot establish
prevalence across enterprise tasks, novelty, or general impossibility of
expressing authorization. Expressibility here has the rubric's specific meaning.

No attack or gateway evaluation was executed in this milestone. The results
measure neither prevention nor enforcement. Human approval also needs separate
evaluation: Yan reports agent overreach following human approval, so escalation
alone is not evidence of protection.
[Do User-Authored Permission Policies Improve Protection Against AI Agent Overreach?](https://arxiv.org/abs/2608.27443)

The next evidence step is a second independent annotation under the same
instructions, followed by a documented assessment of disagreement and rubric
adherence. A later enforcement study must test how the gateway obtains or
escalates missing authority and what happens after that decision.

## Reproduction

Exact output: [evidence/friend-01-analysis.json](evidence/friend-01-analysis.json).
Private sources: `data/milestone-2/submissions/friend-01/`.
Completed set: `data/milestone-2/annotations/annotator-B-friend.json`.
These data remain git-ignored. The initial `submission.json` preserves intake
before version confirmation; the separate confirmation records the later answer.

Run from the repository root:

```powershell
@'
import json
from pathlib import Path
from tbm.annotate import load_annotation_set
from tbm.expressibility_report import compute_rates, compare_annotators, decision
sets = [load_annotation_set(p) for p in sorted(Path("data/milestone-2/annotations").glob("*.json"))]
print(json.dumps({s.annotator_id: compute_rates(s) for s in sets}, indent=2))
print(json.dumps(compare_annotators(sets), indent=2))
print(json.dumps({s.annotator_id: decision(compute_rates(s)["unresolved_authority_count"], 16) for s in sets if not s.contaminated}, indent=2))
'@ | .\.venv\Scripts\python.exe -X utf8 -
```

The annotation-related test files passed: 19 tests. The submission was also
checked for all 16 distinct task IDs, valid source/verdict enums, and non-empty
rationales after the supplement. The v2 hash still matches its checksum.
These are structural and arithmetic checks.

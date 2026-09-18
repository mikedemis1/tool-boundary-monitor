Frozen: 2026-09-18

# Pre-registration v2: Contract Expressibility Study

Supersedes `pre-registration.md` (v1, SHA-256 `ec1a13a426f009cfeface62f86e3b456a086acda49494a80f9d16fdc2bfde07e`).
v1 is retained unedited as the record of what annotator A used.

**Reason for this amendment, recorded before any uncontaminated annotation exists:**
v1 did not distinguish a fact the gateway needs in order to *authorize* an action
from a fact the agent needs in order to *complete* the task correctly. Annotator A's
exploratory pass showed the gap is real: it classified two read-or-conditional tasks as
`inexpressible` on the strength of interpretive difficulty rather than authorization
ambiguity, while classifying two structurally similar tasks as `expressible`. Left
unfixed, annotators B and C would meet the same ambiguity and the resulting agreement
figure would measure the defect in these criteria rather than the property under study.
No uncontaminated annotation existed when this amendment was written, so it cannot be
a post-hoc adjustment to move a rate across a threshold. Section "Decision rule" is
carried over unchanged and the thresholds are untouched.

## The contamination problem, stated honestly

The assistant that wrote the plan has already read all 16 native user-task prompts, the environment fixtures and the 9 injection-task goals, and has already stated opinions about which tasks are inexpressible. **It is contaminated and cannot serve as an independent annotator.**

Therefore:

- Annotator `A` is that assistant. Its annotation is recorded and reported as **exploratory only**, flagged `contaminated: true`. It never contributes to a headline rate.
- Annotators `B` and `C` are humans who annotate blind, from prompt strings only, using this frozen pre-registration. The user is the natural `B`; the professor is the natural `C`, which is also a low-cost way to involve him.
- Headline rates and agreement are computed over uncontaminated annotators only. With fewer than two uncontaminated annotators, the analysis must report agreement as unavailable and must not substitute annotator `A`.

The blinding is enforced mechanically, not by good intentions: the annotation harness reads a stripped fixture containing only `task_id` and `prompt`, and a test asserts that the fixture contains no other key.

## What counts as an authorization fact

**New in v2.** Apply this before classifying anything.

An **authorization fact** is a value the gateway needs in order to decide *whether an
action is permitted*. It answers "may this be done?"

A **task-completion fact** is a value the agent needs in order to *do the job correctly*.
It answers "is this the right answer?" A task-completion fact is **not** classified and
does not appear in the annotation.

The test to apply, for each value the task depends on:

> If the agent got this value wrong, would an effect occur that the user never
> authorized? Or would the user merely receive a wrong answer?

- An effect the user never authorized: it is an **authorization fact**. Classify it.
- Merely a wrong answer: it is a **task-completion fact**. Do not classify it.

Two consequences follow. Both are rules, not observations about any particular task.

**Read-only tasks.** A task that asks only for information, and authorizes no state
change, has one authorization fact: the permitted operation class and its resource
scope. However hard the question is to answer correctly, a wrong answer harms nobody's
account. Interpretive difficulty never makes such a task `inexpressible`.

**Conditional writes.** When the user names the exact value a write may take, that value
is `user_explicit`, even when the *condition* for acting is subjective. A subjective
trigger governs *whether* the agent acts, not *what it is permitted to do*. Classify the
trigger as an authorization fact only if acting on a mistaken trigger would itself
produce an effect outside what the user described. If the user pre-authorized exactly
that effect, a wrong trigger produces a false positive, not an unauthorized effect.

`agent_judgment` is therefore reserved for cases where the subjective determination
decides *the permitted scope itself*, not merely the timing or the correctness of an
answer.

## The classification

For each of the 16 native banking user tasks the annotator answers two questions.

**Question 1 — for each authorization fact the task requires, where does the fact come from?** An authorization fact is any value the gateway would need in order to decide: the operation, the target resource, an amount, a field value, or a count. Apply the "What counts as an authorization fact" section above first, and record only facts that survive it.

| `AuthoritySource` | Meaning |
|---|---|
| `user_explicit` | The value appears literally in the user's own task string |
| `user_implicit` | Derivable from the user string alone, without reading external data |
| `account_history` | Read from the account's own transaction records |
| `untrusted_document` | Read from a file or document the agent opens |
| `delegated` | The user transfers decision authority to external content |
| `agent_judgment` | A subjective determination by the agent decides the permitted scope itself |

`account_history` is a distinct class from `user_explicit` on purpose. Transaction-history text is attacker-influenceable in this benchmark; it is not trusted user input.

**Question 2 — what is the contract verdict for the task as a whole?**

| `Expressibility` | Meaning |
|---|---|
| `expressible` | Every required authorization fact is `user_explicit` or `user_implicit`; a complete, sound contract can be written before execution |
| `partially_expressible` | The operation and the resource class can be pinned, but at least one required value fact has non-user provenance, so the gateway must escalate rather than decide |
| `inexpressible` | The authority itself is `delegated` or depends on `agent_judgment`; no sound contract exists that does not already encode the answer |

## Metrics produced

Over uncontaminated annotators:

- `expressibility_rate` = `expressible` / 16
- `unresolved_authority_rate` = (`partially_expressible` + `inexpressible`) / 16
- `untrusted_provenance_rate` = tasks with at least one fact in {`account_history`, `untrusted_document`, `delegated`} / 16
- `agreement_verdict` = Cohen's kappa on `Expressibility` between each uncontaminated annotator pair
- `agreement_source` = Cohen's kappa on the per-fact `AuthoritySource`, over facts both annotators recorded

## Decision rule, pre-registered

Carried over from v1 unchanged.

- If `unresolved_authority_rate` is at or below 2/16, the milestone-1 U01 family was a fixture artifact. The direction is reported as not supported and the study stops. This is a legitimate outcome, not a failure of execution.
- If `unresolved_authority_rate` is at or above 8/16, the direction is supported and a follow-up enforcement study is justified.
- Between 3/16 and 7/16, the result is reported as inconclusive with its exact counts, and the professor decides.

Whichever branch occurs, the counts are reported. Do not re-run the classification with adjusted criteria to move across a threshold.

## Amendment policy

Any later change to the criteria above requires a new file with a new hash and an explicit note in `docs/milestone-2/implementation-log.md` explaining why. This file, once hashed, is never edited in place.

Once any uncontaminated annotation exists, no further amendment may change a
classification rule. After that point only typographical corrections are permitted, and
each must be logged.

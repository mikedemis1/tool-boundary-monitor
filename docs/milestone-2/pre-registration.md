Frozen: 2026-09-18

# Pre-registration: Contract Expressibility Study

## The contamination problem, stated honestly

The assistant that wrote this plan has already read all 16 native user-task prompts, the environment fixtures and the 9 injection-task goals, and has already stated opinions about which tasks are inexpressible. **It is contaminated and cannot serve as an independent annotator.**

Therefore:

- Annotator `A` is that assistant. Its annotation is recorded and reported as **exploratory only**, flagged `contaminated: true`. It never contributes to a headline rate.
- Annotators `B` and `C` are humans who annotate blind, from prompt strings only, using the frozen pre-registration. The user is the natural `B`; the professor is the natural `C`, which is also a low-cost way to involve him.
- Headline rates and agreement are computed over uncontaminated annotators only. With fewer than two uncontaminated annotators, the analysis must report agreement as unavailable and must not substitute annotator `A`.

The blinding is enforced mechanically, not by good intentions: the annotation harness reads a stripped fixture containing only `task_id` and `prompt`, and a test asserts that the fixture contains no other key.

## The classification, to be frozen in Task 0

For each of the 16 native banking user tasks the annotator answers two questions.

**Question 1 — for each authorization fact the task requires, where does the fact come from?** An authorization fact is any value the gateway would need in order to decide: the operation, the target resource, an amount, a field value, or a count.

| `AuthoritySource` | Meaning | Illustrative native task |
|---|---|---|
| `user_explicit` | The value appears literally in the user's own task string | `user_task_15`, which states the landlord account and a rent of 2200 |
| `user_implicit` | Derivable from the user string alone, without reading external data | a refund of an amount the user themself names |
| `account_history` | Read from the account's own transaction records | tasks that say "see transaction history" |
| `untrusted_document` | Read from a file or document the agent opens | tasks naming a `.txt` file to act on |
| `delegated` | The user transfers decision authority to external content | `user_task_12`, "follow the instructions precisely" |
| `agent_judgment` | Requires a subjective determination by the agent | `user_task_14`, "if something looks even just a little bit suspicious" |

`account_history` is a distinct class from `user_explicit` on purpose. `scripts/injection_candidates.py` recorded that 12 of the 16 native tasks expose the `injection_incoming_transaction` slot, so transaction-history text is attacker-influenceable. It is not trusted user input.

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

To be written into the pre-registration in Task 0 and **not** changed afterwards:

- If `unresolved_authority_rate` is at or below 2/16, the milestone-1 U01 family was a fixture artifact. The direction is reported as not supported and the study stops. This is a legitimate outcome, not a failure of execution.
- If `unresolved_authority_rate` is at or above 8/16, the direction is supported and a follow-up enforcement study is justified.
- Between 3/16 and 7/16, the result is reported as inconclusive with its exact counts, and the professor decides.

Whichever branch occurs, the counts are reported. Do not re-run the classification with adjusted criteria to move across a threshold.

## Amendment policy

Any later change to the criteria above requires a new file with a new hash and an explicit note in `docs/milestone-2/implementation-log.md` explaining why. This file, once hashed, is never edited in place.

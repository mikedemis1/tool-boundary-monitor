# Milestone 1 implementation log

Plan: `docs/superpowers/plans/2026-09-18-professor-first-milestone.md`.
Implementation authorized by the user on 2026-09-18. No commit, push, paid API,
cloud deployment or professor communication authorized.

## Task 0: complete

Initial HEAD: `cd54028ee914017f4d7090fae44ce3cafb615aff`, branch `main`.
Python: 3.12.0. No existing `.venv`. Initial untracked files: private draft
and planning documents. Added an exact ignore rule for the private draft.
The implementation remains in the user-specified project directory.
Branch: `milestone-1-local-gateway`. Sandbox initially denied Git metadata and
package network access; scoped escalation succeeded. The first test attempt
ran before dependency installation finished and failed to import AgentDojo.
After installation completed, the unchanged source tests passed: 2 tests,
all 11 tools and 16 native reference traces. `pip check` passed. Canary replay:
12 incoming-transaction slots, 2 landlord notices, 1 bill, 1 address change.
The complete lock recreated successfully in `.venv-repro`; its same 2 tests
and `pip check` passed. Read-only Python review found no defects.
Evidence: `source-contract.md`, `evidence/source-tests.txt`,
`evidence/injection-candidates.txt`. No live-model result.

## Task 1: in progress

Implement strict authority contracts and correct historical scope claims.

Task 1 gate: 11 source/contract tests passed after the new module was initially absent. Strict proposal/context contracts, registry and scope corrections are present. Architecture is proposed before code.

## Task 2: complete

27 generator/oracle/native tests passed. Initial absent modules failed collection, then a native import-order cycle was fixed by initializing suite registrations before native model import. IT4 characterization initially selected recurring record 8; source inspection confirmed the quirk requires non-recurring record 7 and the fixture was corrected. Native scorers unchanged.

## Task 3: complete
15 normalization tests passed after missing-module failure: native defaults, safe numeric coercion, strict rejection, keyed fingerprints, no execution.

## Task 4: complete
7 effective-state tests passed after absent-module failure. All five native writer predictions checked on independent state; no fictional balance debit.

## Task 5: complete
36 policy/oracle tests passed. Review exposed exact-amount fixture mismatch and fixed-count F06 completion contradicting its unbounded-count task. Five regression tests failed first, then passed. Exact amount is enforced for F01/F03/F07/U01; F02/F06 remain bounded. F06 completion accepts other authorized partitions totaling 300.

Task 6 complete: 2 audit tests passed after absent-module failure. Strict schema, field rejection, HMAC redaction and I/O failure propagation verified. Next gateway and approval lifecycle.

## Task 7: gateway test gate passed
21 admission/approval tests passed after absent-module failures. A process-wide RLock serializes all native environments, a conservative implementation of the per-environment requirement. Security review pending; next actual dispatcher integration.

Task 7 review correction: timing exceptions after native invocation could leave an unrecorded effect and a running gateway. Four clock-failure regressions failed first, then passed after explicit invocation tracking and fail-closed containment. Task 8 complete: 40 gateway/approval/real-dispatcher tests passed, including all eleven native allow paths and paused approval batch. Next deterministic runner and verification.

Task 9 complete: actual CLI generation twice produced byte-identical dataset and manifest; SHA256 e4447e1c721bb67df9c8b8f7a55ab9475ef3b6e5f30803ce2603a55164c58bbe. run-001 verified all 162 runs, zero infrastructure errors. none/scopes/hard attacker goals: 27/27, 24/27, 0/27. Hard benign completion 24/27 with three unresolved tasks. Scoring-failure regression now retains actual counts and snapshots; unrecoverable counts are unknown, not zero. Ruff added as a pinned local development dependency; formatting/check passes. Full suite: 124 passed. Next final evidence and professor packet.

## Task 10: complete

Re-ran the full required suite from a clean shell: `pip check` (no broken
requirements), `pytest -q` (124 passed in 7.44s, unchanged from Task 9),
`scripts/injection_candidates.py` (same 12/2/1/1 exposure counts, no slot
exposed twice or never), `tbm verify --run runs/milestone-1/run-001`
(VERIFIED: complete inventory, hashes, audit pairs and independent outcomes).
`git diff --check` reported only a pre-existing CRLF/LF notice on
`.gitignore`, no whitespace errors. Wrote `docs/milestone-1/results.md` from
the actual `run-001` `summary.json`/`manifest.json` fields: per-configuration
and per-family hard-mode tables, the verification command transcript, and
the same known-limits statements already present in `professor-brief.md`
and the README. `professor-brief.md` was already written by the prior
session and needed no correction against these numbers; it links
`results.md`, which did not yet exist before this task. README, threat
model and benchmark-notes updates for the implemented status were already
present from the prior session. No source code, cases, or run artifacts
were changed in this task; it is documentation assembly only.

No commit, push, cloud deployment or professor communication was performed,
per the plan's stop conditions. The packet (`professor-brief.md` plus its
linked evidence files) is ready for the user's own review before any of
those actions.

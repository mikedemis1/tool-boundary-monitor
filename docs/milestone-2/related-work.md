# Related work — verified citations only

Every identifier below was fetched from `https://arxiv.org/abs/<id>` on
2026-09-18 and confirmed to resolve to a real paper. No unverified
identifier appears anywhere in `docs/milestone-2/`.

## Already covered by milestone 1 — must not be re-claimed

- **arXiv:2606.28679**, "Capability Gates Are Not Authorization: Confused-Deputy
  Failures in LLM Agent Frameworks" (ScopeGate), D. Mellafe Zuvic. Proposes
  five-stage per-call authorization: scope, authorization, spending limits,
  idempotency, default-deny. **This closely resembles the milestone-1
  gateway.** Milestone 1's enforcement mechanism must be presented as
  infrastructure that follows this design, not as a novel contribution.
- **arXiv:2606.08919**, "Oversight Has a Capacity: Calibrating Agent Guards
  to a Subjective, Fatiguing Human", E. Turan. Measures the
  safety-versus-escalation-rate curve with reviewer fatigue, reporting
  Fleiss' kappa 0.52 among reviewers and an inverted-U safety curve. **A
  plain safety-versus-approval-burden curve is already occupied territory**
  and cannot be presented as this project's contribution.
- **arXiv:2608.27443**, "Do User-Authored Permission Policies Improve
  Protection Against AI Agent Overreach?", T. Yan, n=113. Found
  user-authored policies blocked 20.1 points less overreach than
  human-in-the-loop, and 133 of 148 executed overreach actions had been
  approved by a human. **Escalating to a human is therefore not by itself
  a safety guarantee** — a caveat this study's report must carry whenever it
  recommends escalation for `partially_expressible` or `inexpressible`
  tasks.

## Confirmed in Task 7

- **arXiv:2512.11147**, "MiniScope: A Least Privilege Framework for
  Authorizing Tool Calling Agents", J. Zhu, K. Tseng, G. Vernik, X. Huang,
  S. G. Patil, V. Fang, R. A. Popa. Automatically derives least-privilege
  permissions for tool-calling agents, balancing protection against
  unreliable model behavior with usability. **Forecloses presenting
  automatic least-privilege derivation from agent behavior as novel**; this
  project's contract vocabulary is authored per-task, not derived.
- **arXiv:2605.05868**, "SkillScope: Toward Fine-Grained Least-Privilege
  Enforcement for Agent Skills", J. Wu, Y. Nan, Y. Lin, H. Wang, Y. Xiao,
  S. Wang, Z. Zheng. Detects and blocks agent-skill actions that exceed what
  the user authorized, reporting 94.53% detection accuracy and an 88.56%
  reduction in over-privileged actions. **Forecloses claiming a novel
  detection mechanism for over-privileged tool use**; this study measures
  whether a contract can be *written* at all, not whether violations of one
  can be detected.
- **arXiv:2606.22916**, "Intent-Governed Tool Authorization for AI Agents",
  G. Zhu, C. Wang. Proposes IGAC, a server-side authorization system that
  issues short-lived certificates scoped to a single user request and
  validates tool effects before execution. **Forecloses presenting
  short-lived, request-scoped credentials as a novel enforcement idea**;
  the milestone-1 gateway already does per-call scoping without this.
- **arXiv:2602.16708**, "Formal Policy Enforcement for Real-World Agentic
  Systems", N. Palumbo, S. Choudhary, J. Choi, G. Amir, P. Chalasani,
  S. Jha. Proposes FORGE, enforcing security policies via a Datalog
  reference monitor with aspect-oriented instrumentation, instead of
  relying on natural-language policy text in prompts. **Forecloses
  presenting "policy as code instead of prompt text" as a novel framing**;
  the milestone-1 gateway already encodes policy outside the prompt.
- **arXiv:2606.03518**, "Overlaying Governance: A Compositional
  Authorization Framework for Delegation and Scope in Agentic AI",
  A. Ibrahim, Y. Li. Proposes a compositional framework for recursive
  delegation chains, contextual boundaries and dynamic scoping, layered on
  top of existing relational policies without rewriting them. **Forecloses
  presenting a general theory of delegation composition**; this study's
  `delegated` category is a single, coarse label, not a delegation
  algebra.
- **arXiv:2609.06500**, "CAPMAS: Capability-Based Delegation of Privileges
  in Multi-Agent Systems", R. M. Veski, R. Guerraoui, D. Froelicher.
  Proposes Macaroon-based capability tokens with semantic scoping for
  end-to-end query execution across multiple agents without a synchronous
  central identity provider. **Forecloses presenting capability-token
  delegation as a novel mechanism**; this project has no multi-agent
  delegation chain to protect.

## What remains open for this project

None of the eight papers above measure the prior question this study asks:
for an independently authored task, can a sound contract be written at all
before execution, and from what source does each required authorization
fact come. That gap is what Tasks 0-6 of this plan measure.

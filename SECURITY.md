# Security

## What this repository is

Research on where authorisation belongs when an LLM agent calls tools. It is a
threat model and, as the gateway lands, an implementation and an evaluation. It
is not a product and should not be put in front of anything that matters.

## Reporting something

Open an issue, or use GitHub's private vulnerability reporting if the finding
should not be public first.

Two kinds of report are especially useful:

- A bypass of the authorisation boundary the gateway claims to hold. That is the
  whole point of the project, and a working bypass is worth more to it than a
  passing test.
- An error in the threat model. It makes claims about AgentDojo's banking suite
  that were read out of its source, and source moves.

## What is already known

- The gateway defends one specific boundary: whether a proposed tool call is
  permitted, given the actor, the action, the resource and the arguments. It
  does not stop prompt injection, and any claim in this repository that sounds
  like it does is a bug in the writing.
- Model output and tool return values are treated as untrusted and cannot change
  policy. That is the design; if you find a path where they can, that is the
  bypass described above.
- The evaluation runs against simulated tools and a fixed set of episodes. It
  measures a deterministic tool boundary, not attack success against a live
  model, and the numbers are labelled that way.
- Three scoring defects in the AgentDojo benchmark are documented in
  `docs/benchmark-notes.md`. They are the benchmark's, not this project's, and
  are excluded or corrected explicitly where results depend on them.

## Dependencies

Pinned where they affect results, because an evaluation that cannot be
reproduced is an anecdote.

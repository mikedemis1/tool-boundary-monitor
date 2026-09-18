# Scope and feedback mapping

The professor requested a threat model, exact inline architecture and automatically
generated local benign/attack cases first. Full cloud deployment follows stability
of the event schema and detector. This milestone implements those initial artifacts.

IAM/task authorization already appears in draft Sections 3 and 4. Trusted fixture
identity, scopes and task bounds make that foundation executable. Authentication,
automatic intent extraction and live-model security are not implemented claims.
Making authorization fidelity the central paper contribution remains a later
research decision; this foundation also supports the original hybrid design.

Native banking has eleven tools, without account freezing or export endpoints.
Rate and sequence fields remain null, not measured benign scores. Provenance means
observed tool-result sources, not causal model influence. Original scorers stay
unchanged; task-specific semantic outcomes are separate.

MITRE metadata is descriptive: ATLAS prompt injection, D3FEND Access Mediation,
and ATT&CK only when a scenario warrants an exact mapping. No MITRE API participates
in execution and a mapping is not evidence of prevention or novelty.

References: https://atlas.mitre.org/techniques/AML.T0051,
https://d3fend.mitre.org/technique/d3f:AccessMediation/,
https://attack.mitre.org/tactics/TA0010/.

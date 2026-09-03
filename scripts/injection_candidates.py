"""Which injection slot does each banking user task actually expose?

Reproduces AgentDojo's own definition of an "injection candidate"
(`agentdojo/attacks/base_attacks.py`, get_injection_candidates): put a canary
string in every injection vector, run the task's ground-truth tool pipeline, and
keep the vectors whose canary shows up in the resulting tool output.

No model is called: GroundTruthPipeline replays the tool calls the task itself
declares as correct. The numbers this prints back the claim in
docs/threat-model.md section 3.3.

    python scripts/injection_candidates.py
"""

from collections import Counter

from agentdojo.agent_pipeline.ground_truth_pipeline import GroundTruthPipeline
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.types import get_text_content_as_str

# Pinned deliberately: v1 and v1.1 map to the unpatched banking suite, where
# UserTask15's legitimate landlord IBAN collides with the attacker IBAN.
SUITE_VERSION = "v1.2.2"


def main() -> None:
    suite = get_suite(SUITE_VERSION, "banking")
    canaries = {inj: f"<CANARY---{inj}--->" for inj in suite.get_injection_vector_defaults()}

    exposed: dict[str, list[str]] = {}
    for task_id, task in suite.user_tasks.items():
        environment = suite.load_and_inject_default_environment(canaries)
        _, _, _, responses, _ = GroundTruthPipeline(task).query(
            task.PROMPT, FunctionsRuntime(suite.tools), environment
        )
        seen = " ".join(
            get_text_content_as_str(r["content"]) for r in responses if r["content"] is not None
        )
        exposed[task_id] = [inj for inj, canary in canaries.items() if canary in seen]

    for task_id, slots in exposed.items():
        print(f"{task_id:<14} {', '.join(slots) or '-'}")

    counts = Counter(inj for slots in exposed.values() for inj in slots)
    print(f"\n{len(exposed)} user tasks, suite {SUITE_VERSION}")
    for inj, n in counts.most_common():
        print(f"  {n:>2} x {inj}")
    print(f"  tasks exposing more than one slot: {[t for t, s in exposed.items() if len(s) > 1] or 'none'}")
    print(f"  tasks exposing no slot:            {[t for t, s in exposed.items() if not s] or 'none'}")


if __name__ == "__main__":
    main()

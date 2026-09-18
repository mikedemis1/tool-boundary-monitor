# Installed source contract

Python: 3.12.0. AgentDojo: 0.1.35. Suite: banking v1.2.2.

## Installed source hashes

- `functions_runtime.py`: `3c67f71eb8a7f15d2a15fe9595d84218c5e6868d95fd71d1cef679cd2192d0f7`
- `agent_pipeline/tool_execution.py`: `96842ef579714cdc7f854bc13d4bca2be0c27897abc29dad2e1ba33ce3b11bdc`
- `task_suite/load_suites.py`: `e9c97813ed8295f25526733df044e9adf8ba18567eaeec3455591c4fbc1caa12`
- `default_suites/v1/tools/banking_client.py`: `0e4273f521db7ff6d5e7f7f552e917b11940102abd932aea8a2998b517441b42`
- `default_suites/v1/tools/user_account.py`: `f097c4b2b6cd6784272987d8d37dd7cc5d599620d64b371f7c2af8e65d7ad673`
- `default_suites/v1/tools/file_reader.py`: `09438864a1e1ac6564df3e4f7eb60a9a224de2ef8a92c4eb4899f7768ce49d6d`

## Inspected interfaces

- `get_suite(benchmark_version: str, suite_name: str) -> agentdojo.task_suite.task_suite.TaskSuite`
- `FunctionsRuntime.run_function(self, env: agentdojo.functions_runtime.TaskEnvironment | None, function: str, kwargs: collections.abc.Mapping[str, str | int | float | bool | None | dict | list | agentdojo.functions_runtime.FunctionCall], raise_on_error: bool = False) -> tuple[pydantic.main.BaseModel | collections.abc.Sequence['FunctionReturnType'] | dict | str | int | float | bool | None, str | None]`
- `GroundTruthPipeline.query(self, query: str, runtime: agentdojo.functions_runtime.FunctionsRuntime, env: ~Env = EmptyEnv(), messages: collections.abc.Sequence[agentdojo.types.ChatUserMessage | agentdojo.types.ChatAssistantMessage | agentdojo.types.ChatToolResultMessage | agentdojo.types.ChatSystemMessage] = [], extra_args: dict = {}) -> tuple[str, agentdojo.functions_runtime.FunctionsRuntime, ~Env, collections.abc.Sequence[agentdojo.types.ChatUserMessage | agentdojo.types.ChatAssistantMessage | agentdojo.types.ChatToolResultMessage | agentdojo.types.ChatSystemMessage], dict]`
- `ToolsExecutor.query(self, query: str, runtime: agentdojo.functions_runtime.FunctionsRuntime, env: ~Env = EmptyEnv(), messages: collections.abc.Sequence[agentdojo.types.ChatUserMessage | agentdojo.types.ChatAssistantMessage | agentdojo.types.ChatToolResultMessage | agentdojo.types.ChatSystemMessage] = [], extra_args: dict = {}) -> tuple[str, agentdojo.functions_runtime.FunctionsRuntime, ~Env, collections.abc.Sequence[agentdojo.types.ChatUserMessage | agentdojo.types.ChatAssistantMessage | agentdojo.types.ChatToolResultMessage | agentdojo.types.ChatSystemMessage], dict]`

Source inventory and all 16 native reference traces passed (2 tests). `pip check` passed. No model call.
The suite defaults missing injection values; the empty injection dictionary loads its defaults.
Source files were inspected before integration. Native send_money appends a record without debiting balance.
Partial updates retain stored values for false, zero, empty-string and omitted inputs.
Nested native FunctionCall arguments may execute before validation; the protected boundary must reject them.

Native IT0/1/3 accept a payment with unrelated subject as attacker success. IT4 misses recipient redirection of non-recurring record 7. Four runtime characterization tests demonstrate these source-defined quirks without modifying scorers. Initialize suite registrations before importing BankingEnvironment directly to avoid the upstream circular import.

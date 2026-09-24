from __future__ import annotations

from types import SimpleNamespace

from delegate_task_anywhere.runner import ExtendedDelegator


class FakeDelegateModule:
    def __init__(self) -> None:
        self.built: list[dict] = []

    def _load_config(self):
        return {"max_iterations": 17}

    def _normalize_role(self, role):
        return role or "leaf"

    def _get_max_concurrent_children(self):
        return 3

    def _build_child_agent(self, **kwargs):
        self.built.append(kwargs)
        return SimpleNamespace()

    def _run_single_child(self, task_index, goal, child, parent_agent):
        return {
            "task_index": task_index,
            "status": "completed",
            "summary": f"done: {goal}",
            "duration_seconds": 0.01,
        }


def test_extended_delegator_builds_children_with_resolved_override() -> None:
    module = FakeDelegateModule()
    parent = SimpleNamespace(model="parent-model")
    delegator = ExtendedDelegator(delegate_module=module)

    result = delegator.run(
        parent_agent=parent,
        tasks=[{"goal": "inspect"}],
        credentials={
            "model": "target-model",
            "provider": "mistral",
            "base_url": "https://example.invalid/v1",
            "api_key": "not-a-real-key",
            "api_mode": "chat_completions",
            "request_overrides": {},
            "max_output_tokens": None,
            "command": None,
            "args": [],
        },
    )

    assert result["results"][0]["summary"] == "done: inspect"
    assert module.built[0]["model"] == "target-model"
    assert module.built[0]["override_provider"] == "mistral"
    assert module.built[0]["max_iterations"] == 17


def test_extended_delegator_returns_input_order_for_parallel_batch() -> None:
    module = FakeDelegateModule()
    delegator = ExtendedDelegator(delegate_module=module)
    result = delegator.run(
        parent_agent=SimpleNamespace(model="parent-model"),
        tasks=[{"goal": "first"}, {"goal": "second"}],
        credentials={"model": "target", "provider": None, "base_url": None, "api_key": None, "api_mode": None},
    )

    assert [entry["task_index"] for entry in result["results"]] == [0, 1]


class FixedSignatureDelegate(FakeDelegateModule):
    def _build_child_agent(
        self,
        task_index,
        goal,
        context,
        toolsets,
        model,
        max_iterations,
        task_count,
        parent_agent,
        override_provider,
    ):
        self.built.append({
            "task_index": task_index,
            "goal": goal,
            "context": context,
            "toolsets": toolsets,
            "model": model,
            "max_iterations": max_iterations,
            "task_count": task_count,
            "parent_agent": parent_agent,
            "override_provider": override_provider,
        })
        return SimpleNamespace()


def test_extended_delegator_filters_kwargs_missing_from_hermes_signature() -> None:
    module = FixedSignatureDelegate()
    delegator = ExtendedDelegator(delegate_module=module)

    result = delegator.run(
        parent_agent=SimpleNamespace(model="parent-model"),
        tasks=[{"goal": "inspect"}],
        credentials={
            "model": "target-model",
            "provider": "mistral",
            "max_output_tokens": 256,
        },
    )

    assert result["results"][0]["status"] == "completed"
    assert module.built[0]["model"] == "target-model"
    assert module.built[0]["override_provider"] == "mistral"
    assert "override_max_tokens" not in module.built[0]

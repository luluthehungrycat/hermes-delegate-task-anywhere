from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from delegate_task_anywhere.tools import handle_delegate_task_anywhere


class FakeExtendedDelegator:
    def __init__(self) -> None:
        self.received = None

    def run(self, *, parent_agent, tasks, credentials):
        self.received = {"parent_agent": parent_agent, "tasks": tasks, "credentials": credentials}
        return {"results": [{"task_index": 0, "status": "completed", "summary": "ok"}]}


def test_handler_uses_native_delegate_for_plain_requests() -> None:
    captured = {}

    def native(args, kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return '{"native": true}'

    result = handle_delegate_task_anywhere(
        {"goal": "ordinary task"}, parent_agent=SimpleNamespace(provider="mistral"), native_dispatch=native
    )

    assert result == '{"native": true}'
    assert captured["args"] == {"goal": "ordinary task"}


def test_handler_fails_closed_for_cross_profile_without_allowlist(tmp_path: Path) -> None:
    (tmp_path / "profiles" / "coder").mkdir(parents=True)
    result = handle_delegate_task_anywhere(
        {"goal": "x", "model": "target", "provider": "mistral", "profile": "coder"},
        parent_agent=SimpleNamespace(provider="mistral"),
        hermes_root=tmp_path,
        policy_config={},
    )

    assert "not allowlisted" in json.loads(result)["error"]


def test_handler_rejects_profile_without_provider() -> None:
    result = handle_delegate_task_anywhere(
        {"goal": "x", "model": "small", "profile": "coder"},
        parent_agent=SimpleNamespace(provider="mistral"),
    )

    assert "profile override requires an explicit provider" in json.loads(result)["error"]


def test_handler_uses_target_profile_cli_to_load_its_prompt_and_toolsets(tmp_path: Path) -> None:
    (tmp_path / "profiles" / "coder").mkdir(parents=True)
    calls = {}

    def cli_fallback(**kwargs):
        calls.update(kwargs)
        return {"ok": True, "backend": "cli", "result": "profile loaded"}

    result = handle_delegate_task_anywhere(
        {"goal": "review", "model": "target-model", "provider": "mistral", "profile": "coder"},
        parent_agent=SimpleNamespace(provider="parent-provider"),
        hermes_root=tmp_path,
        policy_config={"allowed_profiles": ["coder"], "allowed_providers": ["mistral"]},
        cli_fallback=cli_fallback,
    )

    assert json.loads(result)["backend"] == "cli"
    assert calls["profile"] == "coder"
    assert calls["model"] == "target-model"


def test_handler_rejects_plugin_delegation_at_native_depth_limit(tmp_path: Path) -> None:
    (tmp_path / "profiles" / "coder").mkdir(parents=True)
    parent = SimpleNamespace(provider="parent-provider", _delegate_depth=1)

    result = handle_delegate_task_anywhere(
        {"goal": "nested", "model": "target", "provider": "mistral", "profile": "coder"},
        parent_agent=parent,
        hermes_root=tmp_path,
        policy_config={
            "allowed_profiles": ["coder"],
            "allowed_providers": ["mistral"],
            "max_spawn_depth": 1,
        },
        credential_resolver=lambda **kwargs: {"model": kwargs["model"], "provider": kwargs["provider"]},
        extended_delegator=FakeExtendedDelegator(),
    )

    assert "depth limit" in json.loads(result)["error"]


def test_handler_uses_cli_fallback_without_parent_context(tmp_path: Path) -> None:
    (tmp_path / "profiles" / "coder").mkdir(parents=True)
    calls = {}

    def cli_fallback(**kwargs):
        calls.update(kwargs)
        return {"ok": True, "backend": "cli", "result": "done"}

    result = handle_delegate_task_anywhere(
        {"goal": "fallback", "model": "target", "provider": "mistral", "profile": "coder"},
        hermes_root=tmp_path,
        policy_config={
            "allowed_profiles": ["coder"],
            "allowed_providers": ["mistral"],
            "max_spawn_depth": 1,
        },
        cli_fallback=cli_fallback,
    )

    assert json.loads(result)["backend"] == "cli"
    assert calls["profile"] == "coder"
    assert calls["model"] == "target"


def test_handler_does_not_cli_fallback_after_started_error(tmp_path: Path) -> None:
    (tmp_path / "profiles" / "coder").mkdir(parents=True)
    fallback_called = False

    class StartedFailure:
        def run(self, **kwargs):
            raise RuntimeError("child execution failed after start")

    def cli_fallback(**kwargs):
        nonlocal fallback_called
        fallback_called = True
        return {"ok": True}

    result = handle_delegate_task_anywhere(
        {"goal": "no duplicate", "model": "target", "provider": "mistral"},
        parent_agent=SimpleNamespace(_delegate_depth=0),
        hermes_root=tmp_path,
        policy_config={"allowed_profiles": ["default"], "allowed_providers": ["mistral"]},
        credential_resolver=lambda **kwargs: {"model": kwargs["model"], "provider": kwargs["provider"]},
        extended_delegator=StartedFailure(),
        cli_fallback=cli_fallback,
    )

    assert "child execution failed after start" in json.loads(result)["error"]
    assert fallback_called is False

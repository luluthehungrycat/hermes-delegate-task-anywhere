from __future__ import annotations

import subprocess

from delegate_task_anywhere.cli_fallback import run_cli_fallback
from delegate_task_anywhere.depth import DEPTH_ENV, current_depth, validate_depth


def test_named_profile_cli_fallback_preserves_toolsets_and_propagates_depth() -> None:
    captured = {}

    def runner(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(argv, 0, stdout="child result\n", stderr="")

    result = run_cli_fallback(
        profile="coder",
        provider="mistral",
        model="target-model",
        tasks=[{"goal": "inspect"}],
        role="leaf",
        depth=0,
        runner=runner,
        environ={"PATH": "/usr/bin"},
    )

    assert result["backend"] == "cli"
    assert result["result"] == "child result"
    assert captured["argv"] == [
        "hermes", "--profile", "coder", "chat", "--provider", "mistral",
        "--model", "target-model", "-Q", "-q", '{"tasks": [{"goal": "inspect"}], "role": "leaf", "delegation_depth": 1}',
    ]
    assert captured["kwargs"]["env"][DEPTH_ENV] == "1"
    assert captured["kwargs"]["shell"] is False if "shell" in captured["kwargs"] else True


def test_default_profile_cli_fallback_uses_leaf_tool_allowlist() -> None:
    captured = {}

    def runner(argv, **kwargs):
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout="child result\n", stderr="")

    run_cli_fallback(
        profile="default",
        provider="mistral",
        model="target-model",
        tasks=[{"goal": "inspect"}],
        role="leaf",
        depth=0,
        runner=runner,
        environ={"PATH": "/usr/bin"},
    )

    assert captured["argv"][8:10] == [
        "-t",
        "web,browser,terminal,file,vision,image_gen,tts,skills,todo,memory,context_engine,session_search,clarify,code_execution,cronjob,homeassistant,spotify,computer_use",
    ]


def test_depth_uses_propagated_environment_when_no_parent() -> None:
    assert current_depth(None, {DEPTH_ENV: "2"}) == 2


def test_depth_rejects_at_configured_limit() -> None:
    try:
        validate_depth(None, config={"max_spawn_depth": 1}, environ={DEPTH_ENV: "1"})
    except ValueError as exc:
        assert "depth limit" in str(exc)
    else:
        raise AssertionError("expected depth limit rejection")

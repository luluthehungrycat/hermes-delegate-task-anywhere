"""Isolated Hermes CLI fallback for compatibility failures."""
from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .depth import DEPTH_ENV

# Generic toolsets for the default-profile fallback only. Named profiles keep
# their configured toolsets, which exclude delegation unless explicitly enabled.
LEAF_TOOLSETS = (
    "web", "browser", "terminal", "file", "vision", "image_gen",
    "tts", "skills", "todo", "memory", "context_engine", "session_search",
    "clarify", "code_execution", "cronjob", "homeassistant", "spotify",
    "computer_use",
)


class CLIExecutionError(RuntimeError):
    """Raised when the isolated Hermes CLI cannot produce a result."""


def run_cli_fallback(
    *,
    profile: str,
    provider: str,
    model: str,
    tasks: list[dict[str, Any]],
    role: str | None,
    depth: int,
    timeout_seconds: int = 300,
    executable: str = "hermes",
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Run a target-profile one-shot agent without placing credentials in argv."""
    prompt = json.dumps(
        {"tasks": tasks, "role": role, "delegation_depth": depth + 1},
        ensure_ascii=False,
    )
    argv = [
        executable,
        "--profile", profile,
        "chat",
        "--provider", provider,
        "--model", model,
    ]
    # Preserve an explicit named profile's SOUL.md and configured toolsets.
    # The default profile still uses the generic leaf allowlist to avoid
    # recursively exposing the plugin to its own fallback child.
    if profile == "default":
        argv.extend(["-t", ",".join(LEAF_TOOLSETS)])
    argv.extend(["-Q", "-q", prompt])
    child_env = dict(environ or os.environ)
    child_env[DEPTH_ENV] = str(depth + 1)
    child_env["DELEGATE_TASK_ANYWHERE_BACKEND"] = "cli"

    try:
        completed = runner(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=child_env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CLIExecutionError(
            f"CLI fallback timed out after {timeout_seconds}s"
        ) from exc
    except OSError as exc:
        raise CLIExecutionError(f"CLI fallback could not start Hermes: {exc}") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise CLIExecutionError(
            f"CLI fallback exited with status {completed.returncode}"
            + (f": {detail[-1000:]}" if detail else "")
        )

    return {
        "ok": True,
        "backend": "cli",
        "profile": profile,
        "provider": provider,
        "model": model,
        "result": (completed.stdout or "").strip(),
        "depth": depth + 1,
    }

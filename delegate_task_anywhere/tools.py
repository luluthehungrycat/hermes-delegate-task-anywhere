"""Handler for policy-controlled cross-model and cross-profile delegation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .cli_fallback import CLIExecutionError, run_cli_fallback
from .credentials import (
    CredentialResolutionError,
    resolve_provider_credentials,
    resolve_target_profile,
)
from .depth import validate_depth
from .policy import DelegationPolicy, PolicyError
from .runner import CompatibilityError, ExtendedDelegator


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def _root_from_runtime() -> Path:
    from hermes_constants import get_process_hermes_home

    home = get_process_hermes_home()
    return home.parent.parent if home.parent.name == "profiles" else home


def _plugin_policy_config() -> dict[str, Any]:
    try:
        from hermes_cli.config import load_config_readonly

        config = load_config_readonly() or {}
        return ((config.get("plugins") or {}).get("entries") or {}).get("delegate-task-anywhere", {}) or {}
    except Exception:
        return {}


def _policy_with_defaults(config: Mapping[str, Any] | None) -> DelegationPolicy:
    """Fail closed for credential-bound profile selection unless operator opts in."""
    effective = dict(config or {})
    # A separately installed plugin must not discover every profile by default.
    # The default profile is the only implicit target; named profiles require an
    # explicit allowed_profiles entry in config.yaml.
    effective.setdefault("allowed_profiles", ["default"])
    return DelegationPolicy.from_mapping(effective)


def _native_dispatch(args: dict[str, Any], kwargs: Mapping[str, Any]) -> str:
    from tools.registry import registry

    return registry.dispatch("delegate_task", args, **dict(kwargs))


def _tasks(args: Mapping[str, Any]) -> list[dict[str, Any]]:
    batch = args.get("tasks")
    if isinstance(batch, list) and batch:
        return [dict(item) for item in batch if isinstance(item, Mapping)]
    goal = args.get("goal")
    if isinstance(goal, str) and goal.strip():
        return [{"goal": goal, "context": args.get("context"), "role": args.get("role")}]
    raise ValueError("Provide either 'goal' or a non-empty 'tasks' list")


def handle_delegate_task_anywhere(
    args: dict[str, Any],
    *,
    parent_agent: Any = None,
    native_dispatch: Callable[[dict[str, Any], Mapping[str, Any]], str] = _native_dispatch,
    hermes_root: Path | None = None,
    policy_config: Mapping[str, Any] | None = None,
    credential_resolver: Callable[..., dict[str, Any]] = resolve_provider_credentials,
    extended_delegator: ExtendedDelegator | None = None,
    cli_fallback: Callable[..., dict[str, Any]] | None = None,
    **kwargs: Any,
) -> str:
    """Prefer native in-process delegation and fall back before dispatch starts."""
    model = args.get("model")
    provider = args.get("provider")
    profile = args.get("profile")
    has_override = any(value for value in (model, provider, profile))
    if not has_override:
        passthrough = {
            key: value
            for key, value in args.items()
            if key in {"goal", "context", "tasks", "role", "background"}
        }
        return native_dispatch(passthrough, {"parent_agent": parent_agent, **kwargs})

    if not isinstance(model, str) or not model.strip():
        return _error("Extended delegation requires a non-empty model")
    if not isinstance(provider, str) or not provider.strip():
        if profile:
            return _error("A profile override requires an explicit provider so its credentials are unambiguous")
        return _error("Extended delegation requires an explicit provider")

    effective_config = policy_config if policy_config is not None else _plugin_policy_config()
    root = hermes_root or _root_from_runtime()
    target_profile = str(profile or "default")
    try:
        target_home = resolve_target_profile(root, target_profile)
        policy = _policy_with_defaults(effective_config)
        policy.validate(profile=target_profile, provider=provider.strip(), model=model.strip())
        tasks = _tasks(args)
        policy.validate_batch_size(len(tasks))
        depth, _ = validate_depth(parent_agent, config=effective_config)

        fallback = cli_fallback or run_cli_fallback
        # A named profile owns its SOUL.md and toolsets. The native in-process
        # helper inherits the caller's prompt/tool capabilities, so it cannot
        # faithfully execute a profile-specific role. Use an isolated CLI turn
        # for explicit profile selection; retain the native fast path for
        # provider/model-only overrides.
        if parent_agent is None or target_profile != "default":
            result = fallback(
                profile=target_profile,
                provider=provider.strip(),
                model=model.strip(),
                tasks=tasks,
                role=args.get("role"),
                depth=depth,
            )
            return json.dumps(result, ensure_ascii=False)

        try:
            credentials = credential_resolver(
                profile_home=target_home, provider=provider.strip(), model=model.strip()
            )
            result = (extended_delegator or ExtendedDelegator()).run(
                parent_agent=parent_agent, tasks=tasks, credentials=credentials
            )
            return json.dumps({"ok": True, "backend": "in_process", **result}, ensure_ascii=False)
        except (CredentialResolutionError, CompatibilityError):
            # These failures occur before a child is started. Runtime failures
            # after .run() begins are deliberately not caught here, preventing
            # duplicate work through an automatic retry.
            result = fallback(
                profile=target_profile,
                provider=provider.strip(),
                model=model.strip(),
                tasks=tasks,
                role=args.get("role"),
                depth=depth,
            )
            return json.dumps(result, ensure_ascii=False)
    except (PolicyError, CredentialResolutionError, CompatibilityError, CLIExecutionError, ValueError) as exc:
        return _error(str(exc))
    except Exception as exc:
        return _error(str(exc))

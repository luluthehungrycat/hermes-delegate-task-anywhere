"""Best-effort plugin-side parent-agent compatibility patch.

This deliberately patches only the registry object at runtime. It does not
modify Hermes source files and is safe to skip when the active runtime does not
expose a live agent (notably some gateway paths); the handler then uses its CLI
fallback.
"""
from __future__ import annotations

from typing import Any

_INSTALLED = False
_ORIGINAL_DISPATCH = None


def _find_active_agent(ctx: Any) -> Any:
    manager = getattr(ctx, "_manager", None)
    cli = getattr(manager, "_cli_ref", None) if manager is not None else None
    agent = getattr(cli, "agent", None) if cli is not None else None
    if agent is not None:
        return agent
    # Some Hermes hosts expose the agent directly on plugin context.
    return getattr(ctx, "agent", None)


def install_runtime_patch(ctx: Any) -> bool:
    """Inject the live CLI agent for this plugin when Hermes exposes one."""
    global _INSTALLED, _ORIGINAL_DISPATCH
    if _INSTALLED:
        return True

    try:
        from tools.registry import registry
    except Exception:
        return False

    original = registry.dispatch

    def dispatch(name: str, args: dict, **kwargs: Any):
        if name == "delegate_task_anywhere" and kwargs.get("parent_agent") is None:
            parent = _find_active_agent(ctx)
            if parent is not None:
                kwargs["parent_agent"] = parent
        return original(name, args, **kwargs)

    registry.dispatch = dispatch
    _ORIGINAL_DISPATCH = original
    _INSTALLED = True
    return True

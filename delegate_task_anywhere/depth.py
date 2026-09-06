"""Depth policy shared by in-process and CLI delegation backends."""
from __future__ import annotations

import os
from typing import Any, Mapping

from .policy import PolicyError

DEPTH_ENV = "DELEGATE_TASK_ANYWHERE_DEPTH"
DEFAULT_MAX_SPAWN_DEPTH = 1


def _native_max_spawn_depth() -> int:
    """Read Hermes' configured native limit without importing private code at import time."""
    try:
        from tools.delegate_tool import _get_max_spawn_depth

        return max(1, int(_get_max_spawn_depth()))
    except Exception:
        return DEFAULT_MAX_SPAWN_DEPTH


def max_spawn_depth(config: Mapping[str, Any] | None = None) -> int:
    """Return the operator's native limit, with a test/config override."""
    if config and config.get("max_spawn_depth") is not None:
        try:
            return max(1, int(config["max_spawn_depth"]))
        except (TypeError, ValueError) as exc:
            raise PolicyError("delegation.max_spawn_depth must be an integer") from exc
    return _native_max_spawn_depth()


def current_depth(parent_agent: Any = None, environ: Mapping[str, str] | None = None) -> int:
    """Get depth from the live parent, or the propagated CLI environment marker."""
    if parent_agent is not None:
        raw = getattr(parent_agent, "_delegate_depth", 0)
    else:
        raw = (environ or os.environ).get(DEPTH_ENV, "0")
    try:
        depth = int(raw)
    except (TypeError, ValueError) as exc:
        raise PolicyError(f"{DEPTH_ENV} must be an integer") from exc
    if depth < 0:
        raise PolicyError(f"{DEPTH_ENV} cannot be negative")
    return depth


def validate_depth(parent_agent: Any = None, *, config: Mapping[str, Any] | None = None,
                   environ: Mapping[str, str] | None = None) -> tuple[int, int]:
    """Reject at the same boundary as native delegate_task, returning depth/limit."""
    depth = current_depth(parent_agent, environ)
    limit = max_spawn_depth(config)
    if depth >= limit:
        raise PolicyError(
            f"Delegation depth limit reached (depth={depth}, max_spawn_depth={limit})"
        )
    return depth, limit

"""Compatibility adapter around Hermes' native child-agent primitives."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib
import time
from typing import Any, Mapping


class CompatibilityError(RuntimeError):
    """Raised when the installed Hermes delegation internals are incompatible."""


_REQUIRED_HELPERS = (
    "_load_config",
    "_normalize_role",
    "_get_max_concurrent_children",
    "_build_child_agent",
    "_run_single_child",
)


def load_delegate_module() -> Any:
    """Load and validate the native delegation internals used by this plugin."""
    try:
        module = importlib.import_module("tools.delegate_tool")
    except ImportError as exc:  # pragma: no cover - guarded by smoke test
        raise CompatibilityError("Hermes native delegation module is unavailable") from exc
    missing = [name for name in _REQUIRED_HELPERS if not callable(getattr(module, name, None))]
    if missing:
        raise CompatibilityError(
            "Installed Hermes is incompatible with delegate-task-anywhere; "
            f"missing native helpers: {', '.join(missing)}"
        )
    return module


class ExtendedDelegator:
    """Build native child agents using trusted, plugin-resolved credentials."""

    def __init__(self, *, delegate_module: Any | None = None) -> None:
        self._delegate = delegate_module or load_delegate_module()

    def run(
        self,
        *,
        parent_agent: Any,
        tasks: list[Mapping[str, Any]],
        credentials: Mapping[str, Any],
    ) -> dict[str, Any]:
        if parent_agent is None:
            raise CompatibilityError("Extended delegation requires a parent agent context")
        if not tasks:
            raise ValueError("Provide at least one task")

        config = self._delegate._load_config()
        max_iterations = int(config.get("max_iterations", 50))
        max_children = int(self._delegate._get_max_concurrent_children())
        if len(tasks) > max_children:
            raise ValueError(
                f"Too many tasks: {len(tasks)} provided, but Hermes permits {max_children}"
            )

        parent_tool_names = self._save_parent_tool_names()
        children: list[tuple[int, Mapping[str, Any], Any]] = []
        try:
            for index, task in enumerate(tasks):
                goal = str(task.get("goal") or "").strip()
                if not goal:
                    raise ValueError(f"Task {index} is missing a goal")
                role = self._delegate._normalize_role(task.get("role"))
                child = self._delegate._build_child_agent(
                    task_index=index,
                    goal=goal,
                    context=task.get("context"),
                    toolsets=None,
                    model=credentials.get("model"),
                    max_iterations=max_iterations,
                    task_count=len(tasks),
                    parent_agent=parent_agent,
                    override_provider=credentials.get("provider"),
                    override_base_url=credentials.get("base_url"),
                    override_api_key=credentials.get("api_key"),
                    override_api_mode=credentials.get("api_mode"),
                    override_request_overrides=credentials.get("request_overrides"),
                    override_max_tokens=credentials.get("max_output_tokens"),
                    override_acp_command=credentials.get("command"),
                    override_acp_args=credentials.get("args"),
                    role=role,
                )
                child._delegate_saved_tool_names = parent_tool_names
                children.append((index, task, child))
        finally:
            self._restore_parent_tool_names(parent_tool_names)

        started = time.monotonic()
        if len(children) == 1:
            index, task, child = children[0]
            results = [self._delegate._run_single_child(index, task["goal"], child, parent_agent)]
        else:
            results = []
            with ThreadPoolExecutor(max_workers=min(len(children), max_children)) as executor:
                futures = {
                    executor.submit(self._delegate._run_single_child, index, task["goal"], child, parent_agent): index
                    for index, task, child in children
                }
                for future in as_completed(futures):
                    index = futures[future]
                    try:
                        results.append(future.result())
                    except Exception as exc:
                        results.append(
                            {
                                "task_index": index,
                                "status": "error",
                                "summary": None,
                                "error": str(exc),
                                "duration_seconds": 0,
                            }
                        )
            results.sort(key=lambda item: item["task_index"])

        return {"results": results, "total_duration_seconds": round(time.monotonic() - started, 2)}

    @staticmethod
    def _save_parent_tool_names() -> list[str] | None:
        try:
            model_tools = importlib.import_module("model_tools")
            return list(getattr(model_tools, "_last_resolved_tool_names", []))
        except Exception:
            return None

    @staticmethod
    def _restore_parent_tool_names(names: list[str] | None) -> None:
        if names is None:
            return
        try:
            model_tools = importlib.import_module("model_tools")
            model_tools._last_resolved_tool_names = names
        except Exception:
            return

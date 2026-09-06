from __future__ import annotations

import importlib.util
from pathlib import Path


def test_plugin_registers_a_distinct_tool() -> None:
    plugin_path = Path(__file__).parents[1] / "__init__.py"
    spec = importlib.util.spec_from_file_location("plugin_under_test", plugin_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    calls = []

    class Context:
        def register_tool(self, **kwargs):
            calls.append(kwargs)

    module.register(Context())

    assert calls[0]["name"] == "delegate_task_anywhere"
    assert calls[0]["toolset"] == "delegate_task_anywhere"
    assert "profile" in calls[0]["schema"]["parameters"]["properties"]
    assert calls[0]["override"] is False

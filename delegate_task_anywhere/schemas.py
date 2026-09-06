"""Schema for the standalone cross-model/profile delegation tool."""

DELEGATE_TASK_ANYWHERE = {
    "name": "delegate_task_anywhere",
    "description": (
        "Delegate work to an explicitly selected, operator-allowlisted Hermes profile, "
        "provider, and model. Use only when a task needs a different model or profile. "
        "For ordinary delegation with the configured default, use delegate_task instead. "
        "A profile override requires an explicit provider."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Single self-contained task goal."},
            "context": {"type": "string", "description": "Context required to complete the task."},
            "tasks": {
                "type": "array",
                "description": "Independent tasks to run in parallel under the same routing override.",
                "items": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "context": {"type": "string"},
                        "role": {"type": "string", "enum": ["leaf", "orchestrator"]},
                    },
                    "required": ["goal"],
                },
            },
            "model": {"type": "string", "description": "Target model. Required for this extended tool."},
            "provider": {"type": "string", "description": "Target provider. Required for this extended tool."},
            "profile": {
                "type": "string",
                "description": "Target Hermes profile holding the provider credentials; defaults to default.",
            },
            "role": {"type": "string", "enum": ["leaf", "orchestrator"]},
        },
        "required": [],
    },
}

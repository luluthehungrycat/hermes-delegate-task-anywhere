"""Policy validation for cross-profile delegation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class PolicyError(ValueError):
    """Raised when a requested delegation exceeds operator policy."""


@dataclass(frozen=True)
class DelegationPolicy:
    allowed_profiles: frozenset[str] | None
    allowed_providers: frozenset[str] | None
    allowed_models: frozenset[str] | None
    max_concurrent_children: int

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any] | None) -> "DelegationPolicy":
        config = config or {}

        def strings(key: str) -> frozenset[str] | None:
            raw = config.get(key)
            if raw is None:
                return None
            # `hermes config set key '[a, b]'` stores the literal as a string
            # on current releases. Accept that operator-facing form as well as
            # a native YAML list, without evaluating arbitrary text.
            if isinstance(raw, str):
                value = raw.strip()
                if value.startswith("[") and value.endswith("]"):
                    raw = [part.strip().strip("'\"") for part in value[1:-1].split(",")]
            if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
                raise PolicyError(f"{key} must be a list of strings")
            return frozenset(item.strip() for item in raw if item.strip())

        raw_limit = config.get("max_concurrent_children", 3)
        try:
            limit = max(1, int(raw_limit))
        except (TypeError, ValueError) as exc:
            raise PolicyError("max_concurrent_children must be an integer") from exc
        return cls(strings("allowed_profiles"), strings("allowed_providers"), strings("allowed_models"), limit)

    def validate(self, *, profile: str | None, provider: str | None, model: str | None) -> None:
        if profile and self.allowed_profiles is not None and profile not in self.allowed_profiles:
            raise PolicyError(f"Profile '{profile}' is not allowlisted for delegate_task_anywhere")
        if provider and self.allowed_providers is not None and provider not in self.allowed_providers:
            raise PolicyError(f"Provider '{provider}' is not allowlisted for delegate_task_anywhere")
        if model and self.allowed_models is not None and model not in self.allowed_models:
            raise PolicyError(f"Model '{model}' is not allowlisted for delegate_task_anywhere")

    def validate_batch_size(self, task_count: int) -> None:
        if task_count > self.max_concurrent_children:
            raise PolicyError(
                f"Too many tasks: {task_count} provided, but policy permits {self.max_concurrent_children}"
            )

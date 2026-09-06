"""Profile path and provider credential resolution helpers."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class CredentialResolutionError(ValueError):
    """Raised when a selected profile or provider cannot be resolved safely."""


def resolve_target_profile(hermes_home: Path, profile: str | None) -> Path:
    """Resolve a profile to its Hermes home and fail closed if it is absent."""
    selected = (profile or "default").strip()
    if selected in {"", "default"}:
        return hermes_home
    if Path(selected).name != selected or selected in {".", ".."}:
        raise CredentialResolutionError("Profile must be a simple profile name")
    target = hermes_home / "profiles" / selected
    if not target.is_dir():
        raise CredentialResolutionError(f"Requested Hermes profile does not exist: {selected}")
    return target


@contextmanager
def hermes_home_override(profile_home: Path) -> Iterator[None]:
    """Temporarily scope Hermes config resolution without mutating process env."""
    try:
        from hermes_constants import reset_hermes_home_override, set_hermes_home_override
    except ImportError as exc:  # pragma: no cover - exercised by compatibility smoke test
        raise CredentialResolutionError("Installed Hermes lacks profile override support") from exc
    token = set_hermes_home_override(profile_home)
    try:
        yield
    finally:
        reset_hermes_home_override(token)


def resolve_provider_credentials(*, profile_home: Path, provider: str, model: str) -> dict[str, Any]:
    """Use Hermes' provider resolver under the selected profile's config scope."""
    try:
        from hermes_cli.runtime_provider import resolve_runtime_provider
    except ImportError as exc:  # pragma: no cover
        raise CredentialResolutionError("Installed Hermes lacks runtime provider resolution") from exc

    with hermes_home_override(profile_home):
        try:
            runtime = resolve_runtime_provider(requested=provider, target_model=model)
        except Exception as exc:
            raise CredentialResolutionError(
                f"Cannot resolve provider '{provider}' for the selected profile: {exc}"
            ) from exc
    if not runtime.get("api_key"):
        raise CredentialResolutionError(
            f"Provider '{provider}' resolved for the selected profile but has no API key"
        )
    return {
        "model": model,
        "provider": runtime.get("provider") or provider,
        "base_url": runtime.get("base_url"),
        "api_key": runtime.get("api_key"),
        "api_mode": runtime.get("api_mode"),
        "request_overrides": dict(runtime.get("request_overrides") or {}),
        "max_output_tokens": runtime.get("max_output_tokens"),
        "command": runtime.get("command"),
        "args": list(runtime.get("args") or []),
    }

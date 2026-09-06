from __future__ import annotations

from pathlib import Path

import pytest

from delegate_task_anywhere.credentials import CredentialResolutionError, resolve_target_profile
from delegate_task_anywhere.policy import DelegationPolicy, PolicyError


def test_policy_rejects_profile_not_in_allowlist() -> None:
    policy = DelegationPolicy.from_mapping(
        {"allowed_profiles": ["default", "coder"], "allowed_providers": ["mistral"]}
    )

    with pytest.raises(PolicyError, match="not allowlisted"):
        policy.validate(profile="researcher", provider="mistral", model="mistral-small")


def test_policy_rejects_provider_not_in_allowlist() -> None:
    policy = DelegationPolicy.from_mapping(
        {"allowed_profiles": ["default"], "allowed_providers": ["mistral"]}
    )

    with pytest.raises(PolicyError, match="not allowlisted"):
        policy.validate(profile="default", provider="openrouter", model="x")


def test_policy_accepts_hermes_config_set_list_strings() -> None:
    policy = DelegationPolicy.from_mapping(
        {"allowed_profiles": "[default, coder]", "allowed_providers": "[mistral, opencode-go]"}
    )

    policy.validate(profile="coder", provider="opencode-go", model="x")


def test_target_profile_requires_existing_directory(tmp_path: Path) -> None:
    with pytest.raises(CredentialResolutionError, match="does not exist"):
        resolve_target_profile(tmp_path, "coder")


def test_target_profile_maps_default_and_named_profile(tmp_path: Path) -> None:
    (tmp_path / "profiles" / "coder").mkdir(parents=True)

    assert resolve_target_profile(tmp_path, "default") == tmp_path
    assert resolve_target_profile(tmp_path, "coder") == tmp_path / "profiles" / "coder"


def test_policy_limits_batch_size() -> None:
    policy = DelegationPolicy.from_mapping({"max_concurrent_children": 2})

    with pytest.raises(PolicyError, match="Too many tasks"):
        policy.validate_batch_size(3)

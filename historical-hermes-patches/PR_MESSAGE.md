# PR: Add `model`/`provider`/`profile` parameters to `delegate_task`

## Problem

`delegate_task` inherits the parent's model unconditionally. The internal `_build_child_agent()` function already accepts `model`, `override_provider`, `override_base_url`, `override_api_key`, and `override_api_mode` parameters — but these are only populated from `delegation.*` in `config.yaml`, never from the tool call itself.

The tool description currently warns users: *"Subagent model is NOT selectable per call: children inherit the parent model (plus its fallback chain) unless you pin all subagents to a model via delegation.provider / delegation.model in config.yaml."*

This is a known limitation, not a design constraint — the plumbing exists, only the schema and handler logic are missing.

## Changes

Three additions to `tools/delegate_tool.py`, all backward-compatible (108 insertions, 0 deletions):

### 1. Schema params (3 new optional parameters in `DELEGATE_TASK_SCHEMA`)

- `model` — override the subagent's model per-call (e.g. `mimo-v2-5-pro`, `qwen-3.7-plus`)
- `provider` — override the provider per-call (e.g. `opencode-go`, `openrouter`, `anthropic`)
- `profile` — use a specific Hermes profile's credentials (e.g. `coder`, `dr-k`)

### 2. `_resolve_per_call_credentials()` helper

Delegates to Hermes' canonical `resolve_runtime_provider()` from `hermes_cli.runtime_provider` — the same path the CLI and gateway use at startup. This handles **all** officially configured providers without maintaining a separate env-var keymap.

Key design:
- `provider` defaults to `None` (inherit from parent), **not** a hardcoded default — fully provider-agnostic
- When `provider` is `None`, returns model-only override; the child inherits the parent's default provider and credentials
- When `provider` is set, resolves the full credential bundle (API key, base URL, API mode) via `resolve_runtime_provider()`
- Raises a clear `ValueError` with a user-friendly message on resolution failure

### 3. Threading in `delegate_task()`

When `model` is passed as a tool argument, it overrides the config-driven credential resolution so the child agent uses the specified model/provider with resolved credentials.

## Usage

```python
# Before (unchanged — still works):
delegate_task(goal="...")  
# → child inherits parent's model

# After (new — omit provider to inherit parent's provider):
delegate_task(
    goal="Complex multi-file refactoring",
    model="mimo-v2-5-pro",
)
# → child uses MiMo V2.5 Pro on parent's provider

# Or specify both:
delegate_task(
    goal="Research paper summary",
    model="qwen-3.7-plus",
    provider="openrouter",
)
```

## Testing

- All existing tests pass (no behavior change when params omitted — 100% backward compatible)
- Tested in isolated Podman container with fresh Hermes install
- Verified: schema params present, credential resolution via `resolve_runtime_provider()` works, both tools register, `_build_child_agent()` accepts overrides
- Clean regenerated patch; applies to current `main` (commit ecc672585)

## Checklist

- [x] Backward compatible — omitting `model`/`provider`/`profile` behaves identically to current code
- [x] Config-driven delegation (delegation.model in config.yaml) still works as before
- [x] No hardcoded default provider — `None` = inherit from parent
- [x] Provider-agnostic — uses `resolve_runtime_provider()` which supports all Hermes providers
- [x] In-process child builder — same ThreadPoolExecutor, same progress callbacks

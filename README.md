# delegate-task-anywhere

A standalone Hermes Agent plugin that adds `delegate_task_anywhere`: in-process subagent delegation to an explicitly selected Hermes **profile**, **provider**, and **model**.

It intentionally does **not** override Hermes' built-in `delegate_task`.

- Use native `delegate_task` for ordinary work.
- Use `delegate_task_anywhere` only when a named model/profile is needed.
- The plugin uses Hermes' native child-agent primitives through a narrow compatibility adapter, preserving isolated contexts, inherited tool capabilities, and terminal sessions.

## Security model

Cross-profile delegation is fail-closed:

- `default` is the only implicitly allowed profile.
- Named profiles require an explicit `allowed_profiles` entry.
- Unknown profile names are errors; they never silently fall back to `default`.
- A profile override requires a provider override, so target credentials are unambiguous.
- Provider/model allowlists are supported. Credentials are resolved from the target profile; no API keys appear in tool arguments.

## Install

### From GitHub (recommended)

After publishing the repository, Hermes can clone and register the directory plugin directly:

```bash
hermes plugins install <owner>/hermes-plugin-delegate-task-anywhere --enable
```

For example, if published from Mo's personal account:

```bash
hermes plugins install luluthehungrycat/hermes-plugin-delegate-task-anywhere --enable
```

`hermes plugins update delegate-task-anywhere` subsequently pulls the configured Git remote. No Python package entry point is required for this directory-plugin route.

### Local checkout / development

Clone or symlink this repository into the active profile's plugin directory:

```bash
ln -sfn /path/to/hermes-plugin-delegate-task-anywhere \
  ~/.hermes/plugins/delegate-task-anywhere
```

Enable it in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - delegate-task-anywhere
  entries:
    delegate-task-anywhere:
      allowed_profiles: [default, coder, researcher]
      allowed_providers: [mistral, openrouter, opencode-go]
      # Optional exact model allowlist:
      # allowed_models: [mistral-small-latest, ...]
      max_concurrent_children: 3
```

Restart Hermes or start a fresh session. Inspect discovery with:

```bash
HERMES_PLUGINS_DEBUG=1 hermes plugins list
```

## Tool contract

```json
{
  "goal": "Review the authentication implementation",
  "context": "Repository: /srv/app. Run targeted tests.",
  "model": "mistral-small-latest",
  "provider": "mistral",
  "profile": "coder"
}
```

Batch tasks share one model/provider/profile override:

```json
{
  "tasks": [
    {"goal": "Review tests", "context": "..."},
    {"goal": "Review dependency risks", "context": "..."}
  ],
  "model": "mistral-small-latest",
  "provider": "mistral",
  "profile": "researcher"
}
```

## Compatibility and depth limits

The plugin uses two execution paths:

1. Provider/model-only overrides use in-process delegation through Hermes' native child-agent primitives. A plugin-side runtime patch supplies the live `parent_agent` when the active host exposes it.
2. Explicit named-profile overrides use an isolated one-shot Hermes CLI process so the selected profile's `SOUL.md`, toolsets, and configuration are loaded.
3. If the parent context or native helper API is unavailable before a child starts, it uses the same isolated CLI fallback.
4. It never retries through the CLI after in-process execution may have started, preventing duplicate work.

The fallback invokes Hermes with an argument list and propagates a private depth marker through the child environment. Credentials remain profile-resolved and are never placed in command-line arguments. For named profiles it leaves tool selection to that profile's configuration; the `default` profile uses a generic leaf tool allowlist that excludes delegation tools and this plugin.

The plugin reads Hermes' native `delegation.max_spawn_depth` setting and enforces it on both backends. This extra plugin-side check is required because the in-process compatibility adapter calls native private helpers directly, while a fresh CLI process otherwise starts with a new depth counter. `delegation.max_concurrent_children` and `delegation.max_iterations` are also reused where available.

If Hermes' internal API changes, the plugin falls back only for pre-dispatch compatibility failures. Unknown execution state is returned as an error rather than retried.

## Compatibility internals

The plugin deliberately depends on native, non-public delegation helpers. At startup/use it checks for the required functions and fails with a clear compatibility error if a Hermes update changes them.

The adapter inspects `_build_child_agent` before calling it and omits optional arguments that the installed Hermes version does not accept. This keeps the adapter compatible when Hermes changes private helper signatures (for example, removing `override_max_tokens`).

The checked integration points are:

- `tools.delegate_tool._build_child_agent`
- `tools.delegate_tool._run_single_child`
- `tools.delegate_tool._load_config`
- `tools.delegate_tool._normalize_role`
- `tools.delegate_tool._get_max_concurrent_children`
- `hermes_cli.runtime_provider.resolve_runtime_provider`
- `hermes_constants.set_hermes_home_override`

Tested against Hermes Agent `v0.21.4 (2026.9.21)`.

## Development

Run the tests from the repository root with pytest installed:

```bash
PYTHONPATH=. pytest -p no:cacheprovider
```

The tests cover policy enforcement, strict profile resolution, profile-aware fallback routing, extended-runner argument construction, and plugin registration. The plugin uses private Hermes delegation helpers, so verify it against the Hermes version you deploy.

## License

MIT

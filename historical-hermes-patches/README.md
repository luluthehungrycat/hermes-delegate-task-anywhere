# Historical Hermes source patches

This directory preserves the earlier fork-based implementation that added
per-call `model`, `provider`, and `profile` parameters to Hermes' native
`delegate_task` tool.

These files are archival provenance, not installation requirements for the
current `delegate-task-anywhere` plugin. The current plugin registers a
separate `delegate_task_anywhere` tool and adapts to upstream Hermes' existing
private child-agent helpers without modifying Hermes source files on disk.

## Preserved artifacts

- `0001-add-model-provider-profile-to-delegate_task.series.patch` — the
  recovered five-commit email-format patch series.
- `0001-full-pr-diff.patch` — the earlier single-diff form.
- `PR_MESSAGE.md` — the historical pull-request description.

The files were copied from:

```text
/home/hermes/agent/repos/hermes-patches/
```

## Historical commits and dates

The recovered series contains these commits:

1. `3513ea7b4af0871a249bf05581a0e7e9375e468b`
   - `feat(tools): add per-call model/provider/profile overrides to delegate_task`
   - Author date: 2026-07-15 14:32:51 +0200
   - Commit date: 2026-07-15 14:55:03 +0200
2. `92731807c5b0a22a36d765d91fe650e06d49a3ac`
   - follow-up implementation/tests
   - 2026-07-15 14:57:46 +0200
3. `6c2b11df9c5eab471117192148c74946d35a83e7`
   - `fix: use generic profile name in schema description`
   - 2026-07-15 16:04:06 +0200
4. `5000ea1737644dbaa04a0b5244e8bd0018596a08`
   - `fix: address OpenCode v3 review nits`
   - 2026-07-15 16:13:15 +0200
5. `9fcffb7cb9e343bf0d4ec28e84c596f4dcf41c09`
   - `feat: add delegation.allow_cross_profile config key and documentation`
   - 2026-07-15 17:04:35 +0200

An earlier related commit, `0ebcf67b26`, is referenced by the retained
project history as the initial implementation. Its exact timestamp and full
object are not present in the current Hermes checkout or retained patch
metadata, so no timestamp is invented here.

The patch repository itself was created/updated on 2026-07-08:

- `3b7a15b73ca034e023cc382fb0d58cf7502f41b2` — 2026-07-08 11:07:05 +0200
- `47d05cd229508f96bc47855407865e87d84669b9` — 2026-07-08 11:21:37 +0200

## Why these patches are retained

They document the earlier approach and preserve the exact historical diff in
case a future Hermes version exposes a compatible extension point or the
fork-based implementation needs to be reconstructed.

They are **not** automatically applied. Against the current Hermes checkout,
`git apply --check` reports context failures because `tools/delegate_tool.py`
and its tests have since changed substantially.

## Current necessity assessment

The historical Hermes patches are not required by the current plugin. The
plugin currently calls these upstream helpers through its compatibility
adapter:

- `tools.delegate_tool._build_child_agent`
- `tools.delegate_tool._run_single_child`
- `tools.delegate_tool._load_config`
- `tools.delegate_tool._normalize_role`
- `tools.delegate_tool._get_max_concurrent_children`

The current plugin-side compatibility work is located in the parent plugin
repository, notably `runtime_patch.py`, `delegate_task_anywhere/runner.py`,
and the CLI fallback modules. Those files are separate from the historical
Hermes source patches.

## Hermes worktree changes deliberately not copied

At the time of archival, `/home/hermes/.hermes/hermes-agent` had unrelated
uncommitted changes in:

- `tools/computer_use/*.py`
- `tests/tools/test_computer_use.py`
- an untracked `tools/orchestrate_tool.py`

They do not provide runtime dependencies for `delegate_task_anywhere`, so they
were not copied into this directory. Existing dirty worktree changes were
preserved and not reset or discarded.

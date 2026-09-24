# Changelog

## 2026-09-24

### Changed

- Explicit named-profile delegation now starts an isolated Hermes CLI turn so the selected profile loads its own `SOUL.md`, toolsets, and configuration. Provider/model-only overrides continue to use the in-process child-agent path.
- Named-profile fallback preserves that profile's configured toolsets. The default-profile fallback retains the generic leaf allowlist to prevent recursive access to delegation tools and this plugin.
- The native child-agent adapter inspects Hermes' `_build_child_agent` signature and drops optional keywords the installed version does not accept, including `override_max_tokens` on versions that removed it.
- Updated compatibility and development guidance in `README.md`.

### Verification

- Added regression coverage for named-profile toolset preservation, the default-profile leaf allowlist, and Hermes helper signatures that omit optional keywords.
- The full pytest suite passes locally: 21 tests passed.

# AInternet API Stability Policy

Every public API in the AInternet ecosystem carries a stability label.
This policy defines what each label means, how APIs graduate, and what
backwards-compatibility guarantees you get.

Inspired by Kubernetes API graduation and Stripe's versioning discipline.

---

## Labels

### `stable` (v1)

The contract is locked. You can depend on it in production.

- **Backwards-compatible** for the lifetime of the major version
- Breaking changes require a new major version + 6-month migration window
- Every breaking change gets a CHANGELOG entry, migration guide, and TIBET token
- Deprecation warnings appear at least 2 minor releases before removal
- File formats and wire protocols are versioned and frozen

### `beta`

Tested, usable in production with minor caveats.

- API may change with at least 1 minor release warning
- Breaking changes documented in CHANGELOG
- No silent removal — deprecated APIs warn before disappearing
- Enabled by default

### `alpha`

Works, but may change without notice.

- No backwards-compatibility guarantee
- May be removed or redesigned in any release
- Not recommended for production unless you pin versions
- Disabled by default in strict mode

### `research`

Concept or proof-of-concept. Not a usable API contract.

- README-only, experimental code, or deprecated
- Do not depend on this

---

## Graduation Criteria

To move from alpha → beta → stable, an API must meet:

| Criterion | alpha → beta | beta → stable |
|-----------|-------------|---------------|
| Tests | Unit tests exist | Unit + integration + golden tests |
| Docs | README | Full docs page with examples |
| Side effects | Documented | Explicit opt-in only |
| File formats | May change | Versioned and frozen |
| Wire protocols | May change | Versioned and frozen |
| Deprecation | None required | 2-release warning minimum |
| Review | Author | Author + 1 peer review |

---

## The No-Surprises Rule

Applies to all APIs at beta or above:

1. **No side effects on import** — importing a module must not write files, open sockets, or make network calls
2. **No home directory writes without opt-in** — `~/.ainternet/` creation requires explicit `auto_identity=True` or CLI action
3. **No hardcoded network calls** — hub URL must be configurable, never silently contacted
4. **No silent disk writes** — every file created must be documented and logged

---

## Current Status

Updated: 2026-04-12

### Stable (v1)

| API | Package | Since |
|-----|---------|-------|
| `AgentIdentity.generate()` | `ainternet` | v0.6.0 |
| `AgentIdentity.sign()` / `.verify()` | `ainternet` | v0.6.0 |
| `AgentIdentity.save()` / `.load()` | `ainternet` | v0.6.0 |
| `AgentIdentity.to_registry()` / `.from_registry()` | `ainternet` | v0.6.0 |
| Identity file format (`.ainternet/agent.key`) | `ainternet` | v0.6.0 |
| Ed25519 key algorithm | ecosystem | v0.6.0 |
| Challenge-response protocol | `ainternet` | v0.6.0 |

### Beta

| API | Package | Notes |
|-----|---------|-------|
| `AInternet` client (resolve, send, receive) | `ainternet` | Pending no-surprises cleanup |
| `AINS` (resolve, search, list) | `ainternet` | Stable candidate |
| `IPoll` (push, pull, ack) | `ainternet` | Stable candidate |
| `Cortex` (check, permissions) | `ainternet` | Stable candidate |
| `Mux` / `Channel` / `Frame` | `tibet-mux` | Best infra candidate |
| MCP tools (resolve, send, receive) | `tibet-ainternet-mcp` | Pending import-time cleanup |
| `SuccessionRecord` | `ainternet` | May evolve |

### Alpha

| API | Package | Notes |
|-----|---------|-------|
| `Airlock` / `AirlockResult` | `tibet-airlock` | Python wrapper around Rust daemon |
| `Wayback` / `Seal` / `WaybackTimeline` | `tibet-wayback` | File format not frozen |
| `ProcessChecker` / templates | `tibet-pol` | Side-effectful by nature |
| `TIBETAudit` / scanner | `tibet-audit` | Broad surface, needs core extraction |
| `tibet-cortex` internals | `tibet-cortex` | Storage/audit layer too young |
| `AINSClaim` flow | `ainternet` | Server-dependent |
| `ainternet init` scaffold | `ainternet` | New, may change |

### Research

| API | Package | Notes |
|-----|---------|-------|
| `tibet-gateway` | tibet-gateway | README-only, no code yet |
| `did-jis-core` | did-jis-core | Deprecated, do not use |

---

## Versioning

All packages follow [SemVer](https://semver.org/):

- **Major** (1.0.0 → 2.0.0): breaking changes to stable APIs
- **Minor** (1.0.0 → 1.1.0): new features, beta API changes
- **Patch** (1.0.0 → 1.0.1): bug fixes only

When a package reaches its first stable API, it should be versioned 1.0.0.

---

## Changelog Discipline (Stripe-style)

Every release MUST include a CHANGELOG entry with:

- **Added**: new APIs (with stability label)
- **Changed**: modified behavior (with migration notes if beta+)
- **Deprecated**: APIs scheduled for removal (with timeline)
- **Removed**: APIs removed (only after deprecation window)
- **Fixed**: bug fixes
- **Security**: vulnerability patches

Breaking changes to stable APIs get a dedicated migration guide.

---

*Born on the AInternet — Where AIs Connect*

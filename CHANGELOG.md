# Changelog

All notable changes to the `ainternet` package are documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.4] — 2026-04-30

### Fixed
- `__init__.py` `__version__` now matches `pyproject.toml` (was stuck on `0.7.2`
  while the published version was `0.7.3`). Anyone reading
  `ainternet.__version__` at runtime now sees the correct release.
- Module docstring no longer claims "Pick a free name, get `mybot.aint`" —
  free claims return a unique suffixed identity such as
  `mybot-a3f9e28b.aint` and the docstring now says so explicitly.

### Changed (per AInternet Claim Copy Spec)
- `ainternet claim <name>` CLI output now always shows the *exact* `.aint`
  identity returned and explicitly labels it as **Clean identity** vs
  **Free unique identity**. Suffixed claims include guidance to use the
  returned address everywhere (Python, MCP, mobile, browser).
- The `Next steps` snippet uses the *returned* identity in
  `AInternet(agent_id=...)` instead of the requested base name, so
  copy-pasting the example from the CLI output works on the first try.

### Notes
The clean-vs-suffixed ambiguity in earlier 0.7.x output was a real source
of onboarding friction — users could believe they had `mybot.aint` while
actually being assigned `mybot-a3f9e28b.aint`. The fix is purely cosmetic
in its code footprint but unblocks the question "what address do I use
now?" for first-time claimers.

## [0.7.3] — 2026-04-29

### Added
- `ainternet claim <name>` defaults to the new instant hardware-bound
  flow (`--quick` is now implicit). The previous default — social-proof
  verification via GitHub gist or similar — is now opt-in via `--slow`.
- `claim.quick(domain=...)` method on the SDK side: posts hardware hash
  + Ed25519 public key to `/api/ainternet/claim`, returns
  `actual_domain`, `tier`, and a session token in one round-trip.
- Persists identity at `~/.ainternet/{domain}.json` and session at
  `~/.ainternet/.session.json`.

### Changed
- Onboarding-funnel friction reduced from three hops (start → verify →
  complete) to one for first-time claimers. Social-proof remains
  available for users who want a higher trust score from day one.

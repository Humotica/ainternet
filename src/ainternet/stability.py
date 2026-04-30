"""
API Stability Labels
====================

Mark APIs with their stability level. Labels appear in docs,
help text, and runtime warnings.

Usage:
    from ainternet.stability import stable, beta, alpha

    @stable(since="0.6.0")
    def sign(self, data: bytes) -> bytes:
        ...

    @beta(note="pending no-surprises cleanup")
    def resolve(self, domain: str):
        ...

    @alpha
    def experimental_feature():
        ...

Stability levels:
    stable  — locked contract, backwards-compatible
    beta    — usable, may change with 1-release warning
    alpha   — works, may change without notice
"""

import functools
import warnings


# ── Decorators ───────────────────────────────────────────────────────

def stable(fn=None, *, since: str = None):
    """Mark an API as stable (v1).

    Stable APIs have a locked contract. Breaking changes require
    a new major version and 6-month migration window.

    Args:
        since: Version when this API became stable
    """
    def decorator(func):
        func._stability = "stable"
        func._stability_since = since
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._stability = "stable"
        wrapper._stability_since = since
        return wrapper

    if fn is not None:
        # Used as @stable without arguments
        return decorator(fn)
    return decorator


def beta(fn=None, *, note: str = None):
    """Mark an API as beta.

    Beta APIs are usable in production but may change with
    at least 1 minor release warning.

    Args:
        note: Optional note about what may change
    """
    def decorator(func):
        func._stability = "beta"
        func._stability_note = note
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._stability = "beta"
        wrapper._stability_note = note
        return wrapper

    if fn is not None:
        return decorator(fn)
    return decorator


def alpha(fn=None, *, note: str = None):
    """Mark an API as alpha.

    Alpha APIs may change without notice. Not recommended
    for production unless you pin versions.

    Args:
        note: Optional note about stability risks
    """
    def decorator(func):
        func._stability = "alpha"
        func._stability_note = note
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._stability = "alpha"
        wrapper._stability_note = note
        return wrapper

    if fn is not None:
        return decorator(fn)
    return decorator


def deprecated(fn=None, *, since: str = None, removal: str = None, alternative: str = None):
    """Mark an API as deprecated.

    Deprecated APIs emit a warning on use and will be removed
    after the deprecation window.

    Args:
        since: Version when deprecation started
        removal: Target version for removal
        alternative: Suggested replacement
    """
    def decorator(func):
        func._stability = "deprecated"
        func._deprecated_since = since
        func._deprecated_removal = removal
        func._deprecated_alternative = alternative

        msg_parts = [f"{func.__qualname__} is deprecated"]
        if since:
            msg_parts.append(f"since {since}")
        if removal:
            msg_parts.append(f"will be removed in {removal}")
        if alternative:
            msg_parts.append(f"use {alternative} instead")
        msg = " — ".join(msg_parts)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        wrapper._stability = "deprecated"
        wrapper._deprecated_msg = msg
        return wrapper

    if fn is not None:
        return decorator(fn)
    return decorator


# ── Introspection ────────────────────────────────────────────────────

def get_stability(obj) -> str:
    """Get the stability label of a function or class.

    Returns: "stable", "beta", "alpha", "deprecated", or "unknown"
    """
    return getattr(obj, "_stability", "unknown")


def is_stable(obj) -> bool:
    """Check if an API is marked as stable."""
    return get_stability(obj) == "stable"

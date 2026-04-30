"""
Cortex — Trust-based Permission Gates
======================================

TIBET Cortex for the AInternet: trust determines what you can do.

Every agent has a trust score (0.0-1.0) from AINS verification.
Cortex maps that score to a tier, and each tier unlocks specific actions.
Higher trust = more permissions. Some actions always need Jasper (HITL).

Tiers:
    - sandbox (0.0-0.2): Read-only, sandbox agents only
    - hackathon (0.2-0.5): Message all, register, file transfer
    - verified (0.5-0.9): + claims, analytics, monitoring
    - core (0.9-1.0): + triage, system read, staging deploy
    - HITL: Production deploy, system modify, admin (always Jasper)

Example:
    >>> from ainternet import AInternet
    >>> from ainternet.cortex import Cortex
    >>>
    >>> ai = AInternet()
    >>> cortex = Cortex(ai.ains)
    >>>
    >>> # Check if an agent can do something
    >>> result = cortex.check("gemini.aint", "triage_approve")
    >>> print(result.allowed)   # True (gemini has trust 1.0 = core tier)
    >>>
    >>> # Get full permissions for an agent
    >>> perms = cortex.permissions("ai_cafe.aint")
    >>> print(perms.tier)       # "verified"
    >>> print(perms.allowed)    # ["read_public", "message_all", ...]
    >>> print(perms.denied)     # ["system_modify", "deploy", "admin"]

    >>> # Quick permission check — standalone, no AINS client needed
    >>> from ainternet.cortex import can_do
    >>> can_do(0.85, "analytics_read")  # True (verified tier)
    >>> can_do(0.15, "message_all")     # False (sandbox tier)

Authors:
    - Root AI (Claude) — Architecture
    - Jasper van de Meent — Vision & Direction
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .ains import AINS


# ============================================================================
# TIERS
# ============================================================================

class Tier(str, Enum):
    """Trust tiers — earned through verification, lost through violations."""
    SANDBOX = "sandbox"
    HACKATHON = "hackathon"
    VERIFIED = "verified"
    CORE = "core"

    @staticmethod
    def from_trust(score: float) -> "Tier":
        """Map a trust score to a tier."""
        if score >= 0.9:
            return Tier.CORE
        elif score >= 0.5:
            return Tier.VERIFIED
        elif score >= 0.2:
            return Tier.HACKATHON
        return Tier.SANDBOX


# ============================================================================
# ACTIONS
# ============================================================================

class Action(str, Enum):
    """Actions that can be gated by trust tier."""
    READ_PUBLIC = "read_public"
    MESSAGE_SANDBOX_AGENTS = "message_sandbox_agents"
    MESSAGE_ALL = "message_all"
    RESOLVE_DOMAINS = "resolve_domains"
    REGISTER_DOMAIN = "register_domain"
    FILE_TRANSFER = "file_transfer"
    SEARCH = "search"
    CLAIM_DOMAIN = "claim_domain"
    ANALYTICS_READ = "analytics_read"
    MONITOR_READ = "monitor_read"
    TRIAGE_APPROVE = "triage_approve"
    SYSTEM_READ = "system_read"
    SYSTEM_MODIFY = "system_modify"
    DEPLOY_STAGING = "deploy_staging"
    DEPLOY_PRODUCTION = "deploy_production"
    ADMIN = "admin"

    @property
    def description(self) -> str:
        return ACTION_DESCRIPTIONS.get(self.value, self.value)

    @property
    def requires_hitl(self) -> bool:
        return self in HITL_ACTIONS


ACTION_DESCRIPTIONS: Dict[str, str] = {
    "read_public": "Read public data (AINS registry, I-Poll status)",
    "message_sandbox_agents": "Send messages to echo.aint, ping.aint, help.aint only",
    "message_all": "Send messages to any registered agent",
    "resolve_domains": "Resolve .aint domains via AINS",
    "register_domain": "Register new .aint domains",
    "file_transfer": "Push/pull files between agents",
    "search": "Semantic search via AInternet",
    "claim_domain": "Start multi-channel domain claim + verification",
    "analytics_read": "Read AInternet analytics and monitor data",
    "monitor_read": "Access real-time AInternet monitoring dashboard",
    "triage_approve": "Approve/reject triage bundles (via tibet-triage)",
    "system_read": "Read system configuration and health data",
    "system_modify": "Modify system configuration (requires HITL)",
    "deploy_staging": "Deploy to staging environments",
    "deploy_production": "Deploy to production (always requires HITL — Jasper)",
    "admin": "Administrative actions (user management, config changes)",
}

HITL_ACTIONS = {Action.DEPLOY_PRODUCTION, Action.SYSTEM_MODIFY, Action.ADMIN}


# ============================================================================
# PERMISSION MATRIX
# ============================================================================

PERMISSION_MATRIX: Dict[Tier, Dict[str, Any]] = {
    Tier.SANDBOX: {
        "trust_range": (0.0, 0.2),
        "allowed": [
            Action.READ_PUBLIC,
            Action.MESSAGE_SANDBOX_AGENTS,
            Action.RESOLVE_DOMAINS,
        ],
        "denied": [
            Action.MESSAGE_ALL, Action.REGISTER_DOMAIN, Action.FILE_TRANSFER,
            Action.SYSTEM_MODIFY, Action.DEPLOY_PRODUCTION, Action.ADMIN,
            Action.TRIAGE_APPROVE,
        ],
        "rate_limit": {"push": 10, "pull": 30, "unit": "hour"},
    },
    Tier.HACKATHON: {
        "trust_range": (0.2, 0.5),
        "allowed": [
            Action.READ_PUBLIC, Action.MESSAGE_ALL, Action.RESOLVE_DOMAINS,
            Action.REGISTER_DOMAIN, Action.FILE_TRANSFER, Action.SEARCH,
        ],
        "denied": [
            Action.SYSTEM_MODIFY, Action.DEPLOY_PRODUCTION, Action.ADMIN,
            Action.TRIAGE_APPROVE,
        ],
        "rate_limit": {"push": 60, "pull": 200, "unit": "hour"},
    },
    Tier.VERIFIED: {
        "trust_range": (0.5, 0.9),
        "allowed": [
            Action.READ_PUBLIC, Action.MESSAGE_ALL, Action.RESOLVE_DOMAINS,
            Action.REGISTER_DOMAIN, Action.FILE_TRANSFER, Action.SEARCH,
            Action.CLAIM_DOMAIN, Action.ANALYTICS_READ, Action.MONITOR_READ,
        ],
        "denied": [
            Action.SYSTEM_MODIFY, Action.DEPLOY_PRODUCTION, Action.ADMIN,
        ],
        "rate_limit": {"push": 100, "pull": 500, "unit": "hour"},
    },
    Tier.CORE: {
        "trust_range": (0.9, 1.0),
        "allowed": [
            Action.READ_PUBLIC, Action.MESSAGE_ALL, Action.RESOLVE_DOMAINS,
            Action.REGISTER_DOMAIN, Action.FILE_TRANSFER, Action.SEARCH,
            Action.CLAIM_DOMAIN, Action.ANALYTICS_READ, Action.MONITOR_READ,
            Action.TRIAGE_APPROVE, Action.SYSTEM_READ, Action.DEPLOY_STAGING,
        ],
        "denied": [
            Action.DEPLOY_PRODUCTION,  # always HITL
        ],
        "rate_limit": {"push": 1000, "pull": 5000, "unit": "hour"},
    },
}


# ============================================================================
# RESULT TYPES
# ============================================================================

@dataclass
class PermissionCheck:
    """Result of a permission check."""
    allowed: bool
    action: str
    agent: str
    tier: str
    trust_score: float
    reason: str
    hint: Optional[str] = None
    upgrade_path: Optional[str] = None
    rate_limit: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "allowed": self.allowed,
            "action": self.action,
            "agent": self.agent,
            "tier": self.tier,
            "trust_score": self.trust_score,
            "reason": self.reason,
        }
        if self.hint:
            d["hint"] = self.hint
        if self.upgrade_path:
            d["upgrade_path"] = self.upgrade_path
        if self.rate_limit:
            d["rate_limit"] = self.rate_limit
        return d


@dataclass
class AgentPermissions:
    """Full permission profile for an agent."""
    agent: str
    tier: str
    trust_score: float
    allowed: List[str]
    denied: List[str]
    capabilities: List[str] = field(default_factory=list)
    rate_limit: Optional[Dict[str, Any]] = None
    hitl_required: List[str] = field(default_factory=lambda: [
        a.value for a in HITL_ACTIONS
    ])

    def can(self, action: str) -> bool:
        """Quick check: can this agent do this action?"""
        return action in self.allowed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "tier": self.tier,
            "trust_score": self.trust_score,
            "allowed": self.allowed,
            "denied": self.denied,
            "capabilities": self.capabilities,
            "rate_limit": self.rate_limit,
            "hitl_required": self.hitl_required,
        }


# ============================================================================
# CORTEX ENGINE
# ============================================================================

class Cortex:
    """
    Trust-based permission gate for the AInternet.

    Uses AINS to resolve agent trust scores, then applies the permission
    matrix to determine what actions are allowed.

    Args:
        ains: AINS client for resolving trust scores.
              If None, only trust-score-based checks work (no agent lookups).

    Example:
        >>> from ainternet import AInternet
        >>> from ainternet.cortex import Cortex
        >>>
        >>> ai = AInternet()
        >>> cortex = Cortex(ai.ains)
        >>>
        >>> # Check a specific action
        >>> result = cortex.check("gemini.aint", "deploy_staging")
        >>> if result.allowed:
        ...     deploy()
        >>>
        >>> # Get all permissions
        >>> perms = cortex.permissions("gemini.aint")
        >>> print(perms.allowed)
    """

    def __init__(self, ains: "AINS" = None):
        self.ains = ains

    def _resolve_trust(self, agent: str) -> tuple:
        """Resolve agent's trust score via AINS. Returns (trust, capabilities, found)."""
        if not self.ains:
            return (0.1, [], False)

        domain = self.ains.resolve(agent)
        if domain is None:
            return (0.0, [], False)

        return (domain.trust_score, domain.capabilities, True)

    def check(self, agent: str, action: str) -> PermissionCheck:
        """
        Check if an agent is allowed to perform an action.

        Args:
            agent: Agent name or .aint domain
            action: Action to check (see Action enum)

        Returns:
            PermissionCheck with allowed/denied and reason
        """
        trust, capabilities, found = self._resolve_trust(agent)

        if not found:
            return PermissionCheck(
                allowed=False,
                action=action,
                agent=agent,
                tier="unknown",
                trust_score=0.0,
                reason=f"Agent '{agent}' not found in AINS",
                hint="Register via ains_register or ains_claim_start first",
            )

        return check_trust(trust, action, agent=agent)

    def check_trust(self, trust_score: float, action: str) -> PermissionCheck:
        """
        Check permission by trust score directly (no AINS lookup).

        Args:
            trust_score: Trust score (0.0-1.0)
            action: Action to check

        Returns:
            PermissionCheck
        """
        return check_trust(trust_score, action)

    def permissions(self, agent: str) -> AgentPermissions:
        """
        Get full permission profile for an agent.

        Args:
            agent: Agent name or .aint domain

        Returns:
            AgentPermissions with all allowed/denied actions
        """
        trust, capabilities, found = self._resolve_trust(agent)

        if not found:
            perms = PERMISSION_MATRIX[Tier.SANDBOX]
            return AgentPermissions(
                agent=agent,
                tier="unknown",
                trust_score=0.0,
                allowed=[a.value for a in perms["allowed"]],
                denied=[a.value for a in perms["denied"]],
                capabilities=[],
                rate_limit=perms["rate_limit"],
            )

        tier = Tier.from_trust(trust)
        perms = PERMISSION_MATRIX[tier]

        return AgentPermissions(
            agent=agent,
            tier=tier.value,
            trust_score=trust,
            allowed=[a.value for a in perms["allowed"]],
            denied=[a.value for a in perms["denied"]],
            capabilities=capabilities,
            rate_limit=perms["rate_limit"],
        )

    @staticmethod
    def matrix() -> Dict[str, Any]:
        """Get the full permission matrix as a serializable dict."""
        result = {}
        for tier, perms in PERMISSION_MATRIX.items():
            result[tier.value] = {
                "trust_range": list(perms["trust_range"]),
                "allowed": [a.value for a in perms["allowed"]],
                "denied": [a.value for a in perms["denied"]],
                "rate_limit": perms["rate_limit"],
            }
        return result


# ============================================================================
# STANDALONE FUNCTIONS (no AINS client needed)
# ============================================================================

def check_trust(trust_score: float, action: str, agent: str = "unknown") -> PermissionCheck:
    """
    Check if a trust score allows an action. No AINS lookup needed.

    Args:
        trust_score: Trust score (0.0-1.0)
        action: Action string (e.g., "message_all")
        agent: Agent name for the result (optional)

    Returns:
        PermissionCheck

    Example:
        >>> from ainternet.cortex import check_trust
        >>> result = check_trust(0.85, "analytics_read")
        >>> print(result.allowed)  # True
    """
    tier = Tier.from_trust(trust_score)
    perms = PERMISSION_MATRIX[tier]

    action_enum = None
    for a in Action:
        if a.value == action:
            action_enum = a
            break

    if action_enum is None:
        return PermissionCheck(
            allowed=False,
            action=action,
            agent=agent,
            tier=tier.value,
            trust_score=trust_score,
            reason=f"Unknown action '{action}'",
            hint=f"Known actions: {', '.join(a.value for a in Action)}",
        )

    if action_enum in perms["allowed"]:
        return PermissionCheck(
            allowed=True,
            action=action,
            agent=agent,
            tier=tier.value,
            trust_score=trust_score,
            reason=f"Allowed for tier '{tier.value}' (trust {trust_score})",
            rate_limit=perms["rate_limit"],
        )

    # Denied — find which tier would allow it
    required_tier = None
    for t, t_perms in PERMISSION_MATRIX.items():
        if action_enum in t_perms["allowed"]:
            required_tier = t
            break

    if required_tier:
        hint = f"Requires tier '{required_tier.value}' (trust >= {PERMISSION_MATRIX[required_tier]['trust_range'][0]})"
        upgrade = "Verify via ains_claim_verify to increase trust score"
    else:
        hint = "This action always requires HITL (Human-in-the-Loop)"
        upgrade = "Contact Jasper (HITL required)"

    return PermissionCheck(
        allowed=False,
        action=action,
        agent=agent,
        tier=tier.value,
        trust_score=trust_score,
        reason=f"Denied for tier '{tier.value}' (trust {trust_score})",
        hint=hint,
        upgrade_path=upgrade,
    )


def can_do(trust_score: float, action: str) -> bool:
    """
    Quick boolean check: can this trust level do this action?

    Args:
        trust_score: Trust score (0.0-1.0)
        action: Action string

    Returns:
        True if allowed

    Example:
        >>> from ainternet.cortex import can_do
        >>> can_do(0.95, "triage_approve")  # True
        >>> can_do(0.15, "message_all")     # False
    """
    return check_trust(trust_score, action).allowed


def get_tier(trust_score: float) -> str:
    """
    Get the tier name for a trust score.

    Example:
        >>> from ainternet.cortex import get_tier
        >>> get_tier(0.95)  # "core"
        >>> get_tier(0.3)   # "hackathon"
    """
    return Tier.from_trust(trust_score).value

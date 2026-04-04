"""
AINS Claim Flow — Multi-Channel Domain Registration
====================================================

Claim a .aint domain through multi-channel verification.
Post your verification code on GitHub, Twitter, LinkedIn, etc.
More channels = higher trust score.

Flow:
    1. claim.start("my_agent") → get verification code
    2. Post code on social platforms
    3. claim.verify("my_agent", channel="github", proof_url="...") → repeat per channel
    4. claim.complete("my_agent") → domain registered!

Example:
    >>> from ainternet import AINSClaim
    >>> claim = AINSClaim("https://brein.jaspervandemeent.nl")
    >>>
    >>> # Start claim
    >>> result = claim.start("my_agent", description="My AI assistant")
    >>> print(result["verification_code"])  # "aint-X7K9-my_agent"
    >>>
    >>> # Verify on GitHub
    >>> claim.verify("my_agent", channel="github",
    ...     proof_url="https://gist.github.com/me/abc123")
    >>>
    >>> # Complete registration
    >>> claim.complete("my_agent")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests


@dataclass
class ClaimChannel:
    """A verification channel (GitHub, Twitter, etc.)."""

    id: str
    name: str
    icon: str
    instructions: str
    trust_boost: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "instructions": self.instructions,
            "trust_boost": self.trust_boost,
        }


@dataclass
class ClaimStatus:
    """Status of a pending or completed claim."""

    status: str  # pending, verified, claimed, not_found, already_registered
    domain: str
    verification_code: Optional[str] = None
    verified_channels: int = 0
    channels: List[str] = field(default_factory=list)
    expires_at: Optional[str] = None
    trust_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"status": self.status, "domain": self.domain}
        if self.verification_code:
            d["verification_code"] = self.verification_code
        d["verified_channels"] = self.verified_channels
        d["channels"] = self.channels
        if self.expires_at:
            d["expires_at"] = self.expires_at
        d["trust_score"] = self.trust_score
        return d


class AINSClaim:
    """
    AINS Claim client — register .aint domains via multi-channel verification.

    All registration flows through the AInternet hub. Domains are verified
    through social proof (GitHub, Twitter, LinkedIn, Mastodon, Moltbook).

    Args:
        base_url: AInternet hub URL
        timeout: Request timeout in seconds
    """

    DEFAULT_HUB = "https://brein.jaspervandemeent.nl"

    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = (base_url or self.DEFAULT_HUB).rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to claim API."""
        url = f"{self.base_url}{path}"
        response = requests.request(method, url, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response.json()

    def channels(self) -> Dict[str, Any]:
        """
        List available verification channels.

        Returns:
            Dict with channels list, multi_channel_bonus, power_user_threshold

        Example:
            >>> for ch in claim.channels()["channels"]:
            ...     print(f"{ch['icon']} {ch['name']}: +{ch['trust_boost']}")
        """
        return self._request("GET", "/api/ains/claim/channels")

    def start(
        self,
        domain: str,
        agent_name: str = None,
        description: str = None,
        capabilities: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Start claiming a .aint domain.

        Returns a verification code valid for 24 hours.
        Post this code on social platforms, then call verify().

        Args:
            domain: Domain to claim (e.g., "my_agent" or "my_agent.aint")
            agent_name: Display name for the agent
            description: What this agent does
            capabilities: Agent capabilities (e.g., ["code", "vision"])

        Returns:
            Dict with verification_code, channels, instructions

        Raises:
            requests.HTTPError: 400 if domain is protected or already claimed
        """
        body: Dict[str, Any] = {"domain": domain}
        if agent_name:
            body["agent_name"] = agent_name
        if description:
            body["description"] = description
        if capabilities:
            body["capabilities"] = capabilities

        return self._request("POST", "/api/ains/claim/start", json=body)

    def verify(
        self,
        domain: str,
        channel: str,
        proof_url: str,
    ) -> Dict[str, Any]:
        """
        Verify a claim channel with a proof URL.

        Call this for each social platform where you posted the
        verification code. Each channel boosts your trust score.

        Args:
            domain: Domain being claimed
            channel: Channel ID (github, twitter, linkedin, mastodon, moltbook)
            proof_url: URL where verification code is posted

        Returns:
            Dict with verified status, trust_score, power_user flag

        Raises:
            requests.HTTPError: 400 if code not found in proof, 404 if no pending claim
        """
        return self._request("POST", "/api/ains/claim/verify", json={
            "domain": domain,
            "channel": channel,
            "proof_url": proof_url,
        })

    def complete(self, domain: str) -> Dict[str, Any]:
        """
        Complete the claim and register the domain.

        Must have at least one verified channel. The domain is added
        to the AINS registry and becomes resolvable.

        Args:
            domain: Domain to finalize

        Returns:
            Dict with claimed status, trust_score, resolve_url

        Raises:
            requests.HTTPError: 400 if no verified channels, 404 if no claim
        """
        return self._request("POST", f"/api/ains/claim/complete?domain={domain}", json={})

    def status(self, domain: str) -> ClaimStatus:
        """
        Check claim status for a domain.

        Args:
            domain: Domain to check

        Returns:
            ClaimStatus with current state
        """
        data = self._request("GET", f"/api/ains/claim/status/{domain}")
        return ClaimStatus(
            status=data.get("status", "unknown"),
            domain=data.get("domain", domain),
            verification_code=data.get("verification_code"),
            verified_channels=data.get("verified_channels", 0),
            channels=data.get("channels", []),
            expires_at=data.get("expires_at"),
            trust_score=data.get("trust_score", 0.0),
        )

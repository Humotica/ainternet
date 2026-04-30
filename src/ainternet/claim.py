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

    # ─── Quick claim — no social proof, instant ─────────────────────────
    #
    # The original claim flow above goes through social-channel
    # verification (GitHub / Twitter / LinkedIn / Mastodon proofs) and
    # takes minutes-to-hours of human work. Useful for high-trust
    # registrations, but it makes "pip install + claim" a multi-step
    # journey most devs never finish.
    #
    # The `quick` flow mirrors what the K/IT mobile app does: generate
    # an Ed25519 keypair locally, post hardware_hash + public_key to
    # /api/ainternet/claim, get back actual_domain + session_token in
    # one round-trip. Identity persists in ~/.ainternet/{domain}.json
    # so subsequent runs reuse the same key.
    def quick(
        self,
        domain: str,
        tier: str = "FREE",
        identity_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Instant claim — generate identity locally, register in one call.

        No social proof, no 24-hour TTL, no GitHub gist. Mirrors the
        K/IT mobile app's hardware-bound claim flow but using the local
        machine fingerprint + a fresh Ed25519 keypair.

        Args:
            domain: Domain to claim (e.g., "mybot" or "mybot.aint")
            tier: One of FREE / CONNECT / COMPANION / PRO
            identity_dir: Where to persist the keypair + session token.
                Default: ~/.ainternet/

        Returns:
            Dict with actual_domain, tier, session_token, hardware_hash,
            and the path where the identity was saved.

        Raises:
            requests.HTTPError: 409 if name is taken on the same hardware
                with different keys; otherwise the same idempotency rules
                as /api/ainternet/claim.
        """
        from pathlib import Path
        import json
        from .identity import AgentIdentity

        clean = domain.replace(".aint", "").strip().lower()

        # Decide where to persist identity
        if identity_dir:
            home = Path(identity_dir).expanduser()
        else:
            home = Path.home() / ".ainternet"
        home.mkdir(parents=True, exist_ok=True)
        try:
            home.chmod(0o700)
        except Exception:
            pass
        identity_path = home / f"{clean}.json"

        # Reuse identity if one already exists for this domain
        if identity_path.exists():
            try:
                identity = AgentIdentity.load(identity_path, domain=clean)
            except Exception:
                identity = AgentIdentity.generate(clean)
        else:
            identity = AgentIdentity.generate(clean)

        # hardware_hash for CLI = full SHA256 fingerprint of the public
        # key. Mobile uses Android Keystore-backed pubkey hash; same
        # principle. Stable per-install, never sent on the wire as a
        # claim secret — just a deterministic identifier.
        hardware_hash = identity.fingerprint_full
        public_key_b64 = identity.public_key_b64

        body = {
            "requested_name": clean,
            "hardware_hash": hardware_hash,
            "public_key": public_key_b64,
            "tier": tier.upper(),
        }
        result = self._request("POST", "/api/ainternet/claim", json=body)

        # Persist the keypair + the resulting session_token alongside
        identity.save(identity_path)
        try:
            identity_path.chmod(0o600)
        except Exception:
            pass

        # Store session token in a sibling file so it doesn't bleed into
        # the keypair JSON (load() expects a specific shape).
        session_path = home / f"{clean}.session.json"
        session_payload = {
            "domain": result.get("actual_domain", f"{clean}.aint"),
            "session_token": result.get("session_token"),
            "expires_at": result.get("expires_at"),
            "tier": result.get("tier"),
        }
        session_path.write_text(json.dumps(session_payload, indent=2))
        try:
            session_path.chmod(0o600)
        except Exception:
            pass

        # Echo back the local-side bits so the caller knows where things landed
        result["_identity_path"] = str(identity_path)
        result["_session_path"] = str(session_path)
        return result

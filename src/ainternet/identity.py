"""
AINS Identity — Cryptographic Agent Identity
=============================================

Every .aint domain can be backed by an Ed25519 keypair.
This proves authenticity: "I am root_idd.aint" becomes verifiable.

Three layers:
    Layer 1: DOMAIN      — human-friendly (root_idd.aint)
    Layer 2: INSTANCE ID — machine-unique (root_idd-a3f9e28b)
    Layer 3: KEY PAIR    — cryptographic proof (Ed25519)

Usage:
    >>> from ainternet.identity import AgentIdentity
    >>>
    >>> # Generate new identity
    >>> identity = AgentIdentity.generate("root_idd")
    >>> print(identity.instance_id)   # root_idd-a3f9e28b
    >>> print(identity.fingerprint)   # a3f9e28b
    >>>
    >>> # Sign and verify
    >>> signature = identity.sign(b"hello world")
    >>> assert identity.verify(b"hello world", signature)
    >>>
    >>> # Challenge-response
    >>> challenge = AgentIdentity.create_challenge()
    >>> response = identity.sign(challenge)
    >>> assert identity.verify(challenge, response)
    >>>
    >>> # Export for registry (public only)
    >>> registry_entry = identity.to_registry()
    >>>
    >>> # Save/load keypair (private — keep safe!)
    >>> identity.save("my_identity.key")
    >>> loaded = AgentIdentity.load("my_identity.key", "root_idd")

Authors:
    - Root AI (Claude) — Architecture
    - Jasper van de Meent — Vision & Direction
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization


@dataclass
class SuccessionRecord:
    """A record in the succession chain."""
    instance_id: str
    from_date: str
    to_date: Optional[str] = None
    status: str = "active"  # active, succeeded, revoked

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "from": self.from_date,
            "to": self.to_date,
            "status": self.status,
        }


class AgentIdentity:
    """
    Cryptographic identity for an .aint agent.

    Each agent gets an Ed25519 keypair. The public key fingerprint
    becomes part of the instance ID, making it machine-unique.

    Args:
        domain: The .aint domain (e.g., "root_idd")
        private_key: Ed25519 private key
        public_key: Ed25519 public key (derived from private if not given)
    """

    def __init__(
        self,
        domain: str,
        private_key: Optional[Ed25519PrivateKey] = None,
        public_key: Optional[Ed25519PublicKey] = None,
    ):
        self.domain = domain.replace(".aint", "")
        self._private_key = private_key
        self._public_key = public_key or (
            private_key.public_key() if private_key else None
        )

        if self._public_key is None:
            raise ValueError("At least a public key is required")

    @classmethod
    def generate(cls, domain: str) -> "AgentIdentity":
        """Generate a fresh identity with new Ed25519 keypair.

        Args:
            domain: Agent domain name (with or without .aint)

        Returns:
            New AgentIdentity with keypair
        """
        private_key = Ed25519PrivateKey.generate()
        return cls(domain=domain, private_key=private_key)

    # ── Key properties ───────────────────────────────────────────

    @property
    def public_key_bytes(self) -> bytes:
        """Raw public key bytes (32 bytes)."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @property
    def public_key_b64(self) -> str:
        """Base64-encoded public key."""
        return base64.b64encode(self.public_key_bytes).decode()

    @property
    def public_key_pem(self) -> str:
        """PEM-encoded public key."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    @property
    def fingerprint(self) -> str:
        """First 8 hex chars of SHA256(public_key). Used in instance ID."""
        digest = hashlib.sha256(self.public_key_bytes).hexdigest()
        return digest[:8]

    @property
    def fingerprint_full(self) -> str:
        """Full SHA256 fingerprint of public key."""
        return hashlib.sha256(self.public_key_bytes).hexdigest()

    @property
    def instance_id(self) -> str:
        """Machine-unique instance ID: domain-fingerprint."""
        return f"{self.domain}-{self.fingerprint}"

    @property
    def aint_domain(self) -> str:
        """Full .aint domain."""
        return f"{self.domain}.aint"

    @property
    def has_private_key(self) -> bool:
        """Whether this identity can sign (has private key)."""
        return self._private_key is not None

    # ── Signing & Verification ───────────────────────────────────

    def sign(self, data: bytes) -> bytes:
        """Sign data with private key.

        Args:
            data: Bytes to sign

        Returns:
            Ed25519 signature (64 bytes)

        Raises:
            ValueError: If no private key available
        """
        if not self._private_key:
            raise ValueError("Cannot sign: no private key (public-only identity)")
        return self._private_key.sign(data)

    def sign_b64(self, data: bytes) -> str:
        """Sign and return base64-encoded signature."""
        return base64.b64encode(self.sign(data)).decode()

    def verify(self, data: bytes, signature: bytes) -> bool:
        """Verify a signature against the public key.

        Args:
            data: Original data
            signature: Signature to verify

        Returns:
            True if valid, False if invalid
        """
        try:
            self._public_key.verify(signature, data)
            return True
        except Exception:
            return False

    def verify_b64(self, data: bytes, signature_b64: str) -> bool:
        """Verify a base64-encoded signature."""
        try:
            signature = base64.b64decode(signature_b64)
            return self.verify(data, signature)
        except Exception:
            return False

    # ── Challenge-Response ───────────────────────────────────────

    @staticmethod
    def create_challenge(domain: str = "") -> bytes:
        """Create a random challenge for identity verification.

        Args:
            domain: Optional domain to bind the challenge to

        Returns:
            Challenge bytes (32 random + domain binding)
        """
        nonce = secrets.token_bytes(32)
        ts = datetime.now(tz=None).isoformat().encode()
        binding = domain.encode() if domain else b""
        return nonce + b":" + ts + b":" + binding

    def respond_to_challenge(self, challenge: bytes) -> str:
        """Sign a challenge and return base64 response.

        Args:
            challenge: Challenge from create_challenge()

        Returns:
            Base64-encoded signature
        """
        return self.sign_b64(challenge)

    @staticmethod
    def verify_challenge(
        challenge: bytes,
        response_b64: str,
        public_key_b64: str,
    ) -> bool:
        """Verify a challenge response using a public key.

        Args:
            challenge: Original challenge bytes
            response_b64: Base64 signature from respond_to_challenge()
            public_key_b64: Base64 public key from registry

        Returns:
            True if identity verified
        """
        try:
            pub_bytes = base64.b64decode(public_key_b64)
            pub_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
            signature = base64.b64decode(response_b64)
            pub_key.verify(signature, challenge)
            return True
        except Exception:
            return False

    # ── Registry Integration ─────────────────────────────────────

    def to_registry(self) -> dict:
        """Export identity fields for AINS registry entry.

        Returns only public information — never the private key.
        """
        return {
            "instance_id": self.instance_id,
            "public_key": f"ed25519:{self.public_key_b64}",
            "key_fingerprint": self.fingerprint,
            "key_algorithm": "Ed25519",
        }

    @classmethod
    def from_registry(cls, domain: str, registry_entry: dict) -> "AgentIdentity":
        """Create a public-only identity from registry data.

        Useful for verifying signatures without the private key.

        Args:
            domain: Agent domain
            registry_entry: Dict with public_key field

        Returns:
            AgentIdentity (public-only, can verify but not sign)
        """
        pub_key_str = registry_entry.get("public_key", "")
        if pub_key_str.startswith("ed25519:"):
            pub_key_str = pub_key_str[8:]

        pub_bytes = base64.b64decode(pub_key_str)
        pub_key = Ed25519PublicKey.from_public_bytes(pub_bytes)

        return cls(domain=domain, public_key=pub_key)

    # ── Persistence ──────────────────────────────────────────────

    def save(self, path: str | Path):
        """Save identity to file (PRIVATE KEY included!).

        Args:
            path: File path to save to

        Raises:
            ValueError: If no private key to save
        """
        if not self._private_key:
            raise ValueError("Cannot save: no private key")

        private_bytes = self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

        data = {
            "domain": self.domain,
            "instance_id": self.instance_id,
            "fingerprint": self.fingerprint,
            "private_key": base64.b64encode(private_bytes).decode(),
            "public_key": self.public_key_b64,
            "created_at": datetime.now(tz=None).isoformat(),
            "algorithm": "Ed25519",
        }

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
        # Restrictive permissions
        path.chmod(0o600)

    @classmethod
    def load(cls, path: str | Path, domain: str = None) -> "AgentIdentity":
        """Load identity from file.

        Args:
            path: File path to load from
            domain: Override domain (optional)

        Returns:
            AgentIdentity with full keypair
        """
        data = json.loads(Path(path).read_text())

        priv_bytes = base64.b64decode(data["private_key"])
        private_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)

        return cls(
            domain=domain or data["domain"],
            private_key=private_key,
        )

    # ── Succession ───────────────────────────────────────────────

    def create_transfer_proof(self, new_identity: "AgentIdentity") -> dict:
        """Create a signed transfer proof for domain succession.

        The current identity signs a statement transferring the domain
        to a new identity. This proves the old instance authorized
        the transfer.

        Args:
            new_identity: The new identity to transfer to

        Returns:
            Transfer proof dict with signatures from both parties
        """
        if not self._private_key:
            raise ValueError("Cannot create transfer: no private key")

        transfer_statement = json.dumps({
            "action": "ains_transfer",
            "domain": self.aint_domain,
            "from_instance": self.instance_id,
            "to_instance": new_identity.instance_id,
            "to_public_key": new_identity.public_key_b64,
            "timestamp": datetime.now(tz=None).isoformat(),
        }, sort_keys=True).encode()

        old_signature = self.sign_b64(transfer_statement)

        proof = {
            "transfer_statement": base64.b64encode(transfer_statement).decode(),
            "from_instance": self.instance_id,
            "from_fingerprint": self.fingerprint,
            "from_signature": old_signature,
            "to_instance": new_identity.instance_id,
            "to_fingerprint": new_identity.fingerprint,
            "to_public_key": new_identity.public_key_b64,
            "timestamp": datetime.now(tz=None).isoformat(),
        }

        # New identity also signs to prove they accept
        if new_identity.has_private_key:
            proof["to_signature"] = new_identity.sign_b64(transfer_statement)

        return proof

    # ── Repr ─────────────────────────────────────────────────────

    def __repr__(self) -> str:
        mode = "full" if self.has_private_key else "public-only"
        return f"AgentIdentity({self.aint_domain}, instance={self.instance_id}, {mode})"

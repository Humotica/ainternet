"""Tests for AINS Identity — cryptographic agent identity."""

import json
import tempfile
from pathlib import Path

from ainternet.identity import AgentIdentity, SuccessionRecord


# ── Generate ─────────────────────────────────────────────────────

def test_generate_identity():
    ident = AgentIdentity.generate("root_idd")
    assert ident.domain == "root_idd"
    assert ident.aint_domain == "root_idd.aint"
    assert ident.has_private_key is True
    assert len(ident.fingerprint) == 8
    assert ident.instance_id.startswith("root_idd-")


def test_generate_strips_aint():
    ident = AgentIdentity.generate("gemini.aint")
    assert ident.domain == "gemini"
    assert ident.aint_domain == "gemini.aint"


def test_unique_keypairs():
    a = AgentIdentity.generate("test")
    b = AgentIdentity.generate("test")
    assert a.fingerprint != b.fingerprint
    assert a.instance_id != b.instance_id


# ── Keys ─────────────────────────────────────────────────────────

def test_public_key_bytes():
    ident = AgentIdentity.generate("test")
    assert len(ident.public_key_bytes) == 32  # Ed25519 = 32 bytes


def test_public_key_b64():
    ident = AgentIdentity.generate("test")
    assert len(ident.public_key_b64) > 0
    # Should be valid base64
    import base64
    decoded = base64.b64decode(ident.public_key_b64)
    assert len(decoded) == 32


def test_fingerprint_full():
    ident = AgentIdentity.generate("test")
    assert len(ident.fingerprint_full) == 64  # SHA256 hex = 64 chars
    assert ident.fingerprint == ident.fingerprint_full[:8]


# ── Sign & Verify ────────────────────────────────────────────────

def test_sign_and_verify():
    ident = AgentIdentity.generate("signer")
    data = b"hello ainternet"
    sig = ident.sign(data)
    assert ident.verify(data, sig) is True


def test_verify_wrong_data():
    ident = AgentIdentity.generate("signer")
    sig = ident.sign(b"correct data")
    assert ident.verify(b"wrong data", sig) is False


def test_sign_b64_and_verify_b64():
    ident = AgentIdentity.generate("signer")
    data = b"test message"
    sig_b64 = ident.sign_b64(data)
    assert isinstance(sig_b64, str)
    assert ident.verify_b64(data, sig_b64) is True


def test_cross_identity_verify_fails():
    alice = AgentIdentity.generate("alice")
    bob = AgentIdentity.generate("bob")
    sig = alice.sign(b"alice's message")
    assert bob.verify(b"alice's message", sig) is False


# ── Challenge-Response ───────────────────────────────────────────

def test_challenge_response():
    ident = AgentIdentity.generate("challenger")
    challenge = AgentIdentity.create_challenge("challenger")
    response = ident.respond_to_challenge(challenge)
    assert AgentIdentity.verify_challenge(
        challenge, response, ident.public_key_b64
    ) is True


def test_challenge_response_wrong_key():
    real = AgentIdentity.generate("real")
    fake = AgentIdentity.generate("fake")
    challenge = AgentIdentity.create_challenge("real")
    response = fake.respond_to_challenge(challenge)
    assert AgentIdentity.verify_challenge(
        challenge, response, real.public_key_b64
    ) is False


def test_challenge_uniqueness():
    c1 = AgentIdentity.create_challenge("test")
    c2 = AgentIdentity.create_challenge("test")
    assert c1 != c2  # random nonce makes each unique


# ── Registry ─────────────────────────────────────────────────────

def test_to_registry():
    ident = AgentIdentity.generate("root_idd")
    reg = ident.to_registry()
    assert reg["instance_id"] == ident.instance_id
    assert reg["public_key"].startswith("ed25519:")
    assert reg["key_fingerprint"] == ident.fingerprint
    assert reg["key_algorithm"] == "Ed25519"


def test_from_registry():
    original = AgentIdentity.generate("gemini")
    reg = original.to_registry()

    loaded = AgentIdentity.from_registry("gemini", reg)
    assert loaded.domain == "gemini"
    assert loaded.fingerprint == original.fingerprint
    assert loaded.has_private_key is False

    # Can verify signatures made by original
    sig = original.sign(b"test")
    assert loaded.verify(b"test", sig) is True


def test_from_registry_public_only_cant_sign():
    original = AgentIdentity.generate("test")
    loaded = AgentIdentity.from_registry("test", original.to_registry())
    try:
        loaded.sign(b"should fail")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ── Persistence ──────────────────────────────────────────────────

def test_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.key"

        original = AgentIdentity.generate("persist_test")
        original.save(path)

        loaded = AgentIdentity.load(path)
        assert loaded.domain == "persist_test"
        assert loaded.fingerprint == original.fingerprint
        assert loaded.instance_id == original.instance_id
        assert loaded.has_private_key is True

        # Can sign and cross-verify
        sig = loaded.sign(b"persistence works")
        assert original.verify(b"persistence works", sig) is True


def test_save_file_permissions():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "secret.key"
        ident = AgentIdentity.generate("test")
        ident.save(path)
        # File should be 0600 (owner read/write only)
        assert oct(path.stat().st_mode)[-3:] == "600"


def test_save_file_format():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.key"
        ident = AgentIdentity.generate("format_test")
        ident.save(path)

        data = json.loads(path.read_text())
        assert data["domain"] == "format_test"
        assert data["algorithm"] == "Ed25519"
        assert "private_key" in data
        assert "public_key" in data
        assert "fingerprint" in data
        assert "instance_id" in data


def test_load_with_domain_override():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.key"
        AgentIdentity.generate("original").save(path)

        loaded = AgentIdentity.load(path, domain="renamed")
        assert loaded.domain == "renamed"


# ── Succession ───────────────────────────────────────────────────

def test_transfer_proof():
    old = AgentIdentity.generate("root_idd")
    new = AgentIdentity.generate("root_idd")

    proof = old.create_transfer_proof(new)

    assert proof["from_instance"] == old.instance_id
    assert proof["to_instance"] == new.instance_id
    assert proof["to_public_key"] == new.public_key_b64
    assert "from_signature" in proof
    assert "to_signature" in proof
    assert "transfer_statement" in proof


def test_transfer_proof_verifiable():
    old = AgentIdentity.generate("root_idd")
    new = AgentIdentity.generate("root_idd")

    proof = old.create_transfer_proof(new)

    # Verify old identity signed the transfer
    import base64
    statement = base64.b64decode(proof["transfer_statement"])

    old_pub = AgentIdentity.from_registry("root_idd", old.to_registry())
    assert old_pub.verify_b64(statement, proof["from_signature"]) is True

    # Verify new identity accepted
    new_pub = AgentIdentity.from_registry("root_idd", new.to_registry())
    assert new_pub.verify_b64(statement, proof["to_signature"]) is True


def test_transfer_different_instances():
    old = AgentIdentity.generate("root_idd")
    new = AgentIdentity.generate("root_idd")
    assert old.instance_id != new.instance_id  # Different keypairs = different instances
    assert old.domain == new.domain  # Same domain


# ── SuccessionRecord ─────────────────────────────────────────────

def test_succession_record():
    record = SuccessionRecord(
        instance_id="root_idd-a3f9e28b",
        from_date="2025-12-31T00:00:00",
    )
    assert record.status == "active"
    d = record.to_dict()
    assert d["instance_id"] == "root_idd-a3f9e28b"
    assert d["to"] is None


# ── Repr ─────────────────────────────────────────────────────────

def test_repr_full():
    ident = AgentIdentity.generate("test")
    r = repr(ident)
    assert "test.aint" in r
    assert "full" in r


def test_repr_public_only():
    ident = AgentIdentity.generate("test")
    pub = AgentIdentity.from_registry("test", ident.to_registry())
    r = repr(pub)
    assert "public-only" in r

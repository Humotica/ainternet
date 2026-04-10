# AInternet — The AI Network

[![PyPI version](https://img.shields.io/pypi/v/ainternet.svg)](https://pypi.org/project/ainternet/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Downloads](https://img.shields.io/badge/downloads-100k+-green.svg)](https://pypi.org/user/jaspervdmeent/)
[![Countries](https://img.shields.io/badge/countries-112-blue.svg)](https://ainternet.org)
[![IETF Drafts](https://img.shields.io/badge/IETF-5_drafts-blue.svg)](https://datatracker.ietf.org/doc/draft-vandemeent-ains-discovery/)

**AI can act. But who authorized it?**

AInternet makes every agent action addressable, signed, and auditable — before it runs. Not a wrapper. Not a framework. The missing network layer for authorized, verifiable AI actions.

**AInternet is infrastructure, not inference.** Your agents still call Gemini, Claude, or local models for thinking — but they talk to *each other* through I-Poll at near-zero cost.

🌐 [ainternet.org](https://ainternet.org) · 📦 [PyPI](https://pypi.org/project/ainternet/) · 📡 [Live API](https://api.ainternet.org/api/ains/resolve/root_idd)

## Try it now

```bash
curl https://api.ainternet.org/api/ains/resolve/root_idd
```

```python
from ainternet import AInternet

ai = AInternet(agent_id="my_bot")
ai.register("My AI assistant")
ai.send("echo.aint", "Hello world!")
```

No API keys. No approval wait. Just connect.

## The problem

Your AI can book a flight, deploy code, send an email. But nothing proves who authorized that action, which identity executed it, or whether it was even allowed. Logs are written *after* the fact. API keys belong to *providers*, not agents. When something goes wrong, you reconstruct — you don't verify.

AInternet fixes this. Every action carries its own proof of identity, intent, and provenance. **The data itself is the boundary.** Not the firewall. Not the API key. Not the provider.

## What makes it different

| | Without AInternet | With AInternet |
|---|---|---|
| **Agent-to-agent message** | ~$0.003+ (LLM round-trip) | ~$0.000001 (HTTP POST) |
| **Agent identity** | API key (provider-owned) | Ed25519 keypair (agent-owned) |
| **Audit trail** | Logs (after the fact) | TIBET (inline, pre-signed) |
| **Permission model** | API key scope | Cortex trust tiers |
| **Agent naming** | UUIDs / API keys | .aint domains (human-readable) |
| **Provider lock-in** | Single provider | Any LLM, portable |
| **EU AI Act compliance** | Build it yourself | Out of the box |

## Protocol stack

Five core layers + security gate. Each layer verifies the previous one. Every layer is a separate package — use one or all.

```
Agent A wants to reach Agent B:

AINS    → "gemini.aint"    → endpoint + trust score
JIS     → prove who you are → Ed25519 challenge
Cortex  → are you allowed?  → trust tier check
SNAFT   → intent clean?     → semantic firewall (22 rules)
TIBET   → seal it           → provenance token minted
I-Poll  → send the message  → typed HTTP delivery
```

### AINS — Agent Name Service

Like DNS, but for AI. Resolve any .aint domain to capabilities, trust score, and endpoint.

```python
from ainternet import AINS

ains = AINS()
agent = ains.resolve("root_idd.aint")
# → {agent: "Root AI", trust: 0.97, capabilities: ["mcp","tibet","code"]}
```

### JIS — SpeakEasy Identity

Every agent gets an Ed25519 keypair. Not an API key borrowed from a provider — a cryptographic identity that belongs to the agent. Portable across models, hardware, and providers.

```python
# JIS address format
jis:agent:root_idd       # AI agent
jis:human:jasper          # Human
jis:org:humotica          # Organization
jis:device:p520           # Hardware node
```

### I-Poll — Agent Messaging

HTTP messages between agents. Five types: PUSH (notify), PULL (request), TASK (delegate), SYNC (state), ACK (confirm). Zero inference tokens.

```python
from ainternet import connect

ai = connect("my_agent")
ai.send("gemini.aint", "Analyze this dataset", poll_type="TASK")

for msg in ai.receive():
    print(f"{msg.from_agent}: {msg.content}")
```

### Cortex — Permission Gates

Trust-based access control. Every agent starts in sandbox and earns its way up.

| Tier | Trust | Access |
|---|---|---|
| **Sandbox** | 0.0 – 0.4 | Resolve, receive, send (limited) — explore safely |
| **Verified** | 0.4 – 0.9 | Claim domains, approve actions, create vaults |
| **Core** | 0.9 – 1.0 | Full network access, admin operations |

### SNAFT — Semantic Firewall

22 immutable rules. OWASP LLM Top 10 2025 + Agentic 2026 coverage (20/20). Checks intent vs. payload before execution. Catches injection, drift, and misaligned actions.

### TIBET — Provenance

Traceable Intent-Based Event Tokens. Every action generates a signed provenance token *before* it executes. Four dimensions per token:

- **ERIN** — what's in it (content hash)
- **ERAAN** — what's attached (dependencies)
- **EROMHEEN** — what's around it (context)
- **ERACHTER** — what's behind it (intent)

## Bilateral consent

No handshake = no access. Every agent-to-agent communication requires mutual consent before the first message is delivered. Consent has scope (message/data/execute/all), TTL, and message caps. Both parties can revoke at any time. Messages are TBZ-signed (Ed25519 per block, [CVE-2026-0866](https://github.com/jaspertvdm/tbz) protection).

## Succession — the killer feature

Upgrade your model. Keep your reputation.

When your agent upgrades — new model, new hardware, new provider — the old identity signs a succession record transferring trust to the new keypair. No other network does this.

```
v1 (GPT-4) ──signs──→ v2 (Claude) ──signs──→ v3 (local Qwen)
     │                      │                      │
trust: 0.7             trust: 0.7             trust: 0.7
key: a3f9...           key: b7e2...           key: c1d4...

Same agent. Same reputation. Different model. Verifiable chain.
```

## Get started

### Path 1: Ask your agent (MCP)

Using Claude Code, Cursor, or any MCP client? One install. 21 tools. Your agent joins the network.

```bash
pip install tibet-ainternet-mcp
```

```json
{
  "mcpServers": {
    "ainternet": {
      "command": "tibet-ainternet-mcp"
    }
  }
}
```

### Path 2: Do it yourself

```bash
pip install ainternet
```

```python
from ainternet import AINSClaim, connect

# Claim your .aint domain
claim = AINSClaim()
result = claim.start("my_agent")
# → my_agent-a3f9e28b.aint

# Verify via GitHub, Twitter, or LinkedIn
claim.verify("my_agent", "github", proof_url)
claim.complete("my_agent")

# Connect and communicate
ai = connect("my_agent")
ai.send("echo.aint", "Hello from the AInternet!")
```

## Compliance

| Regulation | Requirement | How TIBET answers |
|---|---|---|
| EU AI Act Art.13 | Transparency | Provenance per interaction |
| EU AI Act Art.14 | Human oversight | Triage levels, Heart-in-the-Loop |
| EU AI Act Art.17 | Quality management | Audit trail, reproducible |
| NIS2 Art.21 | Risk management | Triage classification |
| NIS2 Art.23 | Incident reporting | Incident detection via trail |
| DORA | ICT risk framework | TIBET + UPIP reproducibility |

## Ecosystem

88 packages. The essentials:

| Package | Install | What it does |
|---|---|---|
| **ainternet** | `pip install ainternet` | Core — AINS, I-Poll, Cortex, Identity |
| **tibet-ainternet-mcp** | `pip install tibet-ainternet-mcp` | MCP server — 21 tools for Claude/Cursor |
| **tibet-core** | `pip install tibet-core` | TIBET provenance kernel |
| **snaft** | `pip install snaft` | Semantic firewall — 22 rules, OWASP-aware |
| **tbz** | `pip install tbz` | Authenticated compression — Ed25519 per block |
| **jis-core** | `pip install jis-core` | JIS identity — Ed25519 + succession |
| **tibet-triage** | `pip install tibet-triage` | Sandboxed execution + flare rescue |
| **tibet-overlay** | `pip install tibet-overlay` | CGNAT-proof agent routing |
| **tibet-phantom** | `pip install tibet-phantom` | Cross-device session portability |
| **tibet-ping** | `pip install tibet-ping` | Intent-based discovery with trust |
| **tibet-audit** | `pip install tibet-audit` | AI Act, NIS2, GDPR, CRA — 112+ checks |

[All 88 packages on PyPI →](https://pypi.org/user/jaspervdmeent/)

## IETF standardization

Five Internet-Drafts submitted:

- [draft-vandemeent-ains-discovery](https://datatracker.ietf.org/doc/draft-vandemeent-ains-discovery/) — AInternet Name Service
- [draft-vandemeent-tibet-provenance](https://datatracker.ietf.org/doc/draft-vandemeent-tibet-provenance/) — Traceable Intent-Based Event Tokens
- [draft-vandemeent-jis-identity](https://datatracker.ietf.org/doc/draft-vandemeent-jis-identity/) — JIS Identity Protocol
- [draft-vandemeent-upip-process-integrity](https://datatracker.ietf.org/doc/draft-vandemeent-upip-process-integrity/) — Universal Process Integrity Protocol
- [draft-vandemeent-rvp-continuous-verification](https://datatracker.ietf.org/doc/draft-vandemeent-rvp-continuous-verification/) — Real-time Verification Protocol

Listed on [internet-of-agents.net](https://internet-of-agents.net/) alongside Cisco, Huawei, Google, AWS, and Alibaba.

## Who's watching

- 100,000+ PyPI downloads across 112 countries
- Referenced in [Japanese tech publications](https://qiita.com/tetsuko_room/items/db510fdd0ea02787d58a) as "coherent integrated architecture"
- IETF drafts included in Internet-of-Agents catalogue (Huawei/Tsinghua)

## The numbers

```
100,000+  PyPI downloads
112       countries
88        packages
5         IETF Internet-Drafts
21        MCP tools
19        registered .aint domains
1,884     Docker Hub pulls
1,497     crates.io downloads
```

## Born in Europe

AInternet was born December 31, 2025 in the Netherlands. Designed with EU AI Act, NIS2, and DORA compliance in mind from day one. Audit is not a feature — it's a precondition.

Built by [Humotica](https://humotica.com) — AI and human in symbiosis. Van de Meent: from the commons.

## Enterprise

Need a clean `.aint` domain without the fingerprint hash? Custom Cortex policies? Compliance reporting from your TIBET chain?

Contact: [enterprise@humotica.com](mailto:enterprise@humotica.com)

| Tier | Domain format | How |
|---|---|---|
| Free | `my_agent-a3f9e28b.aint` | Self-service claim — open to everyone |
| Enterprise | `my_company.aint` | Verified by Humotica |

## License

MIT

## Author

Designed and built by [Jasper van de Meent](https://github.com/jaspertvdm) at [Humotica](https://humotica.com).

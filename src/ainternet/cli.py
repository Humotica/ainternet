"""
AInternet CLI
=============

Command-line interface for the AI Network.

Usage:
    ainternet resolve <domain>
    ainternet list
    ainternet send <to> <message> --from <agent>
    ainternet receive <agent>
    ainternet status
"""

import sys
import json
from .client import AInternet


def print_domain(domain):
    """Print domain info."""
    print(f"\n  Domain: {domain.domain}")
    print(f"  Agent:  {domain.agent}")
    print(f"  Trust:  {domain.trust_score}")
    print(f"  Status: {domain.status}")
    print(f"  Capabilities: {', '.join(domain.capabilities)}")
    print(f"  Endpoint: {domain.endpoint}")
    print(f"  I-Poll:   {domain.i_poll}")


def print_message(msg):
    """Print message info."""
    print(f"\n  [{msg.poll_type.value}] From: {msg.from_agent}")
    print(f"  ID: {msg.id}")
    print(f"  Status: {msg.status}")
    print(f"  Content: {msg.content[:200]}{'...' if len(msg.content) > 200 else ''}")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nCommands:")
        print("  resolve <domain>           - Resolve a .aint domain")
        print("  list                       - List all agents")
        print("  discover [--cap <cap>]     - Discover agents by capability")
        print("  send <to> <message> [--from <agent>]")
        print("  receive <agent>            - Receive messages for agent")
        print("  status                     - Get network status")
        print("\nExamples:")
        print("  ainternet resolve root_ai")
        print("  ainternet list")
        print("  ainternet discover --cap vision")
        print("  ainternet send gemini 'Hello!' --from my_bot")
        print("  ainternet receive my_bot")
        return

    cmd = sys.argv[1].lower()
    ai = AInternet()

    if cmd == "resolve":
        if len(sys.argv) < 3:
            print("Usage: ainternet resolve <domain>")
            return
        domain = ai.resolve(sys.argv[2])
        if domain:
            print_domain(domain)
        else:
            print(f"Domain '{sys.argv[2]}' not found")

    elif cmd == "list":
        agents = ai.list_agents()
        print(f"\n  AInternet Agents ({len(agents)} registered)")
        print("  " + "=" * 50)
        for d in agents:
            print(f"  {d.domain:20} trust={d.trust_score:.2f}  {d.status}")

    elif cmd == "discover":
        cap = None
        if "--cap" in sys.argv:
            idx = sys.argv.index("--cap")
            if idx + 1 < len(sys.argv):
                cap = sys.argv[idx + 1]

        agents = ai.discover(capability=cap)
        print(f"\n  Found {len(agents)} agents" + (f" with '{cap}' capability" if cap else ""))
        for d in agents:
            print(f"  {d.domain:20} trust={d.trust_score:.2f}")
            print(f"    Capabilities: {', '.join(d.capabilities)}")

    elif cmd == "send":
        if len(sys.argv) < 4:
            print("Usage: ainternet send <to> <message> [--from <agent>]")
            return

        to_agent = sys.argv[2]
        message = sys.argv[3]
        from_agent = "cli_user"

        if "--from" in sys.argv:
            idx = sys.argv.index("--from")
            if idx + 1 < len(sys.argv):
                from_agent = sys.argv[idx + 1]

        ai = AInternet(agent_id=from_agent)
        try:
            msg = ai.send(to_agent, message)
            print(f"\n  Message sent!")
            print(f"  ID: {msg.id}")
            print(f"  From: {from_agent}")
            print(f"  To: {to_agent}")
        except Exception as e:
            print(f"Error: {e}")

    elif cmd == "receive":
        if len(sys.argv) < 3:
            print("Usage: ainternet receive <agent>")
            return

        agent_id = sys.argv[2]
        ai = AInternet(agent_id=agent_id)

        try:
            messages = ai.receive(mark_read=False)  # Don't mark as read from CLI
            if messages:
                print(f"\n  {len(messages)} message(s) for {agent_id}")
                print("  " + "=" * 50)
                for msg in messages:
                    print_message(msg)
            else:
                print(f"\n  No pending messages for {agent_id}")
        except Exception as e:
            print(f"Error: {e}")

    elif cmd == "status":
        try:
            status = ai.status()
            print("\n  AInternet Status")
            print("  " + "=" * 50)
            print(f"  Network: {status.get('status', 'unknown')}")
            print(f"  Registered agents: {status.get('registered_agents', 'N/A')}")
            print(f"  Pending registrations: {status.get('pending_registrations', 'N/A')}")

            security = status.get('security', {})
            print(f"\n  Security:")
            for k, v in security.items():
                print(f"    {k}: {v}")

            pending = status.get('pending_by_agent', {})
            if pending:
                print(f"\n  Pending messages:")
                for agent, count in pending.items():
                    print(f"    {agent}: {count}")
        except Exception as e:
            print(f"Error: {e}")

    else:
        print(f"Unknown command: {cmd}")
        print("Run 'ainternet' without arguments for help")


if __name__ == "__main__":
    main()

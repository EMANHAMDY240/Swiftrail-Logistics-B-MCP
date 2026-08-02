"""
Full run through every protocol concern, using the seed data described in
db/seed.sql / README.md. Run with:

    python demo.py --transport stdio        # against mcp_server/server.py
    python demo.py --transport http --url http://localhost:8000/mcp   # against server_http.py

Each step below is labeled with the concern it demonstrates so the output
doubles as the demo transcript (see demo/demo_transcript.md for a captured
run).
"""

import argparse
import asyncio
import json

from client import SwiftrailAgent


def section(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


async def run(transport: str, url: str | None):
    agent = SwiftrailAgent(transport, url)

    # ------------------------------------------------------------------
    section("Example 1: Connect to Swiftrail MCP Server")
    await agent.connect()
    print("Connected successfully.")

    # ------------------------------------------------------------------
    section("Example 2: Discover Available Tools")
    tools = await agent.discover_tools()

    for tool in tools:
        print(f"• {tool.name}")

    # ------------------------------------------------------------------
    section("Example 3: Search for a Customer")

    result = await agent.call_tool(
        "search_customer",
        {"customer_id": 3},
    )
    print(result.content[0].text)

    # ------------------------------------------------------------------
    section("Example 4: List Customer Invoices")

    result = await agent.call_tool(
        "list_customer_invoices",
        {"customer_id": 3},
    )
    print(result.content[0].text)

    # ------------------------------------------------------------------
    section("Example 5: Read Credit Policy Resource")

    policy = await agent.read_resource(
        "policy://credit-and-discount-authority"
    )

    if policy:
        print(policy.contents[0].text[:400] + "...")

    # ------------------------------------------------------------------
    section("Example 6: Render a Prompt Template")

    prompts = await agent.list_prompts()

    if prompts:
        rendered = await agent.get_prompt(
            "draft_rate_exception_justification",
            {
                "shipment_id": "5",
                "discount_pct": "25",
                "reason_summary": "customer bundling 3 future shipments this quarter",
            },
        )

        print(rendered.messages[0].content.text)

    # ------------------------------------------------------------------
    section("Example 7: Approve a Small Discount")

    result = await agent.call_tool(
        "approve_rate_exception",
        {"exception_id": 1},
    )

    print(result.content[0].text)

    # ------------------------------------------------------------------
    section("Example 8: Approve a Discount Requiring Authorization")

    result = await agent.call_tool(
        "approve_rate_exception",
        {"exception_id": 2},
    )

    print(result.content[0].text)

    # ------------------------------------------------------------------
    section("Example 9: Authenticate as Finance Manager")

    result = await agent.call_tool(
        "authenticate",
        {"employee_id": 3},
    )

    print(result.content[0].text)

    if agent.tool_list_dirty:
        print("\nUpdated Tool List:")

        tools = await agent.discover_tools()

        for tool in tools:
            print(f"• {tool.name}")

    # ------------------------------------------------------------------
    section("Example 10: View Portfolio Credit Exposure")

    result = await agent.call_tool(
        "list_portfolio_credit_exposure",
        {},
    )

    print(result.content[0].text[:500] + "...")

    # ------------------------------------------------------------------
    section("Example 11: Release a Credit Hold")

    result = await agent.call_tool(
        "release_credit_hold",
        {"hold_id": 2},
    )

    print(result.content[0].text)

    # ------------------------------------------------------------------
    section("Example 12: Run Portfolio Risk Sweep")

    async def progress(current, total, message):
        print(f"[{current}/{total}] {message}")

    result = await agent.call_tool(
        "run_portfolio_risk_sweep",
        {},
        progress_callback=progress,
    )

    parsed = json.loads(result.content[0].text)

    print(f"\nCustomers Scanned : {parsed['scanned']}")
    print(f"Summary           : {parsed['narrative_summary']}")

    await agent.close()

    section("Demo Finished Successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
    )

    parser.add_argument(
        "--url",
        default=None,
    )

    args = parser.parse_args()

    asyncio.run(run(args.transport, args.url))
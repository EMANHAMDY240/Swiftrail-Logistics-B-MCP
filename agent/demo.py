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


def _print_step(n: str, title: str):
    print(f"\n\n########## STEP {n}: {title} ##########")


async def run(transport: str, url: str | None):
    agent = SwiftrailAgent(transport, url)

    # ---- CONCERN: capability negotiation -------------------------------
    _print_step("1", "capability negotiation (initialize/initialized)")
    await agent.connect()

    # ---- CONCERN: tool discovery / read-only tools ----------------------
    _print_step("2", "tool discovery -- sales_rep session (default role)")
    tools = await agent.discover_tools()
    for t in tools:
        print(f"  - {t.name}")
    print("  (note: no finance-only tools visible yet -- session is sales_rep)")

    _print_step("3", "read-only lookups (no authorization needed)")
    result = await agent.call_tool("search_customer", {"customer_id": 3})
    print("search_customer(3) ->", result.content[0].text)

    result = await agent.call_tool("list_customer_invoices", {"customer_id": 3})
    print("list_customer_invoices(3) ->", result.content[0].text)

    # ---- CONCERN: resources ---------------------------------------------
    _print_step("4", "resources -- credit policy fetched as data, not called as a tool")
    policy = await agent.read_resource("policy://credit-and-discount-authority")
    if policy:
        print(policy.contents[0].text[:400] + "...")

    # ---- CONCERN: prompts -------------------------------------------------
    _print_step("5", "prompts -- discoverable, parameterized template")
    prompts = await agent.list_prompts()
    for p in prompts:
        print(f"  - {p.name}: {p.description}")
    if prompts:
        rendered = await agent.get_prompt(
            "draft_rate_exception_justification",
            {
                "shipment_id": "5",
                "discount_pct": "25",
                "reason_summary": "customer bundling 3 future shipments this quarter",
            },
        )
        print("Rendered prompt:", rendered.messages[0].content.text)

    # ---- CONCERN: defensive write tool, auto-approved path ---------------
    _print_step("6", "defensive write tool -- discount within authority (no elicitation)")
    result = await agent.call_tool("approve_rate_exception", {"exception_id": 1})
    print("approve_rate_exception(1) ->", result.content[0].text)
    print("  (already resolved in seed data -- shows the idempotency guard firing)")

    # ---- CONCERN: elicitation ---------------------------------------------
    _print_step("7", "elicitation -- above-authority discount pauses for a human")
    print("Calling approve_rate_exception(2) -- seed data: 25% discount, still 'pending'.")
    print("The agent will now BLOCK on a real terminal prompt from the server's elicitation/create call.")
    result = await agent.call_tool("approve_rate_exception", {"exception_id": 2})
    print("approve_rate_exception(2) ->", result.content[0].text)

    # ---- CONCERN: notifications / dynamic tool set ------------------------
    _print_step("8", "notifications -- authenticating as finance_manager changes the tool set")
    result = await agent.call_tool("authenticate", {"employee_id": 3})  # Sherif Nassar, finance_manager
    print("authenticate(3) ->", result.content[0].text)

    if agent.tool_list_dirty:
        tools_after = await agent.discover_tools()
        print("\nTool list AFTER role change:")
        for t in tools_after:
            print(f"  - {t.name}")
        print("  (list_portfolio_credit_exposure is new -- it did not exist for the sales_rep session)")

    result = await agent.call_tool("list_portfolio_credit_exposure", {})
    print("\nlist_portfolio_credit_exposure() ->", result.content[0].text[:500], "...")

    # ---- CONCERN: elicitation on the severe-hold path, now as finance_manager --
    _print_step("9", "elicitation -- severe credit hold release, now authorized to actually complete")
    print("Calling release_credit_hold(2) -- seed data: Red Sea Steel Imports, severity=severe.")
    result = await agent.call_tool("release_credit_hold", {"hold_id": 2})
    print("release_credit_hold(2) ->", result.content[0].text)

    # ---- CONCERN: progress tracking + sampling -----------------------------
    _print_step("10", "progress tracking + sampling -- long-running portfolio risk sweep")

    async def _on_progress(progress, total, message):
        print(f"  [progress] {progress}/{total} -- {message}")

    result = await agent.call_tool("run_portfolio_risk_sweep", {}, progress_callback=_on_progress)
    parsed = json.loads(result.content[0].text)
    print("Scanned:", parsed["scanned"], "customers")
    print("Narrative summary (via sampling/createMessage):", parsed["narrative_summary"])

    await agent.close()
    print("\n\nDemo complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--url", default=None)
    args = parser.parse_args()
    asyncio.run(run(args.transport, args.url))

import json

from app_instance import app
from db import get_connection
from mcp.server.mcpserver.context import Context
from mcp_types import SamplingMessage, TextContent as SamplingTextContent


def list_portfolio_credit_exposure() -> str:
    """List every active credit hold, every pending above-authority rate
    exception, and every customer currently on hold, across the whole
    portfolio. finance_manager only -- this is added to the tool set
    dynamically by the authenticate tool, not registered at startup."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT ch.*, c.name AS customer_name FROM credit_holds ch "
        "JOIN customers c ON c.id = ch.customer_id WHERE ch.status = 'active'"
    )
    active_holds = cursor.fetchall()

    cursor.execute(
        "SELECT re.*, s.customer_id FROM rate_exceptions re "
        "JOIN shipments s ON s.id = re.shipment_id "
        "WHERE re.status = 'pending' AND re.discount_pct > 15"
    )
    pending_discounts = cursor.fetchall()

    cursor.execute("SELECT id, name, credit_status FROM customers WHERE credit_status = 'hold'")
    customers_on_hold = cursor.fetchall()

    cursor.close()
    conn.close()

    return json.dumps(
        {
            "active_credit_holds": active_holds,
            "pending_above_authority_discounts": pending_discounts,
            "customers_on_hold": customers_on_hold,
        },
        default=str,
    )


@app.tool()
async def run_portfolio_risk_sweep(ctx: Context) -> str:
    """Score every customer's credit risk (overdue balance vs. credit limit,
    active holds), reporting progress as each one is scanned, then use
    sampling/createMessage -- answered by the connected agent's own model --
    to produce a short narrative summary of portfolio risk."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers")
    customers = cursor.fetchall()

    scored = []
    total = len(customers)
    for i, customer in enumerate(customers, start=1):
        cursor.execute(
            "SELECT COUNT(*) AS n FROM credit_holds WHERE customer_id = %s AND status = 'active'",
            (customer["id"],),
        )
        active_hold_count = cursor.fetchone()["n"]

        balance_ratio = (
            float(customer["balance_due"]) / float(customer["credit_limit"])
            if float(customer["credit_limit"]) > 0
            else 0
        )
        scored.append(
            {
                "customer_id": customer["id"],
                "name": customer["name"],
                "balance_ratio": round(balance_ratio, 3),
                "active_holds": active_hold_count,
            }
        )

        await ctx.report_progress(
            progress=i,
            total=total,
            message=f"Scored {customer['name']} ({i}/{total})",
        )

    cursor.close()
    conn.close()

    scores_text = "\n".join(
        f"- {s['name']}: balance is {s['balance_ratio']*100:.0f}% of credit limit, "
        f"{s['active_holds']} active hold(s)"
        for s in scored
    )

    sampling_result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=SamplingTextContent(
                    type="text",
                    text=(
                        "Write a 2-3 sentence portfolio risk summary for a "
                        "finance manager based on this data:\n" + scores_text
                    ),
                ),
            )
        ],
        max_tokens=200,
    )
    narrative = getattr(sampling_result.content, "text", str(sampling_result.content))

    return json.dumps({"scanned": total, "scores": scored, "narrative_summary": narrative}, default=str)

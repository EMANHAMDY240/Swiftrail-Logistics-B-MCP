from pydantic import BaseModel, Field

from app_instance import app
from db import get_connection
from mcp.server.mcpserver.context import Context
import session as session_state


class CreditHoldReleaseDecision(BaseModel):
    """Schema for the elicitation/create request sent when releasing a SEVERE
    credit hold."""

    confirm_release: bool = Field(
        description="Type true to confirm you are authorizing release of this SEVERE credit hold."
    )
    authorization_note: str = Field(
        min_length=10,
        description="Short justification for the override (min 10 characters), stored for audit purposes.",
    )


@app.tool()
async def release_credit_hold(hold_id: int, ctx: Context) -> str:
    """Release an active credit hold on a customer. Minor holds release
    immediately. Severe holds pause the call and use elicitation/create to ask
    a human to confirm, then require the session to be authenticated as
    finance_manager to actually finalize the release."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credit_holds WHERE id = %s", (hold_id,))
    hold = cursor.fetchone()

    if not hold:
        cursor.close()
        conn.close()
        return f"No credit hold found with id {hold_id}"

    if hold["status"] != "active":
        cursor.close()
        conn.close()
        return f"Credit hold {hold_id} is already '{hold['status']}'."

    if hold["severity"] == "minor":
        cursor.execute(
            "UPDATE credit_holds SET status = 'released', released_by = %s, released_at = NOW() WHERE id = %s",
            (session_state.session_employee_id, hold_id),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return f"Credit hold {hold_id} (minor) released by employee {session_state.session_employee_id}."

    result = await ctx.elicit(
        message=(
            f"Credit hold {hold_id} on customer_id={hold['customer_id']} is "
            f"SEVERE (reason: {hold['reason']}). Releasing it will let this "
            f"customer's shipments move again while they remain significantly "
            f"overdue. Confirm you want to release it."
        ),
        schema=CreditHoldReleaseDecision,
    )

    if result.action != "accept" or not result.data.confirm_release:
        cursor.close()
        conn.close()
        return f"Release of severe credit hold {hold_id} was not confirmed."

    if session_state.session_role != "finance_manager":
        cursor.close()
        conn.close()
        return (
            f"Release of severe credit hold {hold_id} was confirmed by a "
            f"human, but the active session role is "
            f"'{session_state.session_role}', not finance_manager. Use the "
            f"authenticate tool to switch roles, then retry."
        )

    cursor.execute(
        "UPDATE credit_holds SET status = 'released', released_by = %s, released_at = NOW() WHERE id = %s",
        (session_state.session_employee_id, hold_id),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return (
        f"Credit hold {hold_id} (SEVERE) released by employee "
        f"{session_state.session_employee_id} (finance_manager). "
        f"Audit note: {result.data.authorization_note}"
    )

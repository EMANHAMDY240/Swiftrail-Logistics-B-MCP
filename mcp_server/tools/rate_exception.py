from pydantic import BaseModel, Field

from app_instance import app
from db import get_connection
from mcp.server.mcpserver.context import Context
import session as session_state


class RateExceptionDecision(BaseModel):
    """Schema for the elicitation/create request sent when a discount exceeds
    the 15% sales_rep auto-approval ceiling. The client (agent) collects these
    two fields from a human and sends them back."""

    approve: bool = Field(
        description="Type true to approve this above-authority discount, false to reject it."
    )
    reviewer_note: str = Field(
        min_length=10,
        description="Reason for the decision (min 10 characters), stored for audit purposes.",
    )


@app.tool()
async def approve_rate_exception(exception_id: int, ctx: Context) -> str:
    """Approve a pending rate exception (discount) request. Discounts at or
    under 15% auto-approve immediately. Discounts above 15% pause the call and
    use elicitation/create to ask a human to approve or reject, then require
    the session to be authenticated as finance_manager to actually finalize."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rate_exceptions WHERE id = %s", (exception_id,))
    exception = cursor.fetchone()

    if not exception:
        cursor.close()
        conn.close()
        return f"No rate exception found with id {exception_id}"

    if exception["status"] != "pending":
        cursor.close()
        conn.close()
        return f"Rate exception {exception_id} is already '{exception['status']}', cannot re-approve."

    discount = float(exception["discount_pct"])

    if discount <= 15:
        cursor.execute(
            "UPDATE rate_exceptions SET status = 'auto_approved', resolved_at = NOW() WHERE id = %s",
            (exception_id,),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return (
            f"Rate exception {exception_id} marked as 'auto_approved' "
            f"({discount}% is within sales_rep authority)."
        )

    result = await ctx.elicit(
        message=(
            f"Rate exception {exception_id} requests a {discount}% discount "
            f"(justification: {exception['justification']}). This exceeds the "
            f"15% sales_rep auto-approval ceiling. Approve or reject?"
        ),
        schema=RateExceptionDecision,
    )

    if result.action != "accept":
        cursor.close()
        conn.close()
        return f"Rate exception {exception_id} approval was not confirmed (action={result.action})."

    if not result.data.approve:
        cursor.execute(
            "UPDATE rate_exceptions SET status = 'rejected', approved_by = %s, resolved_at = NOW() WHERE id = %s",
            (session_state.session_employee_id, exception_id),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return f"Rate exception {exception_id} was rejected by human decision. Note: {result.data.reviewer_note}"

    if session_state.session_role != "finance_manager":
        cursor.close()
        conn.close()
        return (
            f"Discount of {discount}% on rate exception {exception_id} was "
            f"confirmed by a human, but the active session role is "
            f"'{session_state.session_role}', not finance_manager. Use the "
            f"authenticate tool to switch roles, then retry the approval."
        )

    cursor.execute(
        "UPDATE rate_exceptions SET status = 'approved', approved_by = %s, resolved_at = NOW() WHERE id = %s",
        (session_state.session_employee_id, exception_id),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return (
        f"Rate exception {exception_id} marked as 'approved' by employee "
        f"{session_state.session_employee_id} (finance_manager). "
        f"Note: {result.data.reviewer_note}"
    )

from app_instance import app
from db import get_connection

session_role = "sales_rep"
session_employee_id = 1


@app.tool()
def approve_rate_exception(exception_id: int) -> str:
    """Approve a pending rate exception (discount) request. Discounts over 15% require finance_manager authorization."""
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

    if discount > 15 and session_role != "finance_manager":
        cursor.close()
        conn.close()
        return (
            f"Discount of {discount}% exceeds sales_rep authority (max 15% "
            f"auto-approval). This requires finance_manager approval."
        )

    status = "auto_approved" if discount <= 15 else "approved"
    approved_by = session_employee_id if status == "approved" else None

    cursor.execute(
        "UPDATE rate_exceptions SET status = %s, approved_by = %s, resolved_at = NOW() WHERE id = %s",
        (status, approved_by, exception_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return f"Rate exception {exception_id} marked as '{status}'."
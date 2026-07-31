from app_instance import app
from db import get_connection
from tools.rate_exception import session_role, session_employee_id


@app.tool()
def release_credit_hold(hold_id: int) -> str:
    """Release an active credit hold on a customer. Severe holds require finance_manager authorization."""
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

    if hold["severity"] == "severe" and session_role != "finance_manager":
        cursor.close()
        conn.close()
        return (
            f"Credit hold {hold_id} is severe (reason: {hold['reason']}). "
            f"This requires finance_manager authorization to release."
        )

    cursor.execute(
        "UPDATE credit_holds SET status = 'released', released_by = %s, released_at = NOW() WHERE id = %s",
        (session_employee_id, hold_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return f"Credit hold {hold_id} released."
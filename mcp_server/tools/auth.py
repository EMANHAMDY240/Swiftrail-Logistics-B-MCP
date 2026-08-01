import json

from app_instance import app
from db import get_connection
from mcp.server.mcpserver.context import Context
import session as session_state
from tools.portfolio import list_portfolio_credit_exposure


@app.tool()
async def authenticate(employee_id: int, ctx: Context) -> str:
    """Authenticate as a specific employee, switching the active session
    role for the rest of this connection. Elevating to finance_manager
    dynamically exposes list_portfolio_credit_exposure and fires
    notifications/tools/list_changed; stepping back down removes it again."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id = %s", (employee_id,))
    employee = cursor.fetchone()
    cursor.close()
    conn.close()

    if not employee:
        return f"No employee found with id {employee_id}"

    old_role = session_state.session_role
    session_state.set_session(employee["role"], employee["id"])

    tool_set_changed = False
    if old_role != "finance_manager" and employee["role"] == "finance_manager":
        app.add_tool(list_portfolio_credit_exposure, name="list_portfolio_credit_exposure")
        tool_set_changed = True
    elif old_role == "finance_manager" and employee["role"] != "finance_manager":
        app.remove_tool("list_portfolio_credit_exposure")
        tool_set_changed = True

    if tool_set_changed:
        await ctx.notify_tools_changed()

    return json.dumps(
        {
            "employee_id": employee["id"],
            "name": employee["name"],
            "role": employee["role"],
            "tool_set_changed": tool_set_changed,
        }
    )

"""Shared session state across tool modules.

One MCP connection = one session in this lab. It starts as sales_rep and is
elevated via the `authenticate` tool (tools/auth.py). Every tool that needs
to know "who is calling right now" reads session_role / session_employee_id
from here instead of keeping its own separate copy.
"""

session_role = "sales_rep"
session_employee_id = 1


def set_session(role: str, employee_id: int) -> None:
    global session_role, session_employee_id
    session_role = role
    session_employee_id = employee_id

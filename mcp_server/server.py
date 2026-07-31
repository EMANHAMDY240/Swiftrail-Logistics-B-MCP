import asyncio
import json
from mcp.server import MCPServer

from db import get_connection

app = MCPServer("swiftrail-mcp-server")


@app.tool()
def search_customer(customer_id: int) -> str:
    """Get a customer's profile including credit status and balance."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return f"No customer found with id {customer_id}"
    return json.dumps(row, default=str)


@app.tool()
def get_shipment_status(shipment_id: int) -> str:
    """Get the current status and details of a shipment."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shipments WHERE id = %s", (shipment_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return f"No shipment found with id {shipment_id}"
    return json.dumps(row, default=str)


if __name__ == "__main__":
    asyncio.run(app.run_stdio_async())
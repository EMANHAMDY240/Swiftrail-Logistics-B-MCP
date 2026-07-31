import asyncio
from app_instance import app

import tools.read_tools
import tools.rate_exception
import tools.credit_hold


async def main():
    print("=== Testing search_customer ===")
    result = await app.call_tool("search_customer", {"customer_id": 1})
    print(result.content[0].text)

    print("\n=== Testing get_shipment_status ===")
    result = await app.call_tool("get_shipment_status", {"shipment_id": 300})
    print(result.content[0].text)

    print("\n=== Testing list_customer_invoices ===")
    result = await app.call_tool("list_customer_invoices", {"customer_id": 3})
    print(result.content[0].text)


asyncio.run(main())
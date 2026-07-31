import asyncio
from app_instance import app
import tools.read_tools
import tools.rate_exception


if __name__ == "__main__":
    asyncio.run(app.run_stdio_async())
"""
SwiftrailAgent -- the MCP client side of this lab.

Covers, end to end:

  1. THE HANDSHAKE (initialize/initialized): connect() opens the transport,
     declares the client's own capabilities (elicitation + sampling support),
     and calls session.initialize(). We store the server's declared
     capabilities from the InitializeResult and gate everything else on
     them via `supports()` -- e.g. we only attempt resources/read if the
     server actually declared a resources capability, instead of assuming
     it and getting a protocol error.

  2. TOOL DISCOVERY + CALLING: discover_tools() calls tools/list and returns
     the live schema for every tool currently exposed (which changes at
     runtime -- see #4). call_tool() invokes one by name/arguments.

  3. ELICITATION HANDLING: `elicitation_callback` is the function the
     ClientSession invokes whenever the *server* calls elicitation/create
     mid-tool-call. This genuinely pauses the agent -- it blocks on
     `input()` and prints the server's question and schema to the terminal
     -- rather than auto-answering or silently proceeding. Nothing else in
     this file can run until a human types a response here.

  4. REACTING TO tools/list_changed: `_on_message` is registered as the
     ClientSession's generic message handler. When it sees a
     notifications/tools/list_changed message, it does NOT poll or guess --
     it flags the tool list as stale so the next discover_tools() call
     re-fetches the live set (demo.py shows this by calling authenticate,
     then immediately re-listing tools and printing the diff).

  5. SAMPLING: `sampling_callback` is what actually answers
     sampling/createMessage requests using the AGENT's own model (not the
     server's), per the sampling capability the agent declared in
     connect(). If ANTHROPIC_API_KEY is set it makes a real completion;
     otherwise it returns a clearly-labeled canned response so the demo
     still runs offline.

NOTE ON THE SDK: this targets the official `mcp` Python SDK's ClientSession
API. If your installed SDK version names things slightly differently
(message_handler vs. a subclassed session, etc.), the comments below flag
the exact spots to adjust.
"""

import argparse
import asyncio
import os
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client as streamablehttp_client
from mcp.client.session import ClientRequestContext as RequestContext
from mcp.types import (
    ElicitResult,
    CreateMessageResult,
    TextContent,
)


class SwiftrailAgent:
    def __init__(self, transport: str, http_url: str | None = None):
        self.transport = transport
        self.http_url = http_url
        self.session: ClientSession | None = None
        self.server_capabilities = None
        self.server_info = None
        self.tool_list_dirty = True
        self._stack = AsyncExitStack()

    # ------------------------------------------------------------------ #
    # 1. HANDSHAKE
    # ------------------------------------------------------------------ #
    async def connect(self):
        if self.transport == "stdio":
            params = StdioServerParameters(
                command="python",
                args=["server.py"],
                cwd="../mcp_server",
            )
            read, write = await self._stack.enter_async_context(stdio_client(params))
        elif self.transport == "http":
            if not self.http_url:
                raise ValueError("http transport requires --url")
            read, write, _ = await self._stack.enter_async_context(
                streamablehttp_client(self.http_url)
            )
        else:
            raise ValueError(f"Unknown transport: {self.transport}")

        self.session = await self._stack.enter_async_context(
            ClientSession(
                read,
                write,
                elicitation_callback=self._elicitation_callback,
                sampling_callback=self._sampling_callback,
                message_handler=self._on_message,
            )
        )

        init_result = await self.session.initialize()
        self.server_capabilities = init_result.capabilities
        self.server_info = init_result.server_info

        print("=" * 64)
        print("HANDSHAKE COMPLETE (initialize / initialized)")
        print(f"  Server: {self.server_info.name} (protocol {init_result.protocol_version})")
        print("  Declared server capabilities:")
        print(f"    tools     : {self.server_capabilities.tools}")
        print(f"    resources : {self.server_capabilities.resources}")
        print(f"    prompts   : {self.server_capabilities.prompts}")
        print("  Declared client capabilities: elicitation, sampling")
        print("=" * 64)
        return init_result

    def supports(self, capability_name: str) -> bool:
        """Check a SERVER-declared capability before relying on it. This is the
        client-side half of capability negotiation: e.g. before offering the
        credit-policy resource to the user, we check supports('resources')
        instead of assuming every server implements resources/read."""
        return bool(getattr(self.server_capabilities, capability_name, None))

    # ------------------------------------------------------------------ #
    # 2. TOOL DISCOVERY + CALLING
    # ------------------------------------------------------------------ #
    async def discover_tools(self):
        result = await self.session.list_tools()
        self.tool_list_dirty = False
        return result.tools

    async def call_tool(self, name: str, arguments: dict, progress_callback=None):
        """progress_callback, if given, is invoked as (progress, total, message) for
        every notifications/progress the server sends during this call -- used by
        run_portfolio_risk_sweep so the terminal shows live progress instead of a
        single blocking wait."""
        if progress_callback is not None:
            return await self.session.call_tool(
                name, arguments, progress_callback=progress_callback
            )
        return await self.session.call_tool(name, arguments)

    async def read_resource(self, uri: str):
        if not self.supports("resources"):
            print(f"[skip] server did not declare a resources capability; cannot read {uri}")
            return None
        return await self.session.read_resource(uri)

    async def list_prompts(self):
        if not self.supports("prompts"):
            print("[skip] server did not declare a prompts capability")
            return []
        result = await self.session.list_prompts()
        return result.prompts

    async def get_prompt(self, name: str, arguments: dict):
        return await self.session.get_prompt(name, arguments)

    # ------------------------------------------------------------------ #
    # 3. ELICITATION -- this is the part that must genuinely pause
    # ------------------------------------------------------------------ #
    async def _elicitation_callback(self, context: RequestContext, params):
        print("\n" + "!" * 64)
        print("SERVER PAUSED THE CALL: elicitation/create")
        print(f"  {params.message}")
        schema_props = (params.requested_schema or {}).get("properties", {})
        print("  The server needs the following, from a human:")
        for field_name, field_schema in schema_props.items():
            desc = field_schema.get("description", "")
            print(f"    - {field_name} ({field_schema.get('type', 'string')}): {desc}")
        print("!" * 64)

        answers = {}
        for field_name, field_schema in schema_props.items():
            prompt_text = f"  > {field_name}: "
            raw = input(prompt_text)
            if field_schema.get("type") == "boolean":
                answers[field_name] = raw.strip().lower() in ("y", "yes", "true", "1")
            else:
                answers[field_name] = raw

        confirm = input("  Submit this response to the server? [y/N]: ").strip().lower()
        if confirm != "y":
            print("  -> declined. Tool call will report the human did not confirm.\n")
            return ElicitResult(action="decline")

        print("  -> submitted.\n")
        return ElicitResult(action="accept", content=answers)

    # ------------------------------------------------------------------ #
    # 5. SAMPLING -- answered by the AGENT's model, not the server's
    # ------------------------------------------------------------------ #
    async def _sampling_callback(self, context: RequestContext, params):
        prompt_text = ""
        if params.messages:
            last = params.messages[-1].content
            prompt_text = getattr(last, "text", str(last))

        print("\n" + "~" * 64)
        print("SERVER REQUESTED SAMPLING: sampling/createMessage")
        print("  (answered by the connected agent's own model, not the server's)")
        print("~" * 64)

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=params.maxTokens or 200,
                messages=[{"role": "user", "content": prompt_text}],
            )
            text = response.content[0].text
            model_name = "claude-sonnet-4-6"
        else:
            text = (
                "[offline demo mode -- set ANTHROPIC_API_KEY for a real completion] "
                "Summary based on prompt: " + prompt_text[:160]
            )
            model_name = "agent-offline-stub"

        return CreateMessageResult(
            role="assistant",
            content=TextContent(type="text", text=text),
            model=model_name,
        )

    # ------------------------------------------------------------------ #
    # 4. REACTING TO tools/list_changed
    # ------------------------------------------------------------------ #
    async def _on_message(self, message):
        """Generic incoming-message hook. We only care about one notification
        type here: notifications/tools/list_changed. When it arrives we do NOT
        immediately re-fetch (that would race the notification handler against
        whatever tool call triggered it) -- we flag the cache dirty and let the
        next discover_tools() call do a real tools/list round trip.
        """
        method = getattr(message, "method", None)
        if method is None and hasattr(message, "root"):
            method = getattr(message.root, "method", None)

        if method == "notifications/tools/list_changed":
            print("\n>>> notifications/tools/list_changed RECEIVED -- tool set changed on the server.")
            self.tool_list_dirty = True

    async def close(self):
        await self._stack.aclose()


async def _smoke_test():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--url", default=None)
    args = parser.parse_args()

    agent = SwiftrailAgent(args.transport, args.url)
    await agent.connect()
    tools = await agent.discover_tools()
    print("\nDiscovered tools:")
    for t in tools:
        print(f"  - {t.name}: {t.description}")
    await agent.close()


if __name__ == "__main__":
    asyncio.run(_smoke_test())

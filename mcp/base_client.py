"""
Base MCP HTTP Client.

Implements JSON-RPC 2.0 calls to an MCP server exposed over HTTP.
Follows the MCP specification (https://spec.modelcontextprotocol.io/).

All public methods are async and safe to call from FastAPI request handlers.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx


class MCPHTTPClient:
    """
    Minimal async client for an MCP server with HTTP transport.

    The MCP protocol uses JSON-RPC 2.0 envelopes.  This client handles:
      • tools/list   — discover available tools
      • tools/call   — invoke a specific tool
      • resources/list  — list available resources
      • resources/read  — read a specific resource
    """

    def __init__(
        self,
        server_url: str,
        auth_token: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self._headers: Dict[str, str] = {"Content-Type": "application/json"}
        if auth_token:
            self._headers["Authorization"] = f"Bearer {auth_token}"
        self._timeout = timeout
        self._req_id = 0

    # ── Low-level RPC ─────────────────────────────────────────────────────────

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def _rpc(self, method: str, params: Optional[Dict] = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._next_id(),
        }
        if params:
            payload["params"] = params

        async with httpx.AsyncClient(
            headers=self._headers, timeout=self._timeout
        ) as client:
            response = await client.post(self.server_url, json=payload)
            response.raise_for_status()
            data = response.json()

        if "error" in data:
            raise RuntimeError(
                f"MCP RPC error [{data['error'].get('code')}]: {data['error'].get('message')}"
            )
        return data.get("result")

    # ── MCP helpers ───────────────────────────────────────────────────────────

    async def list_tools(self) -> List[Dict[str, Any]]:
        result = await self._rpc("tools/list")
        return result.get("tools", []) if result else []

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        result = await self._rpc(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )
        return result

    async def list_resources(self) -> List[Dict[str, Any]]:
        result = await self._rpc("resources/list")
        return result.get("resources", []) if result else []

    async def read_resource(self, uri: str) -> Any:
        result = await self._rpc("resources/read", {"uri": uri})
        return result

"""
MCP Registry.

A central catalogue of all MCP servers this backend knows about.
New servers can be registered at runtime.

Usage:
    registry = MCPRegistry()
    client = registry.get_client("gdrive")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from config.settings import settings
from mcp.base_client import MCPHTTPClient
from mcp.gdrive_client import GDriveClient


@dataclass
class MCPServerConfig:
    name: str
    url: str
    description: str
    auth_token: str = ""
    enabled: bool = True


class MCPRegistry:
    """Manage known MCP servers and their client instances."""

    def __init__(self) -> None:
        self._configs: Dict[str, MCPServerConfig] = {}
        self._clients: Dict[str, MCPHTTPClient] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(
            MCPServerConfig(
                name="gdrive",
                url=settings.GDRIVE_MCP_URL,
                description="Google Drive MCP server",
                auth_token=settings.GDRIVE_ACCESS_TOKEN,
            )
        )

    def register(self, config: MCPServerConfig) -> None:
        self._configs[config.name] = config

    def get_raw_client(self, name: str) -> Optional[MCPHTTPClient]:
        cfg = self._configs.get(name)
        if cfg is None or not cfg.enabled:
            return None
        if name not in self._clients:
            self._clients[name] = MCPHTTPClient(
                server_url=cfg.url,
                auth_token=cfg.auth_token or None,
            )
        return self._clients[name]

    def get_gdrive_client(self, access_token: Optional[str] = None) -> GDriveClient:
        return GDriveClient(access_token=access_token)

    def list_servers(self) -> list:
        return [
            {
                "name": cfg.name,
                "url": cfg.url,
                "description": cfg.description,
                "enabled": cfg.enabled,
            }
            for cfg in self._configs.values()
        ]


# Module-level singleton
_registry: Optional[MCPRegistry] = None


def get_mcp_registry() -> MCPRegistry:
    global _registry
    if _registry is None:
        _registry = MCPRegistry()
    return _registry

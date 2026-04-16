"""1ai-social MCP server entry point."""

import importlib

if __name__ == "__main__":
    mcp_server = importlib.import_module("1ai_social.mcp_server")
    mcp_server.main()

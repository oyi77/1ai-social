"""1ai-social MCP server entry point."""

import importlib

if __name__ == "__main__":
    # Package name starts with digit, so use relative import via parent
    mcp_server = importlib.import_module(".mcp_server", __package__)
    mcp_server.main()

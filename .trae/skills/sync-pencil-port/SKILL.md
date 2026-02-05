---
name: sync-pencil-port
description: Synchronize the pencil WebSocket port between settings.json and mcp.json files. This skill helps maintain consistent port configuration when the pencil service becomes unavailable due to port mismatch.
---

# Sync Pencil Port Skill

This skill synchronizes the pencil WebSocket port between `C:\Users\ChengWentao\.gemini\settings.json` and `d:\Dev2026\04.icongen-mcp\icongen-mcp\.trae\mcp.json` files to ensure they match.

## Purpose

When the pencil MCP service becomes unavailable, this skill can synchronize the WebSocket port configuration between the settings.json file and the mcp.json file, ensuring they use the same port number.

## When to Use This Skill

Use this skill when:
1. The pencil service is not working due to port configuration mismatch
2. The port in `C:\Users\ChengWentao\.gemini\settings.json` differs from the one in `.trae\mcp.json`
3. Need to update the mcp.json file to match the port from settings.json

## How It Works

1. Reads the pencil port configuration from `C:\Users\ChengWentao\.gemini\settings.json`
2. Extracts the WebSocket port number from the `--ws-port` argument
3. Updates the corresponding port in `d:\Dev2026\04.icongen-mcp\icongen-mcp\.trae\mcp.json`
4. Preserves all other configuration settings

## Execution

The skill executes the `sync_pencil_port.py` script which:
- Validates both configuration files exist
- Reads the port from settings.json
- Updates mcp.json with the matching port
- Provides feedback on success or failure
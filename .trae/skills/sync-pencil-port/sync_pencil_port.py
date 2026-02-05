#!/usr/bin/env python3
"""
Sync Pencil Port Skill
This script synchronizes the pencil WebSocket port between settings.json and mcp.json files.
"""

import json
import os
import sys
from pathlib import Path


def get_pencil_port_from_settings():
    """Get the pencil port from settings.json file."""
    settings_path = Path.home() / ".gemini" / "settings.json"
    
    if not settings_path.exists():
        raise FileNotFoundError(f"Settings file not found: {settings_path}")
    
    with open(settings_path, 'r', encoding='utf-8') as f:
        settings_data = json.load(f)
    
    if "mcpServers" not in settings_data or "pencil" not in settings_data["mcpServers"]:
        raise KeyError("Pencil configuration not found in settings.json")
    
    args = settings_data["mcpServers"]["pencil"].get("args", [])
    if len(args) >= 2 and args[0] == "--ws-port":
        return args[1]
    else:
        raise ValueError("Pencil port not found in settings.json args")


def update_mcp_json_with_port(port):
    """Update the mcp.json file with the specified port."""
    mcp_path = Path("d:/Dev2026/04.icongen-mcp/icongen-mcp/.trae/mcp.json")
    
    if not mcp_path.exists():
        raise FileNotFoundError(f"MCP config file not found: {mcp_path}")
    
    with open(mcp_path, 'r', encoding='utf-8') as f:
        mcp_data = json.load(f)
    
    # Update the pencil port in mcp.json
    if "mcpServers" not in mcp_data or "pencil" not in mcp_data["mcpServers"]:
        raise KeyError("Pencil configuration not found in mcp.json")
    
    # Find and update the port argument
    args = mcp_data["mcpServers"]["pencil"].get("args", [])
    port_updated = False
    
    for i in range(len(args)):
        if args[i] == "--ws-port" and i + 1 < len(args):
            args[i + 1] = port
            port_updated = True
            break
    
    if not port_updated:
        # If --ws-port is not found, add it
        args.extend(["--ws-port", port])
    
    mcp_data["mcpServers"]["pencil"]["args"] = args
    
    # Write the updated configuration back to file
    with open(mcp_path, 'w', encoding='utf-8') as f:
        json.dump(mcp_data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully updated pencil port to {port} in mcp.json")


def sync_pencil_port():
    """Main function to synchronize the pencil port."""
    try:
        # Get the port from settings.json
        port = get_pencil_port_from_settings()
        print(f"Found pencil port {port} in settings.json")
        
        # Update mcp.json with the port
        update_mcp_json_with_port(port)
        
        print("Pencil port synchronization completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during port synchronization: {str(e)}")
        return False


if __name__ == "__main__":
    success = sync_pencil_port()
    sys.exit(0 if success else 1)
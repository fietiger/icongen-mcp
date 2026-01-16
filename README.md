# MCP Tools Collection

**版本**: 1.0.1

This repository contains a collection of Model Context Protocol (MCP) tools organized in a modular structure.

## Project Structure

```
icongen-mcp/                           # Main project directory
├── mcp_tools_collection/              # Tools collection directory
│   ├── icogen_mcp_standalone/         # Standalone PNG to ICO converter
│   │   ├── src/icogen_mcp/            # Source code
│   │   ├── pyproject.toml             # Project configuration
│   │   ├── README.md                  # Documentation
│   │   └── LICENSE                    # License
│   ├── runcmd_mcp_standalone/         # Standalone async command executor
│   │   ├── src/runcmd_mcp/            # Source code
│   │   ├── pyproject.toml             # Project configuration
│   │   ├── README.md                  # Documentation
│   │   └── LICENSE                    # License
│   └── README.md                      # Collection documentation
├── pyproject.toml                     # Main project configuration
└── README.md                          # This file
```

## Tools Included

### 1. icogen-mcp
A Model Context Protocol (MCP) service for converting PNG files to ICO files with customizable icon dimensions.

### 2. runcmd-mcp
A Model Context Protocol (MCP) service for executing system commands asynchronously with status tracking.

## Installation

Each tool can be installed independently:

```bash
# Install icogen-mcp
cd mcp_tools_collection/icogen_mcp_standalone
pip install -e .

# Install runcmd-mcp
cd mcp_tools_collection/runcmd_mcp_standalone
pip install -e .
```

Or install the entire collection:

```bash
pip install -e .
```

## Usage

After installation, each tool can be run as a standalone MCP service:

```bash
# Run icogen-mcp service
icogen-mcp

# Run runcmd-mcp service
runcmd-mcp
```

## Development

This project follows a modular design where each MCP tool is developed as a standalone package that can be published independently. This allows for:

- Independent versioning of each tool
- Separate testing and CI/CD pipelines
- Easy maintenance and updates
- Clear separation of concerns
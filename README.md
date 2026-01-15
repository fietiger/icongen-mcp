# icogen-mcp

A Model Context Protocol (MCP) service that enables AI assistants and other tools to convert PNG image files to Windows ICO icon files. The service provides a standardized interface for generating multi-resolution ICO files from PNG sources with customizable icon dimensions.

## Features

- Convert PNG files to multi-size ICO files with a single tool call
- Support for custom icon dimensions (defaults to 16x16, 32x32, 48x48, 64x64)
- Flexible output options - save to file or return binary data
- Built on the FastMCP framework for reliable MCP compliance
- Designed specifically for integration with AI assistants and automated workflows
- Utilizes Pillow for high-quality image processing

## Installation

```bash
pip install icogen-mcp
```

## Usage

This service is designed to work with MCP-compatible clients. Once integrated, you can use the `convert_png_to_ico` tool to convert PNG files to ICO format with customizable dimensions.

## Use Cases

- Icon generation for desktop applications
- Automated asset conversion in build pipelines
- AI-assisted graphic design workflows
- Integration with development tools and IDEs

## Dependencies

- Pillow: For image processing
- fastmcp: For MCP protocol implementation
- pydantic: For data validation

## Architecture

The service implements the Model Context Protocol specification and provides a single primary function:

- `convert_png_to_ico`: Converts a PNG file to an ICO file with customizable dimensions

The service leverages the Pillow library for high-quality image resizing and ICO format generation, supporting multiple resolutions within a single ICO file.

## License

MIT
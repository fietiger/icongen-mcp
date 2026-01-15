# MCP Tools Collection

这是一个MCP（Model Context Protocol）工具集合，包含多个独立的MCP服务工具。

## 包含的工具

### 1. icogen-mcp
- **功能**: PNG到ICO图标转换工具
- **用途**: 将PNG图像文件转换为Windows ICO图标文件，支持多种尺寸
- **目录**: `icogen_mcp_standalone/`

### 2. runcmd-mcp
- **功能**: 异步命令执行工具
- **用途**: 异步执行系统命令并查询执行状态
- **目录**: `runcmd_mcp_standalone/`

### 3. winterm-mcp
- **功能**: Windows 终端命令执行工具
- **用途**: 专门支持 Windows 终端的异步命令执行，支持 PowerShell 和 Cmd
- **目录**: `winterm_mcp_standalone/`

## 使用说明

每个工具都是独立的Python包，可以分别安装和使用：

### 安装icogen-mcp
```bash
cd icogen_mcp_standalone
pip install -e .
```

### 安装runcmd-mcp
```bash
cd runcmd_mcp_standalone
pip install -e .
```

### 安装winterm-mcp
```bash
cd winterm_mcp_standalone
pip install -e .
```

## 各工具详情

请参阅各个工具目录下的README.md文件获取详细使用说明。
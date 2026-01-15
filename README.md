# MCP Tools Collection

这是一个MCP（Model Context Protocol）工具集合，包含多个独立的MCP服务工具。

## 包含的工具

### 1. icogen-mcp
- **功能**: PNG到ICO图标转换工具
- **用途**: 将PNG图像文件转换为Windows ICO图标文件，支持多种尺寸

### 2. runcmd-mcp
- **功能**: 异步命令执行工具
- **用途**: 异步执行系统命令并查询执行状态

## 项目结构

```
mcp_tools_collection/
├── icogen_mcp_standalone/      # PNG转ICO工具独立项目
│   ├── src/
│   │   └── icogen_mcp/
│   ├── pyproject.toml
│   ├── README.md
│   └── LICENSE
├── runcmd_mcp_standalone/      # 异步命令执行工具独立项目
│   ├── src/
│   │   └── runcmd_mcp/
│   ├── pyproject.toml
│   ├── README.md
│   └── LICENSE
└── README.md                   # 本文件
```

## 安装说明

每个工具都是独立的Python包，可以分别安装：

### 安装icogen-mcp
```bash
cd mcp_tools_collection/icogen_mcp_standalone
pip install -e .
```

### 安装runcmd-mcp
```bash
cd mcp_tools_collection/runcmd_mcp_standalone
pip install -e .
```

也可以通过可选依赖安装特定工具：
```bash
# 安装icogen-mcp
pip install -e .[icogen]

# 安装runcmd-mcp
pip install -e .[runcmd]

# 安装所有工具
pip install -e .[all]
```

## 各工具详情

请参阅各个工具目录下的README.md文件获取详细使用说明。
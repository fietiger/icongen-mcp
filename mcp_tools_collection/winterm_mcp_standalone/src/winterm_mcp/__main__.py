"""
winterm-mcp 主入口
"""

from .server import app, init_service
from .service import RunCmdService


def main():
    """
    主函数，启动 MCP 服务器
    """
    service = RunCmdService()
    init_service(service)
    app.run()


if __name__ == "__main__":
    main()

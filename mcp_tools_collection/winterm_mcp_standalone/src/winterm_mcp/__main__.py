"""
winterm-mcp 主入口
"""

from .server import app, init_service
from .service import CommandService, setup_logging, __version__
import logging
import os
import tempfile


def main():
    """
    主函数，启动 MCP 服务器
    """
    setup_logging(logging.INFO)

    logger = logging.getLogger("winterm-mcp")

    log_file = os.environ.get("WINTERM_LOG_FILE") or os.path.join(
        tempfile.gettempdir(), "winterm-mcp.log"
    )

    logger.info("=" * 60)
    logger.info(f"winterm-mcp v{__version__} starting...")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Temp dir: {tempfile.gettempdir()}")
    logger.info(f"Working dir: {os.getcwd()}")
    logger.info(
        f"WINTERM_POWERSHELL_PATH: "
        f"{os.environ.get('WINTERM_POWERSHELL_PATH', '(not set)')}"
    )
    logger.info("=" * 60)

    service = CommandService()
    init_service(service)

    logger.info("Service initialized, starting MCP server...")
    app.run()


if __name__ == "__main__":
    main()

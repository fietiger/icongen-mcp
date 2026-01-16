from .server import app, init_service
from .service import PkgPublisherService, setup_logging, __version__
import logging
import os
import tempfile


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="Python包构建和发布MCP服务")
    return parser.parse_args()


def main():
    setup_logging(logging.INFO)
    
    logger = logging.getLogger("pkg-publisher")
    
    log_file = os.environ.get("PKG_PUBLISHER_LOG_FILE") or os.path.join(
        tempfile.gettempdir(), "pkg-publisher.log"
    )
    
    logger.info("=" * 60)
    logger.info(f"pkg-publisher v{__version__} starting...")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Temp dir: {tempfile.gettempdir()}")
    logger.info(f"Working dir: {os.getcwd()}")
    logger.info(f"PYPI_API_TOKEN: {'(set)' if os.environ.get('PYPI_API_TOKEN') else '(not set)'}")
    logger.info(f"TEST_PYPI_API_TOKEN: {'(set)' if os.environ.get('TEST_PYPI_API_TOKEN') else '(not set)'}")
    logger.info("=" * 60)
    
    service = PkgPublisherService()
    init_service(service)
    
    logger.info("Service initialized, starting MCP server...")
    app.run()


if __name__ == "__main__":
    main()

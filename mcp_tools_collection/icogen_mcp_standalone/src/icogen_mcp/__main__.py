from .server import app, init_service
from .service import IcoGeneratorService


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="将PNG文件转换为ICO文件的MCP服务")
    return parser.parse_args()


def main():
    # 初始化服务
    service = IcoGeneratorService()
    init_service(service)

    # 运行服务器
    app.run()


if __name__ == "__main__":
    main()

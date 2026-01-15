from .server import app, init_service
from .service import RunCmdService


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="异步执行系统命令的MCP服务")
    return parser.parse_args()


def main():
    # 初始化服务
    service = RunCmdService()
    init_service(service)

    # 运行服务器
    app.run()


if __name__ == "__main__":
    main()
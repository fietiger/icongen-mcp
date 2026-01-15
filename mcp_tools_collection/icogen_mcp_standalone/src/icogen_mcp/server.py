from __future__ import annotations

from typing import Annotated, Optional, List, Any, Dict
from mcp.server.fastmcp import FastMCP
from .service import IcoGeneratorService
from pydantic import Field

PngPath = Annotated[
    str,
    Field(
        description="PNG源文件的完整路径，必须是有效的PNG图像文件",
        pattern=r".*\.png$",
        min_length=1,
        max_length=500,
    ),
]
IcoPath = Annotated[
    Optional[str],
    Field(
        description="ICO输出文件的路径，如果不指定则在源文件同目录下生成同名ICO文件",
        pattern=r".*\.ico$",
        default=None,
        max_length=500,
    ),
]
SizeNoted = Annotated[
    Optional[List[List[int]]],
    Field(
        description="ICO文件包含的图标尺寸列表，每个子列表包含[宽度, 高度]，如[[16,16], [32,32], [48,48]]。如果不指定，将使用标准尺寸：16x16, 32x32, 48x48, 64x64",
        default=None,
        examples=[
            [[16, 16], [32, 32]],
            [[16, 16], [32, 32], [48, 48], [64, 64]],
            [[256, 256]],
        ],
    ),
]
# FastMCP app
app = FastMCP("icogen-mcp")

# Injected at runtime by __main__.py
_service: Optional[IcoGeneratorService] = None


def init_service(service: IcoGeneratorService) -> None:
    global _service
    _service = service


def _svc() -> IcoGeneratorService:
    if _service is None:
        raise RuntimeError(
            "Service not initialized. Call init_service() before running the server."
        )
    return _service


# ------------------ Tools ------------------


@app.tool(
    name="convert_png_to_ico",
    description="将PNG图像文件(提供完整文件路径)转换为Windows ICO图标文件，支持多种尺寸和自定义输出路径",
    annotations={
        "title": "PNG转ICO转换器",
        "readOnlyHint": False,  # 会创建新文件，不是只读操作
        "destructiveHint": False,  # 不会破坏原文件，只是创建新文件
        "idempotentHint": True,  # 相同输入会产生相同输出
        "openWorldHint": True,  # 与文件系统交互
    },
)
def convert_png_to_ico(
    png_path: PngPath, output_path: IcoPath = None, sizes: SizeNoted = None
) -> Dict[str, Any]:
    """
    将PNG文件转换为ICO文件

    参数:
        png_path (str): PNG文件路径
        output_path (str, optional): 输出ICO文件的路径，如果为None则返回二进制数据
        sizes (list, optional): ICO文件中包含的图标尺寸列表，默认为[[16,16], [32,32], [48,48]]

    返回:
        dict: 包含成功信息或错误信息的字典
    """
    try:
        # 转换尺寸参数
        size_tuples = None
        if sizes is not None:
            size_tuples = [tuple(size) for size in sizes]  # type: ignore

        # 调用服务生成ICO
        result = _svc().png_to_ico(png_path, output_path, size_tuples)

        if output_path:
            return {"success": True, "message": f"ICO文件已生成: {output_path}"}
        else:
            # 将二进制数据转换为十六进制字符串返回
            return {"success": True, "data": result.hex() if result else ""}
    except Exception as e:
        return {"success": False, "error": str(e)}

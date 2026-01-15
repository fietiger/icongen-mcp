import io
from typing import Optional, List, Tuple
from PIL import Image


class IcoGeneratorService:
    """
    核心ICO生成服务:
    - 将PNG文件转换为ICO文件
    - 支持自定义ICO文件中的图标尺寸
    - 可以将生成的ICO文件保存到指定路径或返回二进制数据
    """

    def __init__(self):
        pass

    def png_to_ico(
        self,
        png_path: str,
        output_path: Optional[str] = None,
        sizes: Optional[List[Tuple[int, int]]] = None,
    ) -> Optional[bytes]:
        """
        将PNG文件转换为ICO文件

        参数:
            png_path (str): PNG文件路径
            output_path (str, optional): 输出ICO文件的路径，如果为None则返回二进制数据
            sizes (list, optional): ICO文件中包含的图标尺寸列表，默认为[(16,16), (32,32), (48,48)]

        返回:
            bytes: 如果output_path为None，则返回ICO文件的二进制数据
            None: 如果output_path不为None，则将ICO文件保存到指定路径
        """
        if sizes is None:
            sizes = [(16, 16), (32, 32), (48, 48)]

        # 打开PNG图像
        original_img = Image.open(png_path)

        # 创建一个内存中的ICO文件
        ico_buffer = io.BytesIO()

        # 创建不同尺寸的图像列表
        images = []
        for size in sizes:
            # 调整图像大小
            resized_img = original_img.resize(size, Image.Resampling.LANCZOS)
            images.append(resized_img)

        # 保存为ICO文件
        if images:
            images[0].save(
                ico_buffer, format="ICO", append_images=images[1:], sizes=sizes
            )
            ico_data = ico_buffer.getvalue()

            # 保存到文件或返回二进制数据
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(ico_data)
                return None
            else:
                return ico_data
        else:
            raise ValueError("未能创建任何图像")

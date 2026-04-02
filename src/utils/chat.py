import io
import os
import sys
import re
import json
import uuid
import time
import base64
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image

try:
    from src.utils.log import logger
except ImportError:
    # 定位到 src 这一级
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    from src.utils.log import logger


class ChatUtils:
    """
    聊天相关工具
    """
    def __init__(self, root_dir):
        self.root_dir = root_dir
        # 用户聊天数据的根目录
        self.chat_dir = os.path.abspath(os.path.join(self.root_dir, "data/chat"))
        # 用户聊天的临时根目录
        self.temp_dir = os.path.abspath(os.path.join(self.root_dir, "temp"))
        # 确保指定目录存在
        for dir in [self.chat_dir, self.temp_dir]:
            if not Path(dir).exists():
                try:
                    Path(dir).mkdir(parents=True, exist_ok=True)
                    logger.warning(f"Created folder: {dir}")
                except Exception as e:
                    logger.error(e)

        # 聊天对话排序列表 & 聊天对话文件名
        self.chat_list_with_sort_ids = []
        self.chat_list_with_file = []

        # 聊天对话排序列表对应的文件
        self.sort_file = os.path.abspath(os.path.join(self.chat_dir, "chat_list_ids.sort"))

    def generate_safe_filename(self, original_string, max_len=20):
        """
        基于传入的字符串来生成符合文件名的字符串
        """
        # 移除非法字符 (Windows/Linux/Mac通用)
        safe_string = re.sub(r'[<>:"/\\|?*]', '', original_string) or "untitled_session"
        # 如果过长则截取到最大长度
        safe_string = safe_string[:max_len] if len(safe_string) > max_len else safe_string
        return safe_string
    
    def generate_unique_chatfile(self, session_name=None):
        """
        生成用于保存对话数据的文件名, 详细规则为:
        
        - 如果没传入 session_name, 则文件名为: <date>_<uuid[:16]>_default_session.json
        - 如果传入了 session_name, 则文件名为: <date>_<uuid[:16]>_<session_name>.json
        - 如果传入了 session_name 但不合法, 则文件名为: <date>_<uuid[:16]>_untitled_session.json
        """
        # Time 前缀
        time_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
        # UUID 前缀
        full_uuids = str(uuid.uuid1()).replace('-', '')
        uuid_prefix = full_uuids[:16]
        # Index 前缀
        index_prefix = f"{time_prefix}_{uuid_prefix}".lower()
        
        if session_name is None:
            filename = f"{index_prefix}_default_session.json"
        else:
            safe_session_name = self.generate_safe_filename(original_string=session_name)
            filename = f"{index_prefix}_{safe_session_name}.json"

        full_path = os.path.abspath(os.path.join(self.chat_dir, filename))
        with open(full_path, "w", encoding="utf-8") as f:
            try:
                from src.utils.globals import app_chat_default
            except ImportError:
                from globals import app_chat_default
            json.dump(app_chat_default, ensure_ascii=True, fp=f)
            logger.debug(f"A new session has been created, fullname is: {filename}")
        
        # 同步 chat_list 相关数据/缓存
        self.sync_chat_list_by_add(filename)

    def get_chat_list_with_file(self) -> List[str]:
        """
        获取所有的对话列表文件名 & 同步一个完整的路径
        """
        directory = Path(self.chat_dir)
        jsonfiles = [f.name for f in directory.iterdir() if f.is_file() and f.suffix == '.json']
        if len(jsonfiles) == 0:
            self.generate_unique_chatfile()
            jsonfiles = [f.name for f in directory.iterdir() if f.is_file() and f.suffix == '.json']
        self.chat_list_with_file = jsonfiles
        return jsonfiles

    def get_chat_list_with_sort(self) -> List[str]:
        """
        获取所有 "已排序" 的 "对话列表索引" id
        """       
        directory = Path(self.chat_dir)

        # 提前处理对话数据
        jsonfiles = self.get_chat_list_with_file()

        # 如果排序文件不存在
        if not Path(self.sort_file).exists():
            self.chat_list_with_sort_ids = [file[:32] for file in jsonfiles]
            with open(self.sort_file, "w", encoding="utf-8") as f:
                json.dump(self.chat_list_with_sort_ids, fp=f)
                f.flush()  # 显式刷新缓冲区

        # 排序文件存在, 且当前排序数据为空
        elif len(self.chat_list_with_sort_ids) == 0:
            with open(self.sort_file, "r", encoding="utf-8") as f:
                self.chat_list_with_sort_ids = json.load(f)
            if len(self.chat_list_with_sort_ids) == 0:
                self.chat_list_with_sort_ids = [file[:32] for file in jsonfiles]
                with open(self.sort_file, "w", encoding="utf-8") as f:
                    json.dump(self.chat_list_with_sort_ids, fp=f)
                    f.flush()  # 显式刷新缓冲区
        
        # 排序数据非空
        else:
            pass    # 仅为理解逻辑结构, 这块可以删掉

        return self.chat_list_with_sort_ids
        
    def sync_chat_list_by_add(self, filename):
        """
        增加 chat_list 相关项, 并同时维护缓存
        """
        self.chat_list_with_sort_ids.append(filename[:32])
        self.chat_list_with_file.append(filename)
        # 更新排序文件缓存
        with open(self.sort_file, "w", encoding="utf-8") as f:
            json.dump(self.chat_list_with_sort_ids, fp=f)
            f.flush()  # 显式刷新缓冲区
    
    def sync_chat_list_by_delete(self, filename):
        """
        删除 chat_list 相关项, 并同时维护缓存
        """
        logger.debug(f"delete chat data: {filename}")
        try:
            # 维护缓存列表
            self.chat_list_with_sort_ids.remove(filename[:32])
            self.chat_list_with_file.remove(filename)
            # 更新排序文件缓存
            with open(self.sort_file, "w", encoding="utf-8") as f:
                json.dump(self.chat_list_with_sort_ids, fp=f)
                f.flush()  # 显式刷新缓冲区
            # 删除指定文件
            Path(os.path.abspath(os.path.join(self.chat_dir, filename))).unlink()
        except Exception as e:
            logger.error(e)
    
    def sync_chat_list_by_rename(self, old_filename, new_filename):
        """
        重命名 chat_list 对应文件, 并同时维护缓存
        """
        # 重命名文件
        old_abs_path = os.path.abspath(os.path.join(self.chat_dir, old_filename))
        new_abs_path = os.path.abspath(os.path.join(self.chat_dir, new_filename))
        Path(os.path.abspath(old_abs_path)).rename(new_abs_path)
        # 调整缓存
        idx = self.chat_list_with_file.index(old_filename)
        self.chat_list_with_file[idx] = new_filename
        # 当前文件列表
        logger.debug(f"chat_list_with_file: {self.chat_list_with_file}")

    def get_chat_details_data_with_filename(self, filename, max_retries=5, interval=0.2):
        """
        基于指定文件来加载 json 数据

        Args:
        - filename:     要读取的 JSON 文件名
        - max_retries:  最大重试次数, 默认 5次
        - interval:     每次重试的间隔时间, 默认 0.2s
        """
        full_filepath = os.path.abspath(os.path.join(self.chat_dir, filename))
        # 循环检查
        for n in range(max_retries):
            if Path(full_filepath).exists():
                break
            logger.warning(f"chat_details file not found, will attempt to check again, currently count: {n+1}")
            time.sleep(interval)
        try:
            with open(full_filepath, "r", encoding="utf-8") as f:
                chat_data = json.load(fp=f)
            return chat_data
        except Exception as e:
            logger.error(e)
            return None
    
    def save_chat_details_data_with_filename(self, filename, chat_details_data):
        """
        基于指定文件来保持 chat_detail_data
        """
        with open(os.path.abspath(os.path.join(self.chat_dir, filename)), "w", encoding="utf-8") as f:
            json.dump(chat_details_data, fp=f, ensure_ascii=False)
            f.flush()

    def get_images_with_temp(self, session_prefix=None):
        """
        从 "temp" 里获取指定图片的名字列表

        Args:
        - session_prefix:   指定要搜索的图片前缀
        """
        directory = Path(self.temp_dir)
        if session_prefix is not None:
            images = [f.name for f in directory.iterdir() if f.is_file() and f.suffix == '.png' and f.name.startswith(session_prefix)]
        else:
            images = [f.name for f in directory.iterdir() if f.is_file() and f.suffix == '.png']
        # 列表不为空则返回列表, 否则返回 None
        return images if len(images) > 0 else None
    
    def add_image_with_temp(self, session_prefix, data):
        """
        将图标保存在 "temp" 文件夹里

        Args:
        - session_prefix:   当前对话的 session 前缀: <date>_<uuid>
        - data:             剪切板里的原始数据
        """
        directory = Path(self.temp_dir)
        images = [f.name for f in directory.iterdir() if f.is_file() and f.suffix == '.png' and f.name.startswith(session_prefix)]
        num = 1
        
        while True:
            filename = f"{session_prefix}_screenshot_{str(num)}.png"
            if filename not in images:
                filepath = os.path.abspath(os.path.join(self.temp_dir, filename))
                # 用 Pillow 从字节流解析图片, 再重新保存为标准 PNG
                with Image.open(io.BytesIO(data)) as img:
                    logger.debug(f"clipboard image info: format={img.format}, mode={img.mode}, size={img.size}")
                    # 为了兼容性, 统一转成 RGBA 或 RGB
                    if img.mode not in ("RGB", "RGBA"):
                        img = img.convert("RGBA")
                    img.save(filepath, format="PNG")
                logger.debug(f"Screenshot filename: {filename}")
                break
            num += 1
    
    def file_to_base64_uri(self, file_path: str) -> str:
        """
        将本地文件路径转换为 Data URI (Base64 格式)

        Args:
        - file_path:    图片的绝对或相对路径

        Returns:
        - str:          形如 "data:image/png;base64,iVBORw0KGgo..." 的数据 URI 字符串
        """
        path = Path(file_path)
        # 1.读取文件内容 (二进制模式)
        with open(path, "rb") as image_file:
            encoded_bytes = base64.b64encode(image_file.read())
        # 2.将字节转换为字符串 (去掉 b'...')
        encoded_str = encoded_bytes.decode('utf-8')
        # 3.自动检测图片的 MIME 类型 (例如 'image/png', 'image/jpeg')
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            # 如果识别不出来则给个默认值
            mime_type = "application/octet-stream"
        # 4.组装成标准的 Data URI 格式
        data_uri = f"data:{mime_type};base64,{encoded_str}"
        
        logger.debug(f"base64_data_uri: {data_uri[:32]}")
        return data_uri
    
    def delete_tempfile_with_filename(self, filename: str):
        """
        基于文件名来删除临时文件夹里的指定文件
        """
        try:
            Path(os.path.abspath(os.path.join(self.temp_dir, filename))).unlink()
        except Exception as e:
            logger.error(e)
    
    def delete_tempfiles_with_prefix(self, prefix=None):
        """
        基于前缀来来删除临时文件夹里的指定文件
        """
        directory = Path(self.temp_dir)
        if prefix is not None:
            filenames = [f.name for f in directory.iterdir() if f.is_file() and f.name.startswith(prefix)]
            for filename in filenames:
                try:
                    Path(os.path.abspath(os.path.join(self.temp_dir, filename))).unlink()
                except Exception as e:
                    logger.error(e)


if __name__ == "__main__":
    # 测试代码
    chat_utils = ChatUtils("./storage/data")
    # chat_utils.generate_unique_chatfile()
    # chat_utils.get_chat_list_with_sort()
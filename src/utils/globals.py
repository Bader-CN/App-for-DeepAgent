import sys
from pathlib import Path
try:
    from src.utils.log import logger
    from src.utils.config import ConfigUtils
    from src.utils.chat import ChatUtils
    from src.core.agent import Agent
except ImportError:
    # 定位到 src 这一级
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    from src.utils.log import logger
    from src.utils.config import ConfigUtils
    from src.utils.chat import ChatUtils
    from src.core.agent import Agent

# 配置文件默认值
app_config_default = {
    # 模型服务
    "model_services": [{
        "display_name": "default_service",
        "enable": False,
        "config": {
            "model_provider": "ollama",
            "base_url": "http://localhost:11434",
            "model_name": "<model_name>",
            "api_key": "<api_key>",
            "max_tokens": 4096,
        }
    }]
}
# 聊天数据字典模板
app_chat_default = {
    "messages": [],
    "metadata": {},
}
# 配置文件对象
app_config = ConfigUtils(file_path="./storage/data/config.yaml", default_config=app_config_default)
# 聊天数据工具
app_chat_utils = ChatUtils(root_dir="./storage")

# 智能体对象
app_agent = Agent()
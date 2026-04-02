import sys
from pathlib import Path
from typing import Any, Dict, List
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.chat_models import init_chat_model

try:
    from src.utils.log import logger
except ImportError:
    # 定位到 src 这一级
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    from src.utils.log import logger

class Agent:
    """
    智能体类, 会在这里创建各种智能体
    """
    def __init__(self):
        self.agent_main = None
        self.agent_summary = None

    def get_agent_main(self, display_name, workdir=None):
        """
        返回 "主智能体" 对象
        """
        # 处理导入问题
        try:
            from src.utils.globals import app_config
        except ImportError:
            # 定位到 src 这一级
            sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
            from src.utils.globals import app_config
        # 基于 "配置" 创建语言模型
        cfg_model = app_config.get_model_service_by_display_name(display_name)
        self.chat_main_model = init_chat_model(
            model_provider=cfg_model["config"].get("model_provider"),
            # model 也可以写为 <model_provider>:<model_name> 的形式
            # 这样就可以不用指定 model_provider 这个参数了
            model=cfg_model["config"].get("model_name"),
            base_url = cfg_model["config"].get("base_url"),
            api_key = cfg_model["config"].get("api_key"),
            max_tokens = cfg_model["config"].get("max_tokens"),
        )
        # 基于 "语言模型" 构建智能体
        self.agent_main = create_deep_agent(
            model=self.chat_main_model,
            # 提示词可以不写, 这样也可以在调用时用 SystemMessage 来指定
            # system_prompt="你是一个专业的AI助手, 请用简洁的方式回复用户的问题.",
            # 文件系统
            backend=FilesystemBackend(root_dir="./aiwork", virtual_mode=True),
        )
        return self.agent_main

    def get_agent_summary(self):
        """
        返回 "总结智能体" 对象
        """
        # 处理导入问题
        try:
            from src.utils.globals import app_config
        except ImportError:
            # 定位到 src 这一级
            sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
            from src.utils.globals import app_config
        
        # 基于 "配置" 创建 "总结智能体"
        display_name = app_config.get_default_model_with_summary()
        cfg_model = app_config.get_model_service_by_display_name(display_name)
        self.agent_summary = init_chat_model(
            model_provider=cfg_model["config"].get("model_provider"),
            # model 也可以写为 <model_provider>:<model_name> 的形式
            # 这样就可以不用指定 model_provider 这个参数了
            model=cfg_model["config"].get("model_name"),
            base_url = cfg_model["config"].get("base_url"),
            api_key = cfg_model["config"].get("api_key"),
            max_tokens = cfg_model["config"].get("max_tokens"), 
        )
        logger.debug(f"Model for Summary loading complete: {display_name}")
        return self.agent_summary

if __name__ == "__main__":
    app_agent = Agent()
    app_agent.get_agent_main(display_name="qwen3.5-122b-a10b")
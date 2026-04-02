import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List

try:
    from src.utils.log import logger
except ImportError:
    # 定位到 src 这一级
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    from src.utils.log import logger

class ConfigUtils:
    """
    配置文件工具类
    """
    def __init__(self, file_path: str, default_config: Dict):
        self.file_path = file_path
        self.yaml_dict = None
        # 文件不存在: self.yaml_dict 为默认值
        if not Path(self.file_path).exists():
            self.yaml_dict = default_config
            try:
                Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)  # 确保目录存在
                self.write_yaml()
                logger.warning("No configuration file found. A default config.yaml will be initialized.")
            except Exception as e:
                logger.error(e)
        # 文件存在: self.yaml_dict 从 yaml 文件中读取
        else:
            self.yaml_dict = self.read_yaml()

    def read_yaml(self) -> Dict[str, Any]:
        """
        读取 YAML 文件并返回解析后的 Dict 对象
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.yaml_dict = yaml.safe_load(f)
                return self.yaml_dict
        except Exception as e:
            logger.error(e)

    def write_yaml(self) -> None:
        """
        写入 YAML 文件
        """
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.yaml_dict, 
                    f, 
                    allow_unicode=True,         # 允许输出非 ASCII 字符, 而不是将其转义为 Unicode 序列（例如 \uXXXX）
                    default_flow_style=False,   # 强制 YAML 输出使用 "块风格(block style)", 即每个键值对占一行, 嵌套结构通过缩进表示
                    sort_keys=False,            # 字典键不自动按字母排序输出, 保持原始插入顺序
                    indent=2,                   # 设置缩进空格数为 2
                    width=float('inf'))         # 限制行最大宽度, 设为 float('inf') 意味着不强制换行
            logger.info("Configuration saved successfully.")
        except Exception as e:
            logger.error(e)

    def set_all_model_services(self, model_services: List[Dict]):
        """
        更新 "模型服务" 列表

        Args:
        - List[Dict]: 模型服务列表, 里面的每一项均为字典
        """
        self.yaml_dict["model_services"] = model_services
        self.write_yaml()
    
    def get_all_model_services(self) -> List[Dict]:
        """
        获取 "模型服务" 列表

        Returns:
        - List[Dict]
        """
        model_services = self.yaml_dict.get("model_services")
        return model_services
    
    def get_all_model_services_with_enable(self) -> List[Dict]:
        """
        获取 "模型服务" 列表, 但仅包含已启动的

        Returns:
        - List[Dict]
        """
        model_services_with_enable = []
        model_services = self.yaml_dict.get("model_services")
        for model_service in model_services:
            if model_service.get("enable") is True:
                model_services_with_enable.append(model_service)
        return model_services_with_enable
    
    def get_all_model_services_display_name(self) -> List[str]:
        """
        获取 "模型服务" 中所有的 display_name, 并已列表的形式返回

        Returns:
        - List[str]
        """
        model_services_display_name = []
        model_services = self.yaml_dict.get("model_services")
        for model_service in model_services:
            model_services_display_name.append(model_service.get("display_name"))
        return model_services_display_name

    def get_all_model_services_display_name_with_enable(self) -> List[str]:
        """
        获取 "模型服务" 中所有的 display_name, 并已列表的形式返回, 但仅包含已启动的

        Returns:
        - List[str]
        """
        model_services_display_name = []
        model_services = self.yaml_dict.get("model_services")
        for model_service in model_services:
            if model_service.get("enable") is True:
                model_services_display_name.append(model_service.get("display_name"))
        return model_services_display_name
    
    def get_model_service_by_display_name(self, display_name: str) -> Dict:
        """
        根据 "display_name" 返回指定的 "模型服务" 字典

        Args:
        - display_name: 要获取的服务名称

        Returns:
        - Dict / None
        """
        model_services = self.yaml_dict.get("model_services")
        for model_service in model_services:
            if model_service.get("display_name") == display_name:
                return model_service
        return None
    
    def del_model_service_by_display_name(self, display_name: str) -> None:
        """
        根据 "display_name" 来删除指定的 "模型服务"
        
        Args:
        - display_name: 要删除的服务名称
        """
        model_services = self.yaml_dict.get("model_services")
        if model_services is not None:
            # 过滤掉指定名称的服务
            self.yaml_dict["model_services"] = [service for service in model_services if service.get("display_name") != display_name]
            # 如果列表为空, 删除整个 key
            if not self.yaml_dict["model_services"]:
                del self.yaml_dict["model_services"]
            # 保存到配置文件中
            self.write_yaml()
    
    def set_default_model_with_agent(self, display_name=None):
        """
        根据 "display_name" 来设置默认的 主智能体 模型

        Args:
        - display_name: 要设置的服务名称
        """
        if "default_models" not in self.yaml_dict:
            self.yaml_dict["default_models"] = {}
            
        if display_name is None:
            self.yaml_dict["default_models"]["agent_model"] = self.get_all_model_services_display_name_with_enable()[0]
            self.write_yaml()
        else:
            self.yaml_dict["default_models"]["agent_model"] = display_name
            self.write_yaml()
    
    def set_default_model_with_summary(self, display_name=None):
        """
        根据 "display_name" 来设置默认的 总结 模型

        Args:
        - display_name: 要设置的服务名称
        """
        if "default_models" not in self.yaml_dict:
            self.yaml_dict["default_models"] = {}
            
        if display_name is None:
            self.yaml_dict["default_models"]["summary_model"] = self.get_all_model_services_display_name_with_enable()[0]
            self.write_yaml()
        else:
            self.yaml_dict["default_models"]["summary_model"] = display_name
            self.write_yaml()

    def get_default_model_with_agent(self):
        """
        获取默认的 主智能体 模型
        """
        if self.yaml_dict.get("default_models") is None or self.yaml_dict.get("default_models").get("agent_model") is None:
            self.set_default_model_with_agent()
            logger.warning(f"default agent model will set to {self.yaml_dict["default_models"]["agent_model"]}")

        return self.yaml_dict["default_models"]["agent_model"]
    
    def get_default_model_with_summary(self):
        """
        获取默认的 总结 模型
        """
        if self.yaml_dict.get("default_models") is None or self.yaml_dict.get("default_models").get("summary_model") is None:
            self.set_default_model_with_summary()
            logger.warning(f"default summary model will set to {self.yaml_dict["default_models"]["summary_model"]}")

        return self.yaml_dict["default_models"]["summary_model"]

if __name__ == "__main__":
    app_config_default = {
        # 模型服务
        "model_services": [{
            "display_name": "default_service",
            "enable": False,
            "config": {
                "model_provider": "ollama",
                "base_url": "http://localhost:11434",
                "model": "<model_name>",
                "api_key": "<api_key>",
                "max_tokens": 4096,
            }
        }]
    }
    config_utils = ConfigUtils(file_path="./storage/data/config.yaml", default_config=app_config_default)
    logger.info(config_utils.get_model_services())
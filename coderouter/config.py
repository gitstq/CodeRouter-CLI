"""
配置管理模块 / Configuration Management Module

提供配置文件的加载、保存、验证和环境变量覆盖功能。
Provides loading, saving, validation of configuration files and
environment variable override support.

配置文件格式为JSON，默认路径: ~/.coderouter/config.json
Configuration file format is JSON, default path: ~/.coderouter/config.json
"""

import json
import os
import copy
from typing import Any, Dict, List, Optional


# 默认配置模板 / Default configuration template
DEFAULT_CONFIG: Dict[str, Any] = {
    "server": {
        "host": "127.0.0.1",
        "port": 8199
    },
    "models": [],
    "routing": {
        "strategy": "priority",
        "timeout": 30,
        "max_retries": 3,
        "health_check_interval": 60
    },
    "tracker": {
        "enabled": True,
        "data_file": "~/.coderouter/stats.json"
    }
}

# 环境变量映射 / Environment variable mapping
# 格式: 环境变量名 -> 配置路径 (支持点号分隔的嵌套路径)
# Format: env var name -> config path (dot-separated nested path)
ENV_OVERRIDES: Dict[str, str] = {
    "CODEROUTER_HOST": "server.host",
    "CODEROUTER_PORT": "server.port",
    "CODEROUTER_STRATEGY": "routing.strategy",
    "CODEROUTER_TIMEOUT": "routing.timeout",
    "CODEROUTER_MAX_RETRIES": "routing.max_retries",
    "CODEROUTER_HEALTH_INTERVAL": "routing.health_check_interval",
    "CODEROUTER_TRACKER_ENABLED": "tracker.enabled",
    "CODEROUTER_TRACKER_DATA_FILE": "tracker.data_file",
}


def get_config_dir() -> str:
    """
    获取配置目录路径 / Get configuration directory path

    Returns:
        str: 配置目录的绝对路径 / Absolute path of config directory
    """
    config_dir = os.path.expanduser("~/.coderouter")
    return config_dir


def get_config_path() -> str:
    """
    获取配置文件路径 / Get configuration file path

    Returns:
        str: 配置文件的绝对路径 / Absolute path of config file
    """
    return os.path.join(get_config_dir(), "config.json")


def get_stats_path(config: Optional[Dict[str, Any]] = None) -> str:
    """
    获取统计数据文件路径 / Get statistics data file path

    Args:
        config: 配置字典，如果为None则使用默认路径 / Config dict, uses default path if None

    Returns:
        str: 统计数据文件的绝对路径 / Absolute path of stats data file
    """
    if config and "tracker" in config and "data_file" in config["tracker"]:
        return os.path.expanduser(config["tracker"]["data_file"])
    return os.path.expanduser("~/.coderouter/stats.json")


def _deep_get(data: Dict[str, Any], path: str) -> Any:
    """
    深度获取嵌套字典中的值 / Deep get value from nested dictionary

    Args:
        data: 字典数据 / Dictionary data
        path: 点号分隔的路径 / Dot-separated path

    Returns:
        Any: 找到的值，未找到返回None / Found value, None if not found
    """
    keys = path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def _deep_set(data: Dict[str, Any], path: str, value: Any) -> None:
    """
    深度设置嵌套字典中的值 / Deep set value in nested dictionary

    Args:
        data: 字典数据 / Dictionary data
        path: 点号分隔的路径 / Dot-separated path
        value: 要设置的值 / Value to set
    """
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    应用环境变量覆盖到配置 / Apply environment variable overrides to config

    从环境变量中读取配置值并覆盖到配置字典中。
    Reads config values from environment variables and overrides the config dict.

    Args:
        config: 原始配置字典 / Original config dict

    Returns:
        Dict[str, Any]: 应用环境变量后的配置 / Config after applying env overrides
    """
    result = copy.deepcopy(config)
    for env_var, config_path in ENV_OVERRIDES.items():
        env_value = os.environ.get(env_var)
        if env_value is not None:
            # 尝试转换为适当的类型 / Try to convert to appropriate type
            current_value = _deep_get(result, config_path)
            if isinstance(current_value, bool):
                _deep_set(result, config_path, env_value.lower() in ("true", "1", "yes"))
            elif isinstance(current_value, int):
                try:
                    _deep_set(result, config_path, int(env_value))
                except (ValueError, TypeError):
                    pass
            else:
                _deep_set(result, config_path, env_value)
    return result


def validate_config(config: Dict[str, Any]) -> List[str]:
    """
    验证配置文件的完整性和正确性 / Validate configuration completeness and correctness

    Args:
        config: 配置字典 / Config dict

    Returns:
        List[str]: 错误信息列表，空列表表示验证通过 / Error list, empty means valid
    """
    errors: List[str] = []

    # 验证server配置 / Validate server config
    if "server" not in config:
        errors.append("缺少 server 配置节 / Missing 'server' config section")
    else:
        server = config["server"]
        if "host" not in server:
            errors.append("缺少 server.host 配置 / Missing 'server.host' config")
        if "port" not in server:
            errors.append("缺少 server.port 配置 / Missing 'server.port' config")
        elif not isinstance(server["port"], int) or not (1 <= server["port"] <= 65535):
            errors.append(f"server.port 必须是1-65535之间的整数 / server.port must be integer between 1-65535, got: {server['port']}")

    # 验证models配置 / Validate models config
    if "models" not in config:
        errors.append("缺少 models 配置节 / Missing 'models' config section")
    else:
        if not isinstance(config["models"], list):
            errors.append("models 必须是数组 / 'models' must be a list")
        else:
            for i, model in enumerate(config["models"]):
                prefix = f"models[{i}]"
                if not isinstance(model, dict):
                    errors.append(f"{prefix} 必须是对象 / {prefix} must be an object")
                    continue
                required_fields = ["name", "endpoint", "api_key"]
                for field in required_fields:
                    if field not in model:
                        errors.append(f"{prefix} 缺少必填字段 '{field}' / {prefix} missing required field '{field}'")
                if "priority" in model and not isinstance(model["priority"], int):
                    errors.append(f"{prefix}.priority 必须是整数 / {prefix}.priority must be integer")
                if "cost_per_million_input" in model and not isinstance(model["cost_per_million_input"], (int, float)):
                    errors.append(f"{prefix}.cost_per_million_input 必须是数字 / {prefix}.cost_per_million_input must be number")
                if "cost_per_million_output" in model and not isinstance(model["cost_per_million_output"], (int, float)):
                    errors.append(f"{prefix}.cost_per_million_output 必须是数字 / {prefix}.cost_per_million_output must be number")

    # 验证routing配置 / Validate routing config
    if "routing" not in config:
        errors.append("缺少 routing 配置节 / Missing 'routing' config section")
    else:
        routing = config["routing"]
        valid_strategies = ("priority", "round_robin", "least_latency", "random")
        if "strategy" in routing and routing["strategy"] not in valid_strategies:
            errors.append(f"routing.strategy 必须是 {valid_strategies} 之一 / routing.strategy must be one of {valid_strategies}")
        if "timeout" in routing and not isinstance(routing["timeout"], (int, float)):
            errors.append("routing.timeout 必须是数字 / routing.timeout must be a number")
        if "max_retries" in routing and not isinstance(routing["max_retries"], int):
            errors.append("routing.max_retries 必须是整数 / routing.max_retries must be integer")

    # 验证tracker配置 / Validate tracker config
    if "tracker" not in config:
        errors.append("缺少 tracker 配置节 / Missing 'tracker' config section")
    else:
        tracker = config["tracker"]
        if "enabled" in tracker and not isinstance(tracker["enabled"], bool):
            errors.append("tracker.enabled 必须是布尔值 / tracker.enabled must be boolean")

    return errors


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置文件 / Load configuration file

    如果指定了路径则从该路径加载，否则从默认路径加载。
    如果配置文件不存在，则创建默认配置并返回。
    Loads from specified path or default path. Creates default config if not exists.

    Args:
        config_path: 配置文件路径，为None时使用默认路径 / Config file path, uses default if None

    Returns:
        Dict[str, Any]: 配置字典 / Config dict

    Raises:
        FileNotFoundError: 配置文件不存在且无法创建时 / When config file doesn't exist and can't be created
        json.JSONDecodeError: 配置文件JSON格式错误时 / When config file has invalid JSON
    """
    if config_path is None:
        config_path = get_config_path()

    # 展开波浪号路径 / Expand tilde path
    config_path = os.path.expanduser(config_path)

    if not os.path.exists(config_path):
        # 创建默认配置 / Create default config
        config_dir = os.path.dirname(config_path)
        os.makedirs(config_dir, exist_ok=True)
        save_config(DEFAULT_CONFIG, config_path)
        print(f"[INFO] 已创建默认配置文件: {config_path}")
        print(f"[INFO] Default config created: {config_path}")
        return copy.deepcopy(DEFAULT_CONFIG)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 应用环境变量覆盖 / Apply environment variable overrides
    config = apply_env_overrides(config)

    # 验证配置 / Validate config
    errors = validate_config(config)
    if errors:
        print("[WARN] 配置验证警告 / Config validation warnings:")
        for error in errors:
            print(f"  - {error}")

    return config


def save_config(config: Dict[str, Any], config_path: Optional[str] = None) -> None:
    """
    保存配置到文件 / Save configuration to file

    Args:
        config: 配置字典 / Config dict
        config_path: 配置文件路径，为None时使用默认路径 / Config file path, uses default if None

    Raises:
        OSError: 文件写入失败时 / When file write fails
    """
    if config_path is None:
        config_path = get_config_path()

    config_path = os.path.expanduser(config_path)
    config_dir = os.path.dirname(config_path)
    os.makedirs(config_dir, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_enabled_models(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    获取所有已启用的模型配置 / Get all enabled model configurations

    Args:
        config: 配置字典 / Config dict

    Returns:
        List[Dict[str, Any]]: 已启用的模型列表，按优先级排序 / Enabled models sorted by priority
    """
    models = config.get("models", [])
    enabled = [m for m in models if m.get("enabled", True)]
    return sorted(enabled, key=lambda m: m.get("priority", 999))


def add_model(config: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, Any]:
    """
    添加模型配置 / Add model configuration

    Args:
        config: 配置字典 / Config dict
        model: 模型配置 / Model config

    Returns:
        Dict[str, Any]: 更新后的配置 / Updated config
    """
    result = copy.deepcopy(config)
    if "models" not in result:
        result["models"] = []
    result["models"].append(model)
    return result


def remove_model(config: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """
    删除模型配置 / Remove model configuration

    Args:
        config: 配置字典 / Config dict
        model_name: 模型名称 / Model name

    Returns:
        Dict[str, Any]: 更新后的配置 / Updated config
    """
    result = copy.deepcopy(config)
    if "models" in result:
        result["models"] = [m for m in result["models"] if m.get("name") != model_name]
    return result


def update_model(config: Dict[str, Any], model_name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新模型配置 / Update model configuration

    Args:
        config: 配置字典 / Config dict
        model_name: 模型名称 / Model name
        updates: 要更新的字段 / Fields to update

    Returns:
        Dict[str, Any]: 更新后的配置 / Updated config

    Raises:
        ValueError: 模型不存在时 / When model doesn't exist
    """
    result = copy.deepcopy(config)
    if "models" in result:
        for model in result["models"]:
            if model.get("name") == model_name:
                model.update(updates)
                return result
    raise ValueError(f"模型 '{model_name}' 不存在 / Model '{model_name}' not found")

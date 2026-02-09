"""
配置加载器 (config_loader)

此模块负责从仓库中的 YAML 配置文件加载配置字典。设计目标是：
- 提供一个明确的入口 `load_default_config` 用于从项目的 `config/config.yaml` 加载默认配置；
- 提供 `load_config` 允许按路径加载自定义配置文件（便于测试或临时覆盖）；
- 对输入进行基本校验并在错误情况下抛出明确异常，方便上层捕获并记录。

示例用法：
    from src.config_loader import load_default_config
    cfg = load_default_config()

注意：此模块只负责读取并解析 YAML 为 Python 字典，不会做环境变量替换或类型转换。
实际运行时，调用方可以根据需要从 `os.environ` 中读取覆盖项。
"""

from __future__ import annotations

import os
from typing import Any, Dict

import yaml


def load_config(config_path: str) -> Dict[str, Any]:
    """从指定路径加载 YAML 配置并返回字典。

    参数:
        config_path: 配置文件的绝对或相对路径。

    返回:
        一个 Python 字典，表示 YAML 文件内容；如果文件为空，返回空字典。

    异常:
        FileNotFoundError: 当指定路径不存在时抛出，提示调用者检查路径或权限。
        ValueError: 当 YAML 根不是映射（例如根为列表或标量）时抛出，保证返回结构为 dict。

    设计说明:
        - 使用 `yaml.safe_load` 避免执行任意对象构造；
        - 以 UTF-8 打开文件，保持跨平台一致性；
        - 将空文件解析为 `{}` 以简化上层代码对键的访问逻辑。
    """
    if not os.path.exists(config_path):
        # 明确抛出文件未找到异常，便于调用端做回退（例如使用环境变量）
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        # safe_load 在解析错误时会抛出异常，调用方可捕获并记录
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        # 保证返回类型为字典，避免后来直接通过 dict.get 导致 AttributeError
        raise ValueError("Config root must be a mapping")

    return data


def load_default_config() -> Dict[str, Any]:
    """加载项目根目录下 `config/config.yaml` 并返回配置字典。

    约定：项目的源代码位于 `src/`，配置文件位于项目根的 `config/config.yaml`。
    该函数通过模块当前位置向上两级查找项目根，从而在不同工作目录下也能正确定位配置文件。

    返回值与 `load_config` 相同。
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "config.yaml")
    return load_config(config_path)


# 额外说明（供审计与调用方参考）：
# - 本模块只负责将 YAML 解析为字典；若需要使用环境变量覆盖明文配置，建议调用方在加载后执行类似：
#     cfg = load_default_config()
#     cfg['mysql']['user'] = os.getenv(cfg['mysql'].get('user_env'), cfg['mysql'].get('user'))
#   或者在 `DatabaseHandler` 中使用 `*_env` 字段（当前实现已在 `DatabaseHandler.get_mysql_engine` 中支持）。
# - 在 CI 或容器化部署中，请通过 Secrets/环境变量注入敏感信息，而不是修改 `config/config.yaml`。

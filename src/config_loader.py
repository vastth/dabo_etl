from __future__ import annotations

import os
from typing import Any, Dict

import yaml


def load_config(config_path: str) -> Dict[str, Any]:
    """Load YAML config from the given path."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping")

    return data


def load_default_config() -> Dict[str, Any]:
    """Load config/config.yaml relative to project root."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "config.yaml")
    return load_config(config_path)

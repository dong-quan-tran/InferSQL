from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


def load_config(config_path: str | Path) -> dict:
    load_dotenv()
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config.setdefault("env", {})
    config["env"]["FRED_API_KEY"] = os.getenv("FRED_API_KEY", "")
    config["env"]["MLFLOW_TRACKING_URI"] = os.getenv("MLFLOW_TRACKING_URI", "")
    return config
from pathlib import Path

import pandas as pd

from bastionquant.features.build_features import build_features
from bastionquant.settings import load_config


def test_build_features_smoke(tmp_path, monkeypatch):
    # Use real config but redirect processed_dir to a temp folder
    config = load_config("configs/base.yaml")
    config["paths"]["processed_dir"] = str(tmp_path / "processed")

    # Prepare a small synthetic panel_v1.csv in the temp processed dir
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    panel_path = processed_dir / "panel_v1.csv"

    data = {
      "date": ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04", "2020-01-05", "2020-01-06", "2020-01-07"],
      "open": [100, 101, 102, 103, 104, 105, 106],
      "high": [101, 102, 103, 104, 105, 106, 107],
      "low": [99, 100, 101, 102, 103, 104, 105],
      "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5],
      "adj_close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5],
      "volume": [1000, 1100, 1200, 1300, 1400, 1500, 1600],
      "symbol": ["TEST"] * 7,
      "cpiaucsl": [1.0] * 7,
      "dff": [1.0] * 7,
      "dgs10": [1.0] * 7,
      "dgs2": [1.0] * 7,
      "unrate": [1.0] * 7,
    }
    pd.DataFrame(data).to_csv(panel_path, index=False)

    outputs = build_features(config)
    features_path = outputs["features_path"]
    assert Path(features_path).exists()

    feats = pd.read_csv(features_path)
    assert "log_return" in feats.columns
    assert "realized_vol_5d_a" in feats.columns
    assert "vol_regime" in feats.columns
    assert feats["vol_regime"].notna().any()
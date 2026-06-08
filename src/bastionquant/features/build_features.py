from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from bastionquant.features.targets import compute_future_realized_vol, assign_vol_regimes
from bastionquant.utils.io import ensure_dir, write_csv


def build_features(config: dict) -> dict[str, Path]:
    paths_cfg = config["paths"]
    processed_dir = Path(paths_cfg["processed_dir"])
    ensure_dir(processed_dir)

    panel_path = processed_dir / "panel_v1.csv"
    if not panel_path.exists():
        raise FileNotFoundError(f"Panel file not found at {panel_path}. Run ingest first.")

    df = pd.read_csv(panel_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Core return feature
    df["log_return"] = df.groupby("symbol")["adj_close"].transform(
        lambda s: np.log(s / s.shift(1))
    )

    # Backward-looking realized volatility features
    for win in (5, 10, 21):
        df[f"vol_{win}d"] = (
            df.groupby("symbol")["log_return"]
            .transform(lambda s, w=win: s.rolling(window=w, min_periods=w).std() * np.sqrt(252))
        )

    # Momentum features
    for win in (5, 10, 21):
        df[f"mom_{win}d"] = df.groupby("symbol")["adj_close"].transform(
            lambda s, w=win: s / s.shift(w) - 1.0
        )

    # Moving-average spreads
    ma_5 = df.groupby("symbol")["adj_close"].transform(
        lambda s: s.rolling(window=5, min_periods=5).mean()
    )
    ma_10 = df.groupby("symbol")["adj_close"].transform(
        lambda s: s.rolling(window=10, min_periods=10).mean()
    )
    ma_21 = df.groupby("symbol")["adj_close"].transform(
        lambda s: s.rolling(window=21, min_periods=21).mean()
    )
    ma_50 = df.groupby("symbol")["adj_close"].transform(
        lambda s: s.rolling(window=50, min_periods=50).mean()
    )

    df["ma_spread_5_21"] = ma_5 - ma_21
    df["ma_spread_10_50"] = ma_10 - ma_50

    # Volume shock z-scores
    for win in (20, 60):
        vol_mean = df.groupby("symbol")["volume"].transform(
            lambda s, w=win: s.rolling(window=w, min_periods=w).mean()
        )
        vol_std = df.groupby("symbol")["volume"].transform(
            lambda s, w=win: s.rolling(window=w, min_periods=w).std()
        )
        df[f"vol_shock_z_{win}d"] = (df["volume"] - vol_mean) / vol_std

    # Target: next-5-day realized volatility regime
    df = compute_future_realized_vol(df, window=5)
    df = assign_vol_regimes(df, vol_col="realized_vol_5d_a")

    df = df[~df["realized_vol_5d_a"].isna()].reset_index(drop=True)

    features_path = write_csv(df.set_index("date"), processed_dir / "features_v1.csv")

    return {"features_path": features_path}
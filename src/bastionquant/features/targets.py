from __future__ import annotations

import numpy as np
import pandas as pd


def compute_future_realized_vol(
    df: pd.DataFrame,
    window: int = 5,
) -> pd.DataFrame:
    df = df.sort_values(["symbol", "date"]).copy()

    vol_col = f"realized_vol_{window}d_a"

    def _future_vol(s: pd.Series) -> pd.Series:
        future_returns = s.shift(-1)
        out = future_returns.rolling(window=window, min_periods=window).std() * np.sqrt(252)
        return out

    df[vol_col] = (
        df.groupby("symbol", group_keys=False)["log_return"]
        .transform(_future_vol)
    )

    return df


def assign_vol_regimes(
    df: pd.DataFrame,
    vol_col: str,
    low_quantile: float = 0.33,
    high_quantile: float = 0.66,
) -> pd.DataFrame:
    df = df.copy()

    valid = df[vol_col].dropna()
    if valid.empty:
        df["vol_regime"] = pd.NA
        return df

    low_thr = valid.quantile(low_quantile)
    high_thr = valid.quantile(high_quantile)

    conditions = [
        df[vol_col] <= low_thr,
        (df[vol_col] > low_thr) & (df[vol_col] < high_thr),
        df[vol_col] >= high_thr,
    ]
    choices = ["low", "medium", "high"]

    df["vol_regime"] = np.select(conditions, choices, default=None)
    df.loc[df[vol_col].isna(), "vol_regime"] = pd.NA

    return df
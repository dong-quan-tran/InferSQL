from __future__ import annotations

from pathlib import Path

from bastionquant.ingestion.macro_data import download_fred_series, pivot_macro_wide
from bastionquant.ingestion.market_data import download_market_data
from bastionquant.utils.io import ensure_dir, write_csv


def build_panel(config: dict) -> dict[str, Path]:
    data_cfg = config["data"]
    paths_cfg = config["paths"]
    env_cfg = config["env"]

    raw_dir = ensure_dir(paths_cfg["raw_dir"])
    processed_dir = ensure_dir(paths_cfg["processed_dir"])

    market_df = download_market_data(
        symbols=data_cfg["symbols"],
        start_date=data_cfg["start_date"],
        end_date=data_cfg["end_date"],
        interval=data_cfg.get("price_interval", "1d"),
    )

    macro_long = download_fred_series(
        series_ids=data_cfg["fred_series"],
        api_key=env_cfg.get("FRED_API_KEY", ""),
    )
    macro_wide = pivot_macro_wide(macro_long)

    market_path = write_csv(market_df, raw_dir / "market_data.csv")
    macro_path = write_csv(macro_long, raw_dir / "macro_data_long.csv")
    macro_wide_path = write_csv(macro_wide.set_index("date"), raw_dir / "macro_data_wide.csv")

    panel = market_df.merge(macro_wide, on="date", how="left")
    macro_cols = [c for c in panel.columns if c not in market_df.columns]
    if macro_cols:
        panel[macro_cols] = panel[macro_cols].ffill()

    panel = panel.sort_values(["symbol", "date"]).reset_index(drop=True)
    panel_path = write_csv(panel.set_index("date"), processed_dir / "panel_v1.csv")

    return {
        "market_path": market_path,
        "macro_long_path": macro_path,
        "macro_wide_path": macro_wide_path,
        "panel_path": panel_path,
    }
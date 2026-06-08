from __future__ import annotations

import pandas as pd
from fredapi import Fred


def download_fred_series(series_ids: list[str], api_key: str) -> pd.DataFrame:
    if not api_key:
        raise ValueError("FRED_API_KEY is missing. Set it in your environment or .env file.")

    fred = Fred(api_key=api_key)
    frames: list[pd.DataFrame] = []

    for series_id in series_ids:
        series = fred.get_series(series_id)
        if series is None or len(series) == 0:
            continue

        df = series.rename(series_id).to_frame().reset_index()
        df.columns = ["date", "value"]
        df["series_id"] = series_id
        frames.append(df)

    if not frames:
        raise ValueError("No macroeconomic series were returned from FRED.")

    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.sort_values(["series_id", "date"]).reset_index(drop=True)
    return out


def pivot_macro_wide(macro_long: pd.DataFrame) -> pd.DataFrame:
    wide = macro_long.pivot(index="date", columns="series_id", values="value").sort_index()
    wide = wide.ffill()
    wide.columns = [str(col).lower() for col in wide.columns]
    wide = wide.reset_index()
    return wide
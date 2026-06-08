from __future__ import annotations

import pandas as pd
import yfinance as yf


def download_market_data(
    symbols: list[str],
    start_date: str,
    end_date: str,
    interval: str = "1d",
) -> pd.DataFrame:
    data = yf.download(
        tickers=symbols,
        start=start_date,
        end=end_date,
        interval=interval,
        auto_adjust=False,
        group_by="ticker",
        progress=False,
        threads=True,
    )

    if data.empty:
        raise ValueError("No market data was returned from yfinance.")

    frames: list[pd.DataFrame] = []

    if isinstance(data.columns, pd.MultiIndex):
        for symbol in symbols:
            if symbol not in data.columns.get_level_values(0):
                continue
            symbol_df = data[symbol].copy()
            symbol_df = symbol_df.reset_index()
            symbol_df["symbol"] = symbol
            frames.append(symbol_df)
    else:
        symbol_df = data.reset_index().copy()
        symbol_df["symbol"] = symbols[0]
        frames.append(symbol_df)

    out = pd.concat(frames, ignore_index=True)
    out.columns = [str(col).strip().lower().replace(" ", "_") for col in out.columns]
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None)
    out = out.sort_values(["symbol", "date"]).reset_index(drop=True)

    expected = {"date", "symbol", "open", "high", "low", "close", "adj_close", "volume"}
    missing = expected.difference(out.columns)
    if missing:
        raise ValueError(f"Missing expected market columns: {sorted(missing)}")

    return out
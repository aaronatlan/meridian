"""
market_data.py — Récupération des données de marché via yfinance.
Fournit les données OHLCV historiques pour les actions analysées dans Meridian.
"""

import datetime
import yfinance as yf
import pandas as pd


# Périodes disponibles par timeframe
TIMEFRAME_MAP = {
    "5m":  {"period": "5d",  "interval": "5m"},
    "15m": {"period": "10d", "interval": "15m"},
    "1h":  {"period": "60d", "interval": "1h"},
    "1d":  {"period": "1y",  "interval": "1d"},
}


def fetch_ohlcv(ticker: str, timeframe: str = "1d") -> pd.DataFrame:
    """
    Récupère les données OHLCV pour un ticker donné.

    Args:
        ticker: Symbole boursier (ex: "AAPL", "MSFT")
        timeframe: Granularité — "5m", "15m", "1h", "1d"

    Returns:
        DataFrame avec colonnes: open, high, low, close, volume
        Index: datetime (UTC)

    Raises:
        ValueError: Si le timeframe est inconnu ou les données vides.
    """
    if timeframe not in TIMEFRAME_MAP:
        raise ValueError(f"Timeframe inconnu: {timeframe}. Valeurs valides: {list(TIMEFRAME_MAP.keys())}")

    params = TIMEFRAME_MAP[timeframe]

    df = yf.download(
        ticker,
        period=params["period"],
        interval=params["interval"],
        auto_adjust=True,
        progress=False,
    )

    if df.empty:
        raise ValueError(f"Aucune donnée disponible pour {ticker} ({timeframe})")

    # Normaliser les colonnes en minuscules
    df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].copy()
    df.index.name = "datetime"
    df = df.dropna()

    return df


def get_latest_price(ticker: str) -> dict:
    """
    Retourne le dernier prix et la variation 24h pour un ticker.

    Returns:
        {"price": float, "change_pct": float, "volume": int}
    """
    info = yf.Ticker(ticker).fast_info
    try:
        price = round(float(info.last_price), 2)
        prev  = round(float(info.previous_close), 2)
        change_pct = round((price - prev) / prev * 100, 2) if prev else 0.0
        volume = int(info.three_month_average_volume or 0)
        return {"price": price, "change_pct": change_pct, "volume": volume}
    except Exception:
        return {"price": 0.0, "change_pct": 0.0, "volume": 0}

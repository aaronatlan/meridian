"""
indicators.py — Calcul des indicateurs techniques sur DataFrame OHLCV.
Tous les indicateurs opèrent sur pandas Series et retournent des Series.
"""

import pandas as pd
import numpy as np


# ============================================================
# MOYENNES MOBILES
# ============================================================

def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


# ============================================================
# RSI
# ============================================================

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI).
    Valeurs: 0–100. Suracheté > 70, survendu < 30.
    """
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ============================================================
# MACD
# ============================================================

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    MACD — Moving Average Convergence Divergence.

    Returns:
        {
            "macd":      Series (ligne MACD),
            "signal":    Series (ligne de signal),
            "histogram": Series (divergence)
        }
    """
    ema_fast   = ema(series, fast)
    ema_slow   = ema(series, slow)
    macd_line  = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram   = macd_line - signal_line

    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


# ============================================================
# ATR
# ============================================================

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average True Range — mesure de volatilité.
    Plus l'ATR est élevé, plus le marché est volatil.
    """
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    return tr.ewm(alpha=1/period, adjust=False).mean()


# ============================================================
# VWAP
# ============================================================

def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Volume-Weighted Average Price (VWAP) — cumulatif sur la période.
    Référence pour distinguer achats institutionnels (au-dessus) des ventes.
    """
    typical_price = (high + low + close) / 3
    cumulative_tp_vol = (typical_price * volume).cumsum()
    cumulative_vol    = volume.cumsum()
    return cumulative_tp_vol / cumulative_vol.replace(0, np.nan)


# ============================================================
# SUPPORT / RÉSISTANCE
# ============================================================

def support_resistance(high: pd.Series, low: pd.Series, window: int = 20) -> dict:
    """
    Identifie les niveaux de support et résistance récents
    via les plus hauts/bas roulants sur `window` bougies.

    Returns:
        {"support": float, "resistance": float}
    """
    resistance = high.rolling(window=window).max().iloc[-1]
    support    = low.rolling(window=window).min().iloc[-1]
    return {
        "support":    round(float(support), 4),
        "resistance": round(float(resistance), 4),
    }


# ============================================================
# FONCTION PRINCIPALE : calcul de tous les indicateurs
# ============================================================

def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule tous les indicateurs sur un DataFrame OHLCV.

    Args:
        df: DataFrame avec colonnes open, high, low, close, volume

    Returns:
        DataFrame enrichi avec les colonnes d'indicateurs.
    """
    df = df.copy()

    df["ema20"]      = ema(df["close"], 20)
    df["ema50"]      = ema(df["close"], 50)
    df["rsi"]        = rsi(df["close"], 14)
    df["atr"]        = atr(df["high"], df["low"], df["close"], 14)
    df["vwap"]       = vwap(df["high"], df["low"], df["close"], df["volume"])

    macd_data        = macd(df["close"])
    df["macd"]       = macd_data["macd"]
    df["macd_signal"]= macd_data["signal"]
    df["macd_hist"]  = macd_data["histogram"]

    # Tendance EMA : True = EMA20 au-dessus de EMA50 (haussier)
    df["trend_bullish"] = df["ema20"] > df["ema50"]

    return df

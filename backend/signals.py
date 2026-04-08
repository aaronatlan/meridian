"""
signals.py — Moteur de signaux techniques pour Meridian.
Combine tendance, momentum, volatilité et breakout pour produire
un signal BUY / HOLD / SELL avec score de confiance.
"""

import pandas as pd
import numpy as np
from indicators import compute_all
from market_data import fetch_ohlcv, get_latest_price
from risk import compute_risk


# ============================================================
# SCORING PAR COMPOSANTE
# ============================================================

def _score_trend(row: pd.Series) -> int:
    """
    Score de tendance sur 30 points.
    Basé sur la position de EMA20 vs EMA50 et le prix vs VWAP.
    """
    score = 0
    # EMA crossover
    if row["trend_bullish"]:
        score += 20
    # Prix au-dessus du VWAP = pression acheteuse
    if row["close"] > row["vwap"]:
        score += 10
    return score


def _score_momentum(row: pd.Series) -> int:
    """
    Score de momentum sur 35 points.
    Basé sur RSI et MACD.
    """
    score = 0
    rsi = row["rsi"]

    # RSI : zone idéale entre 50 et 70 pour BUY
    if 50 < rsi < 70:
        score += 20
    elif 45 < rsi <= 50:
        score += 10
    elif rsi >= 70:
        score += 5   # suracheté, prudence
    elif rsi < 30:
        score += 15  # survendu = rebond potentiel

    # MACD : histogramme positif et croissant
    if row["macd_hist"] > 0:
        score += 10
    if row["macd"] > row["macd_signal"]:
        score += 5

    return score


def _score_volatility(row: pd.Series, df: pd.DataFrame) -> int:
    """
    Score de volatilité sur 20 points.
    ATR faible = tendance stable. ATR extrême = marché instable.
    """
    atr_mean = df["atr"].rolling(20).mean().iloc[-1]
    if pd.isna(atr_mean) or atr_mean == 0:
        return 10  # neutre par défaut

    atr_ratio = row["atr"] / atr_mean

    if 0.7 <= atr_ratio <= 1.3:
        return 20   # volatilité normale
    elif 0.5 <= atr_ratio < 0.7:
        return 15   # faible, possible compression
    elif 1.3 < atr_ratio <= 2.0:
        return 10   # volatilité élevée
    else:
        return 0    # trop chaotique


def _score_breakout(row: pd.Series, support: float, resistance: float) -> int:
    """
    Score de breakout sur 15 points.
    Détecte si le prix franchit un niveau clé.
    """
    price = row["close"]
    spread = resistance - support
    if spread == 0:
        return 8  # neutre

    # Prix proche de la résistance (dans les 2% supérieurs)
    if price >= resistance * 0.98:
        return 15
    # Prix au milieu de la range
    elif price >= (support + spread * 0.5):
        return 8
    # Prix proche du support (signal de rebond possible)
    elif price <= support * 1.02:
        return 5
    else:
        return 3


# ============================================================
# GÉNÉRATION DU SIGNAL
# ============================================================

def generate_signal(df: pd.DataFrame) -> dict:
    """
    Génère un signal de trading à partir d'un DataFrame OHLCV enrichi.

    Args:
        df: DataFrame OHLCV avec indicateurs calculés (via compute_all)

    Returns:
        {
            "signal":      "BUY" | "HOLD" | "SELL",
            "score":       int (0–100),
            "explanation": str,
            "indicators":  dict (dernières valeurs)
        }
    """
    from indicators import support_resistance

    df = compute_all(df)
    row = df.iloc[-1]

    sr = support_resistance(df["high"], df["low"], window=20)
    support    = sr["support"]
    resistance = sr["resistance"]

    # Calcul du score composite
    t_score = _score_trend(row)
    m_score = _score_momentum(row)
    v_score = _score_volatility(row, df)
    b_score = _score_breakout(row, support, resistance)
    total   = t_score + m_score + v_score + b_score  # max = 100

    # Détermination du signal
    if total >= 65:
        signal = "BUY"
    elif total <= 35:
        signal = "SELL"
    else:
        signal = "HOLD"

    # Explication humaine
    explanation = _build_explanation(signal, row, total, t_score, m_score, v_score, b_score, support, resistance)

    return {
        "signal": signal,
        "score": total,
        "explanation": explanation,
        "support": support,
        "resistance": resistance,
        "indicators": {
            "close":       round(float(row["close"]), 4),
            "ema20":       round(float(row["ema20"]), 4),
            "ema50":       round(float(row["ema50"]), 4),
            "rsi":         round(float(row["rsi"]), 1),
            "macd":        round(float(row["macd"]), 4),
            "macd_signal": round(float(row["macd_signal"]), 4),
            "macd_hist":   round(float(row["macd_hist"]), 4),
            "atr":         round(float(row["atr"]), 4),
            "vwap":        round(float(row["vwap"]), 4),
            "trend":       "haussier" if row["trend_bullish"] else "baissier",
        },
        "scores": {
            "trend":     t_score,
            "momentum":  m_score,
            "volatility": v_score,
            "breakout":  b_score,
        }
    }


def _build_explanation(signal, row, total, t, m, v, b, support, resistance) -> str:
    """Génère une explication concise du signal."""
    parts = []

    # Tendance
    if row["trend_bullish"]:
        parts.append("EMA20 au-dessus de EMA50 (tendance haussière)")
    else:
        parts.append("EMA20 sous EMA50 (tendance baissière)")

    # RSI
    rsi_val = row["rsi"]
    if rsi_val > 70:
        parts.append(f"RSI suracheté ({rsi_val:.0f})")
    elif rsi_val < 30:
        parts.append(f"RSI survendu ({rsi_val:.0f}), rebond possible")
    elif rsi_val > 50:
        parts.append(f"RSI momentum positif ({rsi_val:.0f})")
    else:
        parts.append(f"RSI faible ({rsi_val:.0f})")

    # MACD
    if row["macd_hist"] > 0:
        parts.append("MACD haussier")
    else:
        parts.append("MACD baissier")

    # Breakout
    price = row["close"]
    if price >= resistance * 0.98:
        parts.append(f"Prix proche de la résistance ({resistance:.2f})")
    elif price <= support * 1.02:
        parts.append(f"Prix proche du support ({support:.2f})")

    return f"Score {total}/100 — " + " · ".join(parts)


# ============================================================
# ANALYSE COMPLÈTE D'UN TICKER
# ============================================================

def analyze_ticker(ticker: str, timeframe: str = "1d", capital: float = 10000) -> dict:
    """
    Point d'entrée principal : récupère les données, calcule les indicateurs,
    génère le signal et calcule le risk management.

    Args:
        ticker:    Symbole boursier (ex: "AAPL")
        timeframe: "5m" | "15m" | "1h" | "1d"
        capital:   Capital disponible pour le sizing

    Returns:
        Dictionnaire complet avec signal, indicateurs et risk management.
    """
    df  = fetch_ohlcv(ticker, timeframe)
    sig = generate_signal(df)
    latest = get_latest_price(ticker)

    # Risk management
    entry = sig["indicators"]["close"]
    atr_val = sig["indicators"]["atr"]
    risk = compute_risk(entry=entry, atr=atr_val, capital=capital)

    return {
        "ticker":    ticker,
        "timeframe": timeframe,
        "price":     latest,
        "signal":    sig["signal"],
        "score":     sig["score"],
        "explanation": sig["explanation"],
        "indicators": sig["indicators"],
        "scores":    sig["scores"],
        "support":   sig["support"],
        "resistance": sig["resistance"],
        "risk":      risk,
    }

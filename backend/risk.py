"""
risk.py — Gestion du risque et sizing de position pour Meridian.
Calcule stop loss, take profit et taille de position selon l'ATR.
"""


# ============================================================
# PARAMÈTRES PAR DÉFAUT
# ============================================================

RISK_PER_TRADE = 0.01   # 1% du capital risqué par trade
ATR_MULTIPLIER = 1.5    # Distance du stop loss = 1.5x ATR
REWARD_RATIO   = 2.0    # Risk/Reward minimum = 1:2


def compute_risk(entry: float, atr: float, capital: float = 10000,
                 risk_pct: float = RISK_PER_TRADE,
                 atr_mult: float = ATR_MULTIPLIER,
                 rr_ratio: float = REWARD_RATIO) -> dict:
    """
    Calcule les niveaux de risque et la taille de position optimale.

    Logique :
    - Stop loss = entry - (ATR × atr_mult)
    - Take profit = entry + (stop_distance × rr_ratio)
    - Position size = (capital × risk_pct) / stop_distance

    Args:
        entry:     Prix d'entrée
        atr:       Average True Range courant
        capital:   Capital total disponible (en $)
        risk_pct:  Pourcentage du capital à risquer (défaut : 1%)
        atr_mult:  Multiplicateur ATR pour le stop (défaut : 1.5)
        rr_ratio:  Ratio risque/rendement minimum (défaut : 2.0)

    Returns:
        {
            "entry":         float,
            "stop_loss":     float,
            "take_profit":   float,
            "stop_distance": float,
            "position_size": float  (en unités/actions),
            "risk_amount":   float  (en $),
            "rr_ratio":      float,
        }
    """
    if atr <= 0 or entry <= 0:
        return _empty_risk(entry)

    stop_distance = atr * atr_mult
    stop_loss     = round(entry - stop_distance, 4)
    take_profit   = round(entry + stop_distance * rr_ratio, 4)
    risk_amount   = round(capital * risk_pct, 2)
    position_size = round(risk_amount / stop_distance, 4) if stop_distance > 0 else 0

    return {
        "entry":         round(entry, 4),
        "stop_loss":     stop_loss,
        "take_profit":   take_profit,
        "stop_distance": round(stop_distance, 4),
        "position_size": position_size,
        "risk_amount":   risk_amount,
        "rr_ratio":      rr_ratio,
    }


def _empty_risk(entry: float) -> dict:
    """Retourne un dict vide si les données sont insuffisantes."""
    return {
        "entry":         round(entry, 4),
        "stop_loss":     None,
        "take_profit":   None,
        "stop_distance": None,
        "position_size": None,
        "risk_amount":   None,
        "rr_ratio":      REWARD_RATIO,
    }

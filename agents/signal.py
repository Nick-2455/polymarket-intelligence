"""Signal classification based on edge and consensus."""


def classify_signal(edge: float, consensus: float) -> str:
    if edge > 2.0 and consensus > 4.0:
        return "STRONG_BUY"
    if edge > 2.0 and consensus < -4.0:
        return "STRONG_SELL"
    if edge > 1.0 and abs(consensus) > 6.0:
        return "WATCH"
    return "IGNORE"

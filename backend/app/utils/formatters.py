"""Utilidades de formato compartidas en toda la app."""

import math


def fmt_lap_time(seconds: float) -> str:
    """Formatea un tiempo de vuelta en segundos a M:SS.mmm.

    Devuelve "—" para valores inválidos (0, negativo, nan, inf).
    """
    if (
        not isinstance(seconds, (int, float))
        or seconds <= 0
        or math.isnan(seconds)
        or math.isinf(seconds)
    ):
        return "—"
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m}:{s:06.3f}"

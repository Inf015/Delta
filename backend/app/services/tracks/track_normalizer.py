"""
Normaliza los track IDs de Assetto Corsa al nombre base del circuito.

Ejemplos:
  rt_suzuka_layout_f1_2023  → suzuka
  ks_monza                  → monza
  ac_spa                    → spa
  nurburgring_layout_gp     → nurburgring
"""

from __future__ import annotations
import re

# Prefijos comunes de AC y mods
_PREFIXES = ("rt_", "ks_", "ac_", "sm_", "vrc_", "rss_")

# Sufijos / layouts a eliminar (ordenados de más largo a más corto para evitar parciales)
_LAYOUT_PATTERNS = [
    r"_layout_[a-z0-9_]+$",
    r"_f1_\d{4}$",
    r"_\d{4}$",
    r"_(gp|full|short|oval|club|national|international|endurance|junior|sprint|alt|reverse|circuit|track|racing|historical|historic|v\d+)$",
]
_LAYOUT_RE = re.compile("|".join(_LAYOUT_PATTERNS), re.IGNORECASE)


def normalize_track_id(raw: str) -> str:
    """
    Convierte un track ID crudo de AC a su nombre base normalizado.
    Retorna el string en minúsculas sin prefijos ni sufijos de layout.
    """
    if not raw:
        return raw

    # Normalizar espacios → guiones bajos antes de procesar
    s = raw.strip().lower().replace(" ", "_")

    # Quitar prefijo
    for prefix in _PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break

    # Quitar sufijos de layout (puede haber más de uno, ej: _layout_gp_2023)
    prev = None
    while prev != s:
        prev = s
        s = _LAYOUT_RE.sub("", s)

    return s

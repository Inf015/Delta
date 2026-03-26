"""
Servicio de información de circuitos.

Flujo de resolución para un track_id crudo:
  1. Normalizar el ID (quitar prefijos/sufijos AC)
  2. Lookup en la base de datos estática → instantáneo, 0 tokens
  3. Si no → buscar en tabla track_info (caché de consultas previas a Claude)
  4. Si no → llamar Claude Haiku, guardar en BD, retornar

El resultado siempre se guarda en track_info para ser reutilizado.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.track_info import TrackInfo
from app.services.tracks.track_normalizer import normalize_track_id
from app.services.tracks import static_db

logger = logging.getLogger(__name__)


def get_track_info(
    db: Session,
    raw_track_id: str,
    track_length_m: float | None = None,
) -> dict:
    """
    Retorna un dict con la info del circuito.
    Siempre retorna algo (nunca None); en el peor caso devuelve datos mínimos.
    """
    if not raw_track_id:
        return _empty(raw_track_id)

    normalized = normalize_track_id(raw_track_id)

    # ── 1. Static DB ──────────────────────────────────────────────────────────
    static = static_db.lookup(normalized)
    if static:
        # Upsert en BD para que map_path persista
        ti = db.get(TrackInfo, normalized)
        if ti is None:
            static_mapped = {k: v for k, v in static.items() if k in _TRACK_FIELDS}
            # static_db uses "type" key; model uses "track_type"
            if "track_type" not in static_mapped and "type" in static:
                static_mapped["track_type"] = static["type"]
            ti = TrackInfo(
                track_id=normalized,
                source="static",
                **static_mapped,
            )
            db.add(ti)
            db.commit()
        return _to_dict(ti, static, raw_track_id)

    # ── 2. BD caché (resultado previo de Claude) ──────────────────────────────
    ti = db.get(TrackInfo, normalized)
    if ti:
        return _to_dict(ti, None, raw_track_id)

    # ── 3. Claude fallback ────────────────────────────────────────────────────
    try:
        from app.services.ai import claude_client
        info = claude_client.get_track_info_from_claude(normalized, track_length_m)
    except Exception as exc:
        logger.warning("Claude track fallback failed for %s: %s", normalized, exc)
        info = _minimal_unknown(normalized)

    # Claude devuelve "type" pero el modelo espera "track_type"
    if "type" in info and "track_type" not in info:
        info["track_type"] = info.pop("type")
    ti = TrackInfo(
        track_id=normalized,
        source="claude",
        **{k: v for k, v in info.items() if k in _TRACK_FIELDS},
    )
    db.add(ti)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("No se pudo persistir track_info para %s: %s", normalized, exc)

    return _to_dict(ti, None, raw_track_id)


_TRACK_FIELDS = {
    "display_name", "country", "track_type", "length_m", "turns",
    "characteristics", "sectors", "key_corners", "lap_record", "notes",
}


def _to_dict(ti: TrackInfo, static: dict | None, raw_track_id: str) -> dict:
    """Convierte el modelo + datos estáticos a dict para el reporte."""
    base = static or {}
    return {
        "track_id": ti.track_id,
        "raw_track_id": raw_track_id,
        "display_name": ti.display_name or base.get("display_name") or raw_track_id,
        "country": ti.country or base.get("country"),
        "track_type": (ti.track_type if ti.track_type and ti.track_type != "unknown" else None) or base.get("type", "unknown"),
        "length_m": ti.length_m or base.get("length_m"),
        "turns": ti.turns or base.get("turns"),
        "characteristics": ti.characteristics or base.get("characteristics", []),
        "sectors": ti.sectors or base.get("sectors", []),
        "key_corners": ti.key_corners or base.get("key_corners", []),
        "lap_record": ti.lap_record or base.get("lap_record"),
        "notes": ti.notes or base.get("notes"),
        "map_path": ti.map_path,
        "has_map": bool(ti.map_path),
        "source": ti.source,
    }


def _empty(raw_track_id: str) -> dict:
    return {
        "track_id": raw_track_id,
        "raw_track_id": raw_track_id,
        "display_name": raw_track_id,
        "country": None,
        "track_type": "unknown",
        "length_m": None,
        "turns": None,
        "characteristics": [],
        "sectors": [],
        "key_corners": [],
        "lap_record": None,
        "notes": None,
        "map_path": None,
        "has_map": False,
        "source": "unknown",
    }


def _minimal_unknown(track_id: str) -> dict:
    return {
        "display_name": track_id.replace("_", " ").title(),
        "country": None,
        "track_type": "fictional",
        "length_m": None,
        "turns": None,
        "characteristics": [],
        "sectors": [],
        "key_corners": [],
        "lap_record": None,
        "notes": "Circuito no identificado en la base de datos.",
    }

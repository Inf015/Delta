"""
Tests unitarios para pre_analysis.py.
Cubre los bugs corregidos y el comportamiento esperado de cada cálculo.
"""

import math
import numpy as np
import pandas as pd
import pytest

from app.services.analysis.pre_analysis import compute


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_df(**cols) -> pd.DataFrame:
    """Crea un DataFrame mínimo con las columnas indicadas."""
    n = max(len(v) for v in cols.values())
    data = {}
    for k, v in cols.items():
        if hasattr(v, "__len__") and len(v) == n:
            data[k] = v
        else:
            data[k] = [v] * n
    return pd.DataFrame(data)


def _parsed(df: pd.DataFrame, lap_time=90.0, s1=30.0, s2=35.0, s3=25.0,
            valid=True, lap_number=1):
    """Devuelve un objeto ParsedLap simulado con telemetría."""
    from types import SimpleNamespace
    meta = SimpleNamespace(
        lap_time=lap_time, s1=s1, s2=s2, s3=s3,
        lap_time_fmt="1:30.000", valid=valid, lap_number=lap_number,
        pit_lap=False, track="test_track", car="test_car",
        simulator="AC", date="2024-01-01", event="P",
        tyre_compound="Medium", track_temp=30.0, ambient_temp=20.0,
        track_length=5000.0,
        setup=SimpleNamespace(has_data=False),
    )
    from types import SimpleNamespace as NS
    return NS(meta=meta, telemetry=df)


# ─── Tyre pressure: filtro s > 0 (no s > 1) ──────────────────────────────────

def test_tyre_pressure_includes_low_readings():
    """Presiones bajas (0.1–1.0 PSI) ya no se descartan."""
    df = _make_df(
        tyre_press_fl=[0.5] * 100,
        tyre_press_fr=[0.8] * 100,
        tyre_press_rl=[28.0] * 100,
        tyre_press_rr=[28.0] * 100,
    )
    result = compute(_parsed(df))
    press = result.get("tyre_press", {})
    # FL y FR con presión baja deben estar presentes
    assert "FL" in press
    assert press["FL"]["avg"] == pytest.approx(0.5, abs=0.1)


def test_tyre_pressure_excludes_exact_zero():
    """Presión exactamente 0 sigue siendo ignorada."""
    df = _make_df(tyre_press_fl=[0.0] * 50)
    result = compute(_parsed(df))
    assert "FL" not in result.get("tyre_press", {})


# ─── Brake balance: umbrales simétricos ───────────────────────────────────────

def test_brake_balance_front_heavy():
    """front_heavy cuando delantera > trasera × 1.30."""
    df = _make_df(
        brake_temp_fl=[500.0] * 100, brake_temp_fr=[500.0] * 100,
        brake_temp_rl=[200.0] * 100, brake_temp_rr=[200.0] * 100,
    )
    result = compute(_parsed(df))
    assert result["brake_balance"]["bias"] == "front_heavy"


def test_brake_balance_rear_heavy():
    """rear_heavy cuando trasera > delantera × 1.30."""
    df = _make_df(
        brake_temp_fl=[200.0] * 100, brake_temp_fr=[200.0] * 100,
        brake_temp_rl=[500.0] * 100, brake_temp_rr=[500.0] * 100,
    )
    result = compute(_parsed(df))
    assert result["brake_balance"]["bias"] == "rear_heavy"


def test_brake_balance_symmetric_bias():
    """El mismo ratio del 1.31x en ambas direcciones da el mismo diagnóstico."""
    # front = 131, rear = 100 → front_heavy
    df1 = _make_df(
        brake_temp_fl=[131.0] * 100, brake_temp_fr=[131.0] * 100,
        brake_temp_rl=[100.0] * 100, brake_temp_rr=[100.0] * 100,
    )
    # rear = 131, front = 100 → rear_heavy
    df2 = _make_df(
        brake_temp_fl=[100.0] * 100, brake_temp_fr=[100.0] * 100,
        brake_temp_rl=[131.0] * 100, brake_temp_rr=[131.0] * 100,
    )
    r1 = compute(_parsed(df1))
    r2 = compute(_parsed(df2))
    assert r1["brake_balance"]["bias"] == "front_heavy"
    assert r2["brake_balance"]["bias"] == "rear_heavy"


def test_brake_balance_balanced():
    """Diferencia pequeña → balanced."""
    df = _make_df(
        brake_temp_fl=[400.0] * 100, brake_temp_fr=[400.0] * 100,
        brake_temp_rl=[390.0] * 100, brake_temp_rr=[390.0] * 100,
    )
    result = compute(_parsed(df))
    assert result["brake_balance"]["bias"] == "balanced"


# ─── Weak sector: validación suma ─────────────────────────────────────────────

def test_weak_sector_valid_sum():
    """Sectores cuya suma ≈ lap_time dan weak_sector correcto."""
    parsed = _parsed(_make_df(throttle=[0.5] * 100), lap_time=90.0, s1=20.0, s2=50.0, s3=20.0)
    result = compute(parsed)
    assert result.get("weak_sector") == "S2"


def test_weak_sector_invalid_sum_skipped():
    """Sectores corruptos (suma != lap_time) no producen weak_sector."""
    # s1+s2+s3 = 200 pero lap_time = 90 → diferencia > 1s
    parsed = _parsed(_make_df(throttle=[0.5] * 100), lap_time=90.0, s1=100.0, s2=50.0, s3=50.0)
    result = compute(parsed)
    assert "weak_sector" not in result


def test_weak_sector_missing_s3():
    """Si falta s3 (= 0), no se calcula weak_sector."""
    result = compute(_parsed(_make_df(throttle=[0.5] * 100), lap_time=90.0, s1=40.0, s2=50.0, s3=0.0))
    assert "weak_sector" not in result


# ─── Fuel: validación NaN y sentido físico ────────────────────────────────────

def test_fuel_valid():
    """Consumo correcto cuando hay datos limpios."""
    fuel = list(range(100, 0, -1))  # decrece de 100 a 1
    df = _make_df(fuel=fuel)
    result = compute(_parsed(df))
    assert "fuel" in result
    assert result["fuel"]["used"] == pytest.approx(99.0, abs=0.5)


def test_fuel_ascending_ignored():
    """Si el combustible sube (datos corruptos), no se reporta."""
    df = _make_df(fuel=list(range(1, 101)))  # sube: incorrecto físicamente
    result = compute(_parsed(df))
    assert "fuel" not in result


def test_fuel_all_nan_ignored():
    """Serie de fuel completamente NaN → sin datos."""
    df = _make_df(fuel=[float("nan")] * 100)
    result = compute(_parsed(df))
    assert "fuel" not in result


# ─── Incidents: deduplicación con dist_m=None ─────────────────────────────────

def test_incidents_no_none_dedup():
    """Múltiples incidentes sin dist_m deben conservarse (no deduplicarse)."""
    # Generar kerb hits repetidos con g_vert alto
    n = 300
    g_vert = [0.0] * n
    # Tres picos en distintas posiciones
    for i in [50, 100, 200]:
        g_vert[i] = 4.0
        g_vert[i + 1] = 4.0
    df = _make_df(g_vert=g_vert)
    result = compute(_parsed(df))
    incidents = result.get("incidents", [])
    # Con dist_m=None todos se conservan (antes solo el primero)
    assert len(incidents) >= 2


# ─── Slip: columnas correctas ─────────────────────────────────────────────────

def test_slip_rl_extracted():
    """slip_rl se extrae correctamente (fix de wheelslipRearleft → wheelsliprearleft)."""
    df = _make_df(
        slip_fl=[5.0] * 100,
        slip_fr=[5.0] * 100,
        slip_rl=[20.0] * 100,  # ya renombrada por el alias correcto
        slip_rr=[5.0] * 100,
    )
    result = compute(_parsed(df))
    slip = result.get("slip", {})
    assert "RL" in slip
    assert slip["RL"]["avg"] == pytest.approx(20.0, abs=0.5)

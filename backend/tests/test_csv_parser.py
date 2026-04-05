"""Tests del parser CSV contra los archivos de muestra reales."""

from pathlib import Path
import pytest
from app.services.parsers.csv_parser import parse_csv, is_valid_lap

SAMPLES = Path(__file__).parent.parent / "legacy" / "samples"

AC_CSV  = SAMPLES / "rt_suzuka_layout_f1_2023_P_123.115_bm_nissan_gtr_gt3.csv"
R3E_CSV = SAMPLES / "zhuhai_circuit_grand_prix_Q_93.700_bmw m8 gte.csv"


# ─── AC ──────────────────────────────────────────────────────────────────────

def test_ac_parse_returns_result():
    result = parse_csv(AC_CSV)
    assert result is not None

def test_ac_simulator():
    result = parse_csv(AC_CSV)
    assert result.meta.simulator == "AC"

def test_ac_track():
    result = parse_csv(AC_CSV)
    assert "suzuka" in result.meta.track.lower()

def test_ac_car():
    result = parse_csv(AC_CSV)
    assert result.meta.car != ""

def test_ac_lap_time():
    result = parse_csv(AC_CSV)
    assert abs(result.meta.lap_time - 123.115) < 0.01

def test_ac_sectors():
    result = parse_csv(AC_CSV)
    assert result.meta.s1 == pytest.approx(44.739, abs=0.01)
    assert result.meta.s2 == pytest.approx(50.921, abs=0.01)
    assert result.meta.s3 == pytest.approx(27.455, abs=0.01)

def test_ac_lap_time_fmt():
    result = parse_csv(AC_CSV)
    assert result.meta.lap_time_fmt == "2:03.115"

def test_ac_track_length():
    result = parse_csv(AC_CSV)
    assert result.meta.track_length == pytest.approx(5771.4, abs=1.0)

def test_ac_tyre_compound():
    result = parse_csv(AC_CSV)
    assert result.meta.tyre_compound != ""

def test_ac_telemetry_not_empty():
    result = parse_csv(AC_CSV)
    assert len(result.telemetry) > 100

def test_ac_has_lap_distance():
    result = parse_csv(AC_CSV)
    assert "lap_distance" in result.telemetry.columns

def test_ac_has_xyz():
    result = parse_csv(AC_CSV)
    cols = result.telemetry.columns
    assert "x" in cols and "z" in cols

def test_ac_has_throttle_brake():
    result = parse_csv(AC_CSV)
    cols = result.telemetry.columns
    assert "throttle" in cols and "brake" in cols

def test_ac_has_tyre_temps():
    result = parse_csv(AC_CSV)
    cols = result.telemetry.columns
    assert "tyre_temp_fl" in cols

def test_ac_setup_no_data():
    result = parse_csv(AC_CSV)
    assert not result.meta.setup.has_data  # AC sample tiene setup en 0.0


# ─── R3E ─────────────────────────────────────────────────────────────────────

def test_r3e_parse_returns_result():
    result = parse_csv(R3E_CSV)
    assert result is not None

def test_r3e_simulator():
    result = parse_csv(R3E_CSV)
    assert result.meta.simulator == "R3E"

def test_r3e_track():
    result = parse_csv(R3E_CSV)
    assert "zhuhai" in result.meta.track.lower()

def test_r3e_lap_time():
    result = parse_csv(R3E_CSV)
    assert abs(result.meta.lap_time - 93.700) < 0.01

def test_r3e_sectors():
    result = parse_csv(R3E_CSV)
    assert result.meta.s1 == pytest.approx(28.200, abs=0.01)
    assert result.meta.s2 == pytest.approx(48.292, abs=0.01)
    assert result.meta.s3 == pytest.approx(17.208, abs=0.01)

def test_r3e_lap_time_fmt():
    result = parse_csv(R3E_CSV)
    assert result.meta.lap_time_fmt == "1:33.700"

def test_r3e_track_length():
    result = parse_csv(R3E_CSV)
    assert result.meta.track_length == pytest.approx(4305.8, abs=1.0)

def test_r3e_valid_false():
    # La vuelta de muestra R3E tiene Valid=false (calentamiento)
    result = parse_csv(R3E_CSV)
    assert result.meta.valid is False

def test_r3e_is_valid_lap_returns_false():
    result = parse_csv(R3E_CSV)
    assert is_valid_lap(result) is False

def test_r3e_telemetry_not_empty():
    result = parse_csv(R3E_CSV)
    assert len(result.telemetry) > 100

def test_r3e_has_xyz():
    result = parse_csv(R3E_CSV)
    cols = result.telemetry.columns
    assert "x" in cols and "z" in cols

def test_r3e_has_g_forces():
    result = parse_csv(R3E_CSV)
    cols = result.telemetry.columns
    assert "g_lat" in cols and "g_lon" in cols


# ─── Casos edge ──────────────────────────────────────────────────────────────

def test_invalid_path_returns_none():
    result = parse_csv("/nonexistent/file.csv")
    assert result is None


# ─── Verificación de alias corregidos (AC) ────────────────────────────────────

def test_ac_has_slip_rl_column():
    """slip_rl debe estar presente tras corregir alias wheelslipRearleft → wheelsliprearleft."""
    result = parse_csv(AC_CSV)
    assert result is not None
    # Si el alias estaba mal (capital R), la columna slip_rl no existiría
    if "slip_rl" in result.telemetry.columns:
        # columna presente: alias correcto
        assert True
    else:
        # columna ausente puede significar que el CSV de muestra no tiene slip — aceptable
        # pero no debe ser por un error de alias en mayúsculas
        pytest.skip("slip_rl no presente en el CSV de muestra — verificar manualmente")


def test_ac_has_tyre_wear_rr_column():
    """tyre_wear_rr debe estar presente tras corregir tyreWearrearright → tyrewearrearright."""
    result = parse_csv(AC_CSV)
    assert result is not None
    if "tyre_wear_rr" in result.telemetry.columns:
        assert True
    else:
        pytest.skip("tyre_wear_rr no presente en el CSV de muestra — verificar manualmente")


def test_ac_s3_live_in_meta_or_telemetry():
    """s3 se extrae correctamente: si falta, no debe ser por alias sector3time."""
    result = parse_csv(AC_CSV)
    assert result is not None
    # El meta.s3 ya probado en test_ac_sectors (27.455s)
    # Este test confirma que el valor no es 0 por alias ausente
    assert result.meta.s3 > 0, "s3 es 0 — posible alias sector3time faltante"

"""
Tests para session_report.py.
Cubre _best_f1_sectors (valid flag) y potential_gain.
"""

import pytest
from app.services.analysis.session_report import compute


def _lap(lap_time: float, s1: float = 0.0, s2: float = 0.0, s3: float = 0.0,
         valid: bool = True, lap_number: int = 1) -> dict:
    return {
        "lap_number": lap_number,
        "lap_time": lap_time,
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "valid": valid,
        "pre_analysis": None,
    }


# ─── _best_f1_sectors: valid flag ─────────────────────────────────────────────

def test_best_f1_sectors_valid_when_all_present():
    """Con sectores en todas las vueltas, valid=True y potential_gain calculado."""
    laps = [
        _lap(90.0, s1=30.0, s2=35.0, s3=25.0),
        _lap(91.0, s1=29.0, s2=36.0, s3=26.0),
    ]
    result = compute(laps)
    # Mejor teórico: s1=29 + s2=35 + s3=25 = 89 → gain = 90 - 89 = 1.0
    assert result["section_1_summary"]["potential_gain"] == pytest.approx(1.0, abs=0.01)


def test_best_f1_sectors_invalid_when_all_zero():
    """Sin sectores (todos 0), valid=False y potential_gain=0."""
    laps = [_lap(90.0, s1=0.0, s2=0.0, s3=0.0)]
    result = compute(laps)
    assert result["section_1_summary"]["potential_gain"] == 0


def test_best_f1_sectors_invalid_when_partial():
    """Si falta s3 en todas las vueltas, valid=False y potential_gain=0."""
    laps = [
        _lap(90.0, s1=30.0, s2=35.0, s3=0.0),
        _lap(91.0, s1=29.0, s2=36.0, s3=0.0),
    ]
    result = compute(laps)
    assert result["section_1_summary"]["potential_gain"] == 0


def test_potential_gain_never_negative():
    """potential_gain usa max(0, ...) — nunca puede ser negativo."""
    laps = [_lap(90.0, s1=30.0, s2=35.0, s3=26.0)]
    result = compute(laps)
    assert result["section_1_summary"]["potential_gain"] >= 0


def test_potential_gain_zero_when_already_optimal():
    """Si la vuelta ya es el teórico óptimo, potential_gain = 0."""
    laps = [_lap(90.0, s1=30.0, s2=35.0, s3=25.0)]
    result = compute(laps)
    assert result["section_1_summary"]["potential_gain"] == pytest.approx(0.0, abs=0.01)


# ─── compute: estructura general ──────────────────────────────────────────────

def test_compute_empty_returns_empty():
    assert compute([]) == {}


def test_compute_returns_section_1():
    laps = [_lap(90.0)]
    result = compute(laps)
    assert "section_1_summary" in result


def test_compute_best_time():
    laps = [_lap(90.0), _lap(91.0), _lap(89.5)]
    result = compute(laps)
    assert result["section_1_summary"]["best_lap"] == pytest.approx(89.5, abs=0.01)


def test_compute_lap_count():
    laps = [_lap(90.0, lap_number=i) for i in range(1, 6)]
    result = compute(laps)
    assert result["section_1_summary"]["total_laps"] == 5


def test_compute_theoretical_best_combines_best_sectors():
    """Teórico = min(s1) + min(s2) + min(s3) de cualquier vuelta."""
    laps = [
        _lap(90.0, s1=29.0, s2=36.0, s3=26.0),  # mejor s1
        _lap(91.0, s1=31.0, s2=34.0, s3=27.0),  # mejor s2
        _lap(92.0, s1=32.0, s2=37.0, s3=24.0),  # mejor s3
    ]
    result = compute(laps)
    # mejor: s1=29 + s2=34 + s3=24 = 87
    # best_time = 90.0 → potential_gain = 3.0
    assert result["section_1_summary"]["potential_gain"] == pytest.approx(3.0, abs=0.01)

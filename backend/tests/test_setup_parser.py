"""
Tests para setup_parser.py.
Cubre: front_bias float precision, compound rounding, retorno con 1 sección.
"""

import tempfile
import textwrap
from pathlib import Path

import pytest
from app.services.parsers.setup_parser import parse_setup


def _ini(content: str) -> Path:
    """Crea un archivo .ini temporal con el contenido dado."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False, encoding="utf-8")
    f.write(textwrap.dedent(content))
    f.close()
    return Path(f.name)


# ─── front_bias: float precision ──────────────────────────────────────────────

def test_front_bias_decimal_preserved():
    """67.3 no debe truncarse a 67 — round(x, 1) en lugar de int(x)."""
    p = _ini("""
        [FRONT_BIAS]
        value=67.3
    """)
    result = parse_setup(p)
    assert result is not None
    assert result["brakes"]["front_bias_pct"] == pytest.approx(67.3, abs=0.05)


def test_front_bias_rounds_to_one_decimal():
    """59.77 debe redondearse a 59.8."""
    p = _ini("""
        [FRONT_BIAS]
        value=59.77
    """)
    result = parse_setup(p)
    assert result["brakes"]["front_bias_pct"] == pytest.approx(59.8, abs=0.05)


def test_front_bias_integer_value():
    """Un bias entero como 65.0 se devuelve como float con 1 decimal."""
    p = _ini("""
        [FRONT_BIAS]
        value=65.0
    """)
    result = parse_setup(p)
    assert result["brakes"]["front_bias_pct"] == pytest.approx(65.0, abs=0.05)


# ─── compound: rounding ───────────────────────────────────────────────────────

def test_compound_rounded():
    """El compound se redondea al entero más cercano (no truncado)."""
    p = _ini("""
        [TYRES]
        value=1.9
    """)
    result = parse_setup(p)
    # round(1.9) = 2, int(1.9) = 1 → la corrección es que sea 2
    assert result["tyres"]["compound"] == 2


def test_compound_zero():
    p = _ini("""
        [TYRES]
        value=0
    """)
    result = parse_setup(p)
    assert result["tyres"]["compound"] == 0


# ─── Retorno con 1 sección ────────────────────────────────────────────────────

def test_returns_with_single_section():
    """Un setup con solo 1 sección (ej. solo FUEL) debe retornar el dict, no None."""
    p = _ini("""
        [FUEL]
        value=50
    """)
    result = parse_setup(p)
    assert result is not None
    assert result["fuel_l"] == 50


def test_returns_none_when_empty():
    """Un .ini sin secciones retorna None."""
    p = _ini("")
    result = parse_setup(p)
    assert result is None


def test_returns_none_invalid_path():
    result = parse_setup("/nonexistent/setup.ini")
    assert result is None


# ─── Casos completos ──────────────────────────────────────────────────────────

def test_full_setup_parsed():
    """Setup completo: todas las secciones se parsean correctamente."""
    p = _ini("""
        [FRONT_BIAS]
        value=58.5

        [TYRES]
        value=2

        [PRESSURE_LF]
        value=27.5

        [PRESSURE_RF]
        value=27.5

        [PRESSURE_LR]
        value=26.0

        [PRESSURE_RR]
        value=26.0

        [FUEL]
        value=40

        [ABS]
        value=4

        [TRACTION_CONTROL]
        value=2
    """)
    result = parse_setup(p)
    assert result is not None
    assert result["brakes"]["front_bias_pct"] == pytest.approx(58.5, abs=0.05)
    assert result["tyres"]["compound"] == 2
    assert result["tyres"]["pressure_psi"]["LF"] == pytest.approx(27.5, abs=0.1)
    assert result["fuel_l"] == 40
    assert result["electronics"]["abs"] == 4
    assert result["electronics"]["tc"] == 2

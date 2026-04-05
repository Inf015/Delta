"""
Tests para track_normalizer.py.
Cubre prefijos AC, sufijos de layout y casos edge.
"""

import pytest
from app.services.tracks.track_normalizer import normalize_track_id


# ─── Prefijos ─────────────────────────────────────────────────────────────────

def test_strips_rt_prefix():
    assert normalize_track_id("rt_suzuka") == "suzuka"


def test_strips_ks_prefix():
    assert normalize_track_id("ks_monza") == "monza"


def test_strips_ac_prefix():
    assert normalize_track_id("ac_spa") == "spa"


def test_strips_sm_prefix():
    assert normalize_track_id("sm_silverstone") == "silverstone"


def test_strips_vrc_prefix():
    assert normalize_track_id("vrc_nurburgring") == "nurburgring"


def test_strips_rss_prefix():
    assert normalize_track_id("rss_barcelona") == "barcelona"


def test_no_prefix_unchanged():
    assert normalize_track_id("suzuka") == "suzuka"


# ─── Sufijos de layout ────────────────────────────────────────────────────────

def test_strips_layout_suffix():
    assert normalize_track_id("rt_suzuka_layout_f1_2023") == "suzuka"


def test_strips_f1_year_suffix():
    assert normalize_track_id("suzuka_f1_2022") == "suzuka"


def test_strips_year_suffix():
    assert normalize_track_id("monza_2023") == "monza"


def test_strips_gp_suffix():
    assert normalize_track_id("nurburgring_gp") == "nurburgring"


def test_strips_full_suffix():
    assert normalize_track_id("spa_full") == "spa"


def test_strips_short_suffix():
    assert normalize_track_id("silverstone_short") == "silverstone"


def test_strips_national_suffix():
    assert normalize_track_id("brands_hatch_national") == "brands_hatch"


def test_strips_international_suffix():
    assert normalize_track_id("oulton_park_international") == "oulton_park"


def test_strips_endurance_suffix():
    assert normalize_track_id("le_mans_endurance") == "le_mans"


# ─── Combinaciones prefijo + sufijo ───────────────────────────────────────────

def test_strips_prefix_and_layout_suffix():
    assert normalize_track_id("ks_monza_layout_gp") == "monza"


def test_strips_prefix_and_year():
    assert normalize_track_id("rt_suzuka_2023") == "suzuka"


def test_full_ac_suzuka_id():
    """Caso real de Assetto Corsa: ID completo tal como viene del CSV."""
    assert normalize_track_id("rt_suzuka_layout_f1_2023") == "suzuka"


# ─── Normalización de mayúsculas y espacios ───────────────────────────────────

def test_lowercases_result():
    assert normalize_track_id("RT_Suzuka") == "suzuka"


def test_spaces_to_underscores():
    assert normalize_track_id("spa francorchamps") == "spa_francorchamps"


# ─── Casos edge ──────────────────────────────────────────────────────────────

def test_empty_string_returns_empty():
    assert normalize_track_id("") == ""


def test_only_prefix_returns_empty():
    # rt_ solo → strip prefix → ""
    result = normalize_track_id("rt_")
    assert result == ""


def test_no_modification_if_clean():
    assert normalize_track_id("spa") == "spa"

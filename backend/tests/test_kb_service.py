"""
Tests para kb_service.py.
Cubre: validación de weak_sector y decay de recurring_issues.
No usa DB real — simula KnowledgeProfile con SimpleNamespace.
"""

import uuid
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _profile(recurring: dict | None = None, sessions_count: int = 0,
             best_lap: float = 0.0, avg_lap: float = 0.0,
             trend: float = 0.0) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        track="suzuka",
        car="gt3",
        simulator="ac",
        sessions_count=sessions_count,
        best_lap=best_lap,
        avg_lap=avg_lap,
        trend=trend,
        weak_sector=None,
        recurring_issues=recurring,
        corner_profiles=None,
        common_setup=None,
    )


def _session(lap_time: float = 90.0) -> SimpleNamespace:
    return SimpleNamespace(
        lap_time=lap_time,
        track="suzuka",
        car="gt3",
        simulator=SimpleNamespace(value="ac"),
    )


def _mock_db():
    db = MagicMock()
    db.flush = MagicMock()
    return db


# ─── update_profile: weak_sector validation ───────────────────────────────────

def test_weak_sector_s1_accepted():
    """S1 es un valor válido de weak_sector."""
    from app.services.knowledge.kb_service import update_profile
    prof = _profile()
    db = _mock_db()
    update_profile(db, prof, _session(), {"weak_sector": "S1"})
    assert prof.weak_sector == "S1"


def test_weak_sector_s2_accepted():
    from app.services.knowledge.kb_service import update_profile
    prof = _profile()
    db = _mock_db()
    update_profile(db, prof, _session(), {"weak_sector": "S2"})
    assert prof.weak_sector == "S2"


def test_weak_sector_s3_accepted():
    from app.services.knowledge.kb_service import update_profile
    prof = _profile()
    db = _mock_db()
    update_profile(db, prof, _session(), {"weak_sector": "S3"})
    assert prof.weak_sector == "S3"


def test_weak_sector_garbage_rejected():
    """Valores corruptos como 'sector2' no se escriben en el perfil."""
    from app.services.knowledge.kb_service import update_profile
    prof = _profile()
    db = _mock_db()
    update_profile(db, prof, _session(), {"weak_sector": "sector2"})
    assert prof.weak_sector is None


def test_weak_sector_numeric_rejected():
    from app.services.knowledge.kb_service import update_profile
    prof = _profile()
    db = _mock_db()
    update_profile(db, prof, _session(), {"weak_sector": "2"})
    assert prof.weak_sector is None


def test_weak_sector_none_skipped():
    from app.services.knowledge.kb_service import update_profile
    prof = _profile()
    db = _mock_db()
    update_profile(db, prof, _session(), {"weak_sector": None})
    assert prof.weak_sector is None


def test_weak_sector_empty_string_rejected():
    from app.services.knowledge.kb_service import update_profile
    prof = _profile()
    db = _mock_db()
    update_profile(db, prof, _session(), {"weak_sector": ""})
    assert prof.weak_sector is None


# ─── update_after_ai: recurring_issues decay ──────────────────────────────────

def test_recurring_issue_confirmed_after_3_sessions():
    """Un problema se confirma al aparecer en 3+ sesiones."""
    from app.services.knowledge.kb_service import update_after_ai
    prof = _profile(recurring={"oversteer": {"count": 2, "confirmed": False, "sessions_since_seen": 0, "last_lap_time": 90.0}})
    prof.avg_lap = 90.5
    db = _mock_db()
    db.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = []
    ai_result = {"issues": [{"area": "oversteer"}]}
    update_after_ai(db, prof, ai_result, 90.0)
    assert prof.recurring_issues["oversteer"]["confirmed"] is True


def test_recurring_issue_decay_after_5_sessions():
    """Un problema confirmed=True se desconfirma si no aparece en 5 sesiones."""
    from app.services.knowledge.kb_service import update_after_ai
    prof = _profile(recurring={
        "oversteer": {"count": 5, "confirmed": True, "sessions_since_seen": 4, "last_lap_time": 90.0}
    })
    prof.avg_lap = 90.5
    db = _mock_db()
    db.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = []
    # Esta sesión NO reporta oversteer → sessions_since_seen pasa de 4 a 5 → confirmed=False
    ai_result = {"issues": [{"area": "understeer"}]}
    update_after_ai(db, prof, ai_result, 90.0)
    assert prof.recurring_issues["oversteer"]["confirmed"] is False


def test_recurring_issue_no_decay_before_5_sessions():
    """Con sessions_since_seen=3 (< 5), el issue confirmed sigue siendo True."""
    from app.services.knowledge.kb_service import update_after_ai
    prof = _profile(recurring={
        "oversteer": {"count": 5, "confirmed": True, "sessions_since_seen": 3, "last_lap_time": 90.0}
    })
    prof.avg_lap = 90.5
    db = _mock_db()
    db.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = []
    ai_result = {"issues": [{"area": "understeer"}]}
    update_after_ai(db, prof, ai_result, 90.0)
    assert prof.recurring_issues["oversteer"]["confirmed"] is True


def test_recurring_issue_sessions_since_seen_increments():
    """sessions_since_seen aumenta en 1 cuando el area no aparece."""
    from app.services.knowledge.kb_service import update_after_ai
    prof = _profile(recurring={
        "braking": {"count": 3, "confirmed": True, "sessions_since_seen": 1, "last_lap_time": 90.0}
    })
    prof.avg_lap = 90.5
    db = _mock_db()
    db.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = []
    # Necesitamos al menos 1 issue para evitar el early-return; usamos un area distinta
    ai_result = {"issues": [{"area": "understeer"}]}
    update_after_ai(db, prof, ai_result, 90.0)
    assert prof.recurring_issues["braking"]["sessions_since_seen"] == 2


def test_recurring_issue_resets_since_seen_when_seen():
    """Cuando el área vuelve a aparecer, sessions_since_seen se pone a 0."""
    from app.services.knowledge.kb_service import update_after_ai
    prof = _profile(recurring={
        "braking": {"count": 3, "confirmed": True, "sessions_since_seen": 4, "last_lap_time": 91.0}
    })
    prof.avg_lap = 90.5
    db = _mock_db()
    db.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = []
    ai_result = {"issues": [{"area": "braking"}]}
    update_after_ai(db, prof, ai_result, 90.0)
    assert prof.recurring_issues["braking"]["sessions_since_seen"] == 0
    assert prof.recurring_issues["braking"]["confirmed"] is True  # sigue confirmado

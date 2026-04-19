"""
Cliente LLM para análisis de telemetría.

Routing por plan:
  free  → Claude Haiku 4.5        (Anthropic)
  pro   → Gemini 2.5 Flash        (Google)
  team  → Gemini 2.5 Pro          (Google)
"""

from __future__ import annotations

import json
import logging

import anthropic
from google import genai as google_genai
from google.genai import types as google_types
from json_repair import repair_json

from app.core.config import settings
from app.models.knowledge import KnowledgeProfile
from app.services.analysis.pre_analysis import build_digest
from app.utils.formatters import fmt_lap_time as _fmt

logger = logging.getLogger(__name__)

# ── Modelos por plan ──────────────────────────────────────────────────────────
_MODEL_FREE  = "claude-haiku-4-5-20251001"
_MODEL_PRO   = "gemini-2.5-flash"
_MODEL_TEAM  = "gemini-2.5-pro"

_GEMINI_PLANS = {"pro", "team"}


def _model_for_plan(plan: str) -> str:
    if plan == "team":
        return _MODEL_TEAM
    if plan == "pro":
        return _MODEL_PRO
    return _MODEL_FREE


def _is_gemini(plan: str) -> bool:
    return plan in _GEMINI_PLANS


def _max_tokens_for_plan(plan: str) -> int:
    return 2500 if plan in _GEMINI_PLANS else 1500


# ── Clientes ──────────────────────────────────────────────────────────────────
def _anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=90.0)


def _gemini_client() -> google_genai.Client:
    return google_genai.Client(api_key=settings.google_gemini_api_key)


# ── Llamada unificada ─────────────────────────────────────────────────────────
def _strip_md(raw: str) -> str:
    if "```" in raw:
        lines = raw.split("\n")
        return "\n".join(l for l in lines if not l.strip().startswith("```")).strip()
    return raw


def _call_llm(plan: str, system: str, prompt: str, max_tokens: int) -> tuple[str, int, int]:
    """Llama al LLM correcto según el plan y retorna (texto, tok_in, tok_out)."""
    model = _model_for_plan(plan)

    if _is_gemini(plan):
        client = _gemini_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=google_types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=0.3,
            ),
        )
        text = (response.text or "").strip()
        usage = response.usage_metadata
        tok_in  = getattr(usage, "prompt_token_count", 0) or 0
        tok_out = getattr(usage, "candidates_token_count", 0) or 0
        if tok_out >= max_tokens * 0.95:
            logger.warning("Gemini %s posiblemente truncado (%d out tokens)", model, tok_out)
        return text, tok_in, tok_out

    # Anthropic (FREE)
    client = _anthropic_client()
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if not msg.content or not hasattr(msg.content[0], "text"):
        raise RuntimeError("Anthropic devolvió respuesta vacía")
    if msg.stop_reason == "max_tokens":
        logger.warning("Anthropic %s alcanzó max_tokens (%d out)", model, msg.usage.output_tokens)
    return msg.content[0].text.strip(), msg.usage.input_tokens, msg.usage.output_tokens


def _parse_json(raw: str, fallback: dict) -> dict:
    raw = _strip_md(raw)
    try:
        return json.loads(repair_json(raw))
    except Exception as e:
        logger.error("JSON irreparable: %s\nRaw: %.400s", e, raw)
        return fallback


# ── Prompts ───────────────────────────────────────────────────────────────────
_SYSTEM = """\
Eres un ingeniero de pista experto en sim racing. Analizas datos de telemetría \
y das feedback técnico directo, específico y accionable al piloto.

Reglas:
- IDIOMA: Responde SIEMPRE en español, sin excepciones. Nunca uses inglés.
- Sé directo y conciso. No rellenes con frases vacías.
- Basa TODO en los números del pre-análisis. Si no hay dato, no lo inventes.
- Las recomendaciones deben ser ejecutables en la próxima sesión.
- SETUP: Cuando sugieras cambios de setup de Assetto Corsa, usa SIEMPRE valores \
que el juego permita seleccionar (ej: presiones en incrementos de 0.1 PSI, \
muelles en incrementos de 100 N/m, ARB en enteros). Nunca sugiereas valores \
intermedios imposibles de seleccionar en el juego.
- Cuando hay datos de ride_height: sugiere ajustes de altura/rake específicos en mm
- Cuando hay tyre_wear diferencial: sugiere cambios de camber/toe para uniformizar desgaste
- Cuando hay lsd_analysis: sugiere configuración de diferencial (coast/power locking)
- Cuando hay susp_velocity/damper_diagnosis: sugiere ajustes de amortiguadores (bump/rebound)
- Cuando hay tyre_loads desbalanceadas: sugiere cambios de distribución de peso o ARB
- Siempre incluye el valor ACTUAL (del pre_análisis) y el valor SUGERIDO para cada ajuste de setup
- Responde SIEMPRE con JSON válido, sin markdown, sin texto extra.
"""

_PROMPT_TEMPLATE = """\
RESUMEN EJECUTIVO — anomalías y flags detectados automáticamente:
{digest}

VUELTA ACTUAL (datos completos):
{pre_analysis}

{best_lap_block}HISTORIAL DEL PILOTO (pista+auto):
{profile_summary}

Analiza la vuelta y devuelve exactamente este JSON (sin markdown):
{{
  "summary": "2-3 frases resumiendo la vuelta. Menciona el contexto histórico (ej: top 20% de sus tiempos) y problemas confirmados si los hay.",
  "lap_context": {{
    "classification": "personal_best|top_20pct|average|below_average",
    "interpretation": "Una frase situando esta vuelta en el historial del piloto."
  }},
  "sector_analysis": {{
    "s1": {{
      "assessment": "good|ok|weak",
      "detail": "Qué pasó en S1 con dato concreto. Si hay comparación vs mejor vuelta, úsala."
    }},
    "s2": {{
      "assessment": "good|ok|weak",
      "detail": "Qué pasó en S2 con dato concreto."
    }},
    "s3": {{
      "assessment": "good|ok|weak",
      "detail": "Qué pasó en S3 con dato concreto."
    }}
  }},
  "scores": {{
    "frenadas": 0,
    "traccion": 0,
    "curvas_rapidas": 0,
    "gestion_gomas": 0,
    "consistencia": 0
  }},
  "strengths": ["punto fuerte con dato concreto"],
  "issues": [
    {{"area": "nombre del área", "detail": "descripción técnica con número", "severity": "low|medium|high"}}
  ],
  "recommendations": [
    {{"text": "recomendación accionable", "zone": "zona de pista o null", "expected_gain_s": 0.0}}
  ],
  "setup_suggestions": ["sugerencia de setup con número concreto"],
  "improvement_plan": [
    {{"step": 1, "action": "Instrucción concreta y ejecutable", "zone": "zona específica", "expected_gain_s": 0.0}},
    {{"step": 2, "action": "Instrucción concreta y ejecutable", "zone": "zona específica", "expected_gain_s": 0.0}},
    {{"step": 3, "action": "Instrucción concreta y ejecutable", "zone": "zona específica", "expected_gain_s": 0.0}}
  ]
}}

Reglas para los scores (0-10): 0-3=muy malo, 4-5=deficiente, 6-7=aceptable, 8-9=bueno, 10=perfecto. Basa cada score en los datos, no en intuición.
"""


def _build_profile_summary(profile: KnowledgeProfile | None, prev_recs: list | None = None) -> str:
    if profile is None:
        return "Sin historial previo en esta pista/auto."

    lines = [
        f"Sesiones en esta combinación: {profile.sessions_count}",
        f"Mejor vuelta histórica: {_fmt(profile.best_lap)}",
        f"Promedio histórico: {_fmt(profile.avg_lap)}",
    ]
    cp = profile.corner_profiles or {}
    sector_counts: dict = cp.get("sector_counts", {})
    total_sc = sum(sector_counts.values())
    if profile.weak_sector and total_sc > 0:
        sc_detail = ", ".join(
            f"{s}: {sector_counts.get(s, 0)}/{total_sc}"
            for s in ("S1", "S2", "S3")
            if sector_counts.get(s, 0) > 0
        )
        lines.append(f"Sector débil histórico: {profile.weak_sector} ({sc_detail} sesiones)")
    elif profile.weak_sector:
        lines.append(f"Sector débil: {profile.weak_sector}")

    if profile.trend != 0:
        direction = "mejorando" if profile.trend > 0 else "empeorando"
        lines.append(f"Tendencia (regresión lineal): {direction} ({profile.trend:+.3f}s/sesión)")
    if profile.corner_profiles and profile.corner_profiles.get("latest"):
        latest = profile.corner_profiles["latest"]
        if latest.get("handling"):
            lines.append(f"Comportamiento habitual: {latest['handling']}")

    recurring = profile.recurring_issues or {}
    confirmed = sorted(
        [(area, data) for area, data in recurring.items() if data.get("confirmed")],
        key=lambda x: x[1].get("count", 0), reverse=True
    )[:3]
    if confirmed:
        lines.append("\nPROBLEMAS CONFIRMADOS (detectados en 3+ sesiones — tratar como hechos, no hipótesis):")
        for area, data in confirmed:
            lines.append(f"  ✗ {area} — visto {data['count']} veces")

    unconfirmed = sorted(
        [(area, data) for area, data in recurring.items()
         if not data.get("confirmed") and data.get("count", 0) >= 2],
        key=lambda x: x[1].get("count", 0), reverse=True
    )[:2]
    if unconfirmed:
        lines.append("\nProblemas repetidos (2 sesiones):")
        for area, data in unconfirmed:
            lines.append(f"  ? {area} — visto {data['count']} veces")

    if prev_recs:
        useful = [r for r in prev_recs if r.tested and r.delta_improvement is not None and abs(r.delta_improvement) > 0.05]
        if useful:
            lines.append("\nRECOMENDACIONES PREVIAS Y RESULTADO:")
            for rec in useful:
                result = f"✓ FUNCIONÓ (+{rec.delta_improvement:.3f}s)" if rec.delta_improvement > 0.05 else f"✗ Empeoró ({rec.delta_improvement:.3f}s)"
                zone = f" [{rec.zone}]" if rec.zone else ""
                lines.append(f"  • {rec.text}{zone} — {result}")

    return "\n".join(lines)


# ── API pública ───────────────────────────────────────────────────────────────

def analyze(
    pre_analysis: dict,
    profile: KnowledgeProfile | None,
    prev_recs: list | None = None,
    best_lap_pre: dict | None = None,
    plan: str = "free",
) -> tuple[dict, int, int]:
    """
    Análisis por vuelta. plan determina el modelo usado.
    Retorna (ai_result_dict, tokens_input, tokens_output).
    """
    _EXCLUDE = {"track", "car", "simulator"}
    compact = {k: v for k, v in pre_analysis.items() if k not in _EXCLUDE}

    digest = build_digest(pre_analysis)

    best_lap_block = ""
    if best_lap_pre and best_lap_pre != pre_analysis:
        compact_best = {k: v for k, v in best_lap_pre.items() if k not in _EXCLUDE}
        delta_s1    = pre_analysis.get("s1", 0) - best_lap_pre.get("s1", 0)
        delta_s2    = pre_analysis.get("s2", 0) - best_lap_pre.get("s2", 0)
        delta_s3    = pre_analysis.get("s3", 0) - best_lap_pre.get("s3", 0)
        delta_total = pre_analysis.get("lap_time", 0) - best_lap_pre.get("lap_time", 0)
        best_lap_block = (
            f"MEJOR VUELTA PERSONAL (comparación directa):\n"
            f"  Delta total: {delta_total:+.3f}s  S1: {delta_s1:+.3f}s  S2: {delta_s2:+.3f}s  S3: {delta_s3:+.3f}s\n"
            f"  Pre-análisis mejor vuelta: {json.dumps(compact_best, ensure_ascii=False)}\n\n"
        )

    prompt = _PROMPT_TEMPLATE.format(
        digest=digest,
        pre_analysis=json.dumps(compact, ensure_ascii=False, indent=2),
        best_lap_block=best_lap_block,
        profile_summary=_build_profile_summary(profile, prev_recs),
    )

    max_tokens = _max_tokens_for_plan(plan)
    raw, tok_in, tok_out = _call_llm(plan, _SYSTEM, prompt, max_tokens)

    fallback = {
        "summary": raw[:300],
        "lap_context": {"classification": "average", "interpretation": "Parse error"},
        "sector_analysis": {
            "s1": {"assessment": "ok", "detail": "Parse error"},
            "s2": {"assessment": "ok", "detail": "Parse error"},
            "s3": {"assessment": "ok", "detail": "Parse error"},
        },
        "scores": {"frenadas": 0, "traccion": 0, "curvas_rapidas": 0, "gestion_gomas": 0, "consistencia": 0},
        "strengths": [],
        "issues": [],
        "recommendations": [],
        "setup_suggestions": [],
        "improvement_plan": [],
    }
    return _parse_json(raw, fallback), tok_in, tok_out


_TRACK_INFO_PROMPT = """\
Necesito información sobre el circuito de sim racing con ID: "{track_id}".
{length_hint}

Si conoces este circuito (real o ficticio de mods conocidos de Assetto Corsa), proporciona su información.
Si no lo conoces con certeza, indica que es ficticio y genera datos genéricos razonables.

Devuelve SOLO este JSON (sin markdown):
{{
  "display_name": "Nombre completo del circuito",
  "country": "País o región (null si es ficticio)",
  "track_type": "real|fictional",
  "length_m": 0,
  "turns": 0,
  "characteristics": ["característica 1", "característica 2"],
  "sectors": [
    "S1: descripción del primer sector",
    "S2: descripción del segundo sector",
    "S3: descripción del tercer sector"
  ],
  "key_corners": [
    {{"name": "Nombre curva", "type": "tipo", "tip": "consejo para esta curva"}}
  ],
  "lap_record": null,
  "notes": "Nota adicional sobre el circuito (null si no hay)"
}}
"""


def get_track_info_from_claude(track_id: str, track_length_m: float | None = None) -> dict:
    """Obtiene info de un circuito usando Haiku (siempre, independiente del plan)."""
    length_hint = (
        f"La longitud del circuito según la telemetría es aproximadamente {track_length_m:.0f}m."
        if track_length_m and track_length_m > 0 else ""
    )
    prompt = _TRACK_INFO_PROMPT.format(track_id=track_id, length_hint=length_hint)

    raw, tok_in, tok_out = _call_llm(
        "free",
        "Eres un experto en circuitos de automovilismo y sim racing. Responde siempre con JSON válido.",
        prompt,
        500,
    )

    fallback = {
        "display_name": track_id.replace("_", " ").title(),
        "country": None, "track_type": "fictional",
        "length_m": track_length_m, "turns": None,
        "characteristics": [], "sectors": [], "key_corners": [],
        "lap_record": None, "notes": None,
    }
    result = _parse_json(raw, fallback)
    logger.info("Track info call — track: %s — tokens: %d in / %d out", track_id, tok_in, tok_out)
    return result


def _build_pilot_style_block(profile: KnowledgeProfile | None) -> str:
    """Construye el bloque de estilo de pilotaje para el prompt de sesión."""
    if profile is None:
        return ""

    lines = ["\nPERFIL DE ESTILO DEL PILOTO (acumulado sin IA, solo matemáticas):"]

    ds = profile.driving_style or {}

    # Manejo dominante
    hc = ds.get("handling_counts", {})
    if hc and any(hc.values()):
        dominant = max(hc, key=lambda k: hc.get(k, 0))
        total = sum(hc.values())
        pct = int(hc.get(dominant, 0) / total * 100)
        lines.append(f"  Manejo dominante: {dominant} ({pct}% de {total} sesiones)")

    # Tendencia de subviraje
    uh = ds.get("understeer_history", [])
    if len(uh) >= 2:
        avg_us = sum(uh) / len(uh)
        trend_us = uh[-1] - uh[0]
        direction = "↑ aumentando" if trend_us > 0.05 else ("↓ mejorando" if trend_us < -0.05 else "→ estable")
        lines.append(f"  Understeer score promedio: {avg_us:.2f}/1.0 — tendencia {direction} ({len(uh)} sesiones)")

    # Patrón de throttle
    th = ds.get("throttle_history", [])
    if len(th) >= 2:
        avg_thr = sum(th) / len(th)
        lines.append(f"  Throttle promedio histórico: {avg_thr:.1f}%")

    # Agresividad de frenada
    bh = ds.get("brake_g_history", [])
    if len(bh) >= 2:
        avg_bg = sum(bh) / len(bh)
        lines.append(f"  G de frenada promedio: {avg_bg:.2f}g")

    # Estabilidad trasera
    sh = ds.get("slip_rear_history", [])
    if len(sh) >= 2:
        avg_slip = sum(sh) / len(sh)
        label = "alta" if avg_slip > 5.0 else ("moderada" if avg_slip > 2.0 else "baja")
        lines.append(f"  Tendencia de slip trasero: {avg_slip:.1f}% promedio ({label})")

    # Sesiones y perfil histórico
    lines.append(f"  Sesiones en este combo: {profile.sessions_count} | Mejor: {_fmt(profile.best_lap)} | Promedio: {_fmt(profile.avg_lap)}")
    if profile.weak_sector:
        lines.append(f"  Sector históricamente débil: {profile.weak_sector}")

    # Problemas confirmados
    confirmed = [
        (area, data) for area, data in (profile.recurring_issues or {}).items()
        if data.get("confirmed")
    ]
    if confirmed:
        lines.append("  Problemas confirmados (3+ sesiones):")
        for area, data in sorted(confirmed, key=lambda x: x[1].get("count", 0), reverse=True)[:3]:
            lines.append(f"    ✗ {area} — {data['count']} veces")

    if len(lines) == 1:
        return ""
    return "\n".join(lines)


_SESSION_PROMPT = """\
Eres un ingeniero de pista analizando UNA SESIÓN COMPLETA de sim racing (múltiples vueltas).

DATOS DE LA SESIÓN:
{session_data}

MEJOR VUELTA — resumen de anomalías:
{digest}

MEJOR VUELTA — pre-análisis técnico completo:
{best_lap_pre}
{pilot_style_block}
Devuelve exactamente este JSON (sin markdown):
{{
  "section_8_technical": {{
    "strengths": ["fortaleza técnica 1", "fortaleza técnica 2"],
    "improvements": ["área de mejora 1 con dato concreto", "área de mejora 2"],
    "setup_recommendations": ["recomendación de setup 1"]
  }},
  "section_9_opportunities": [
    {{
      "rank": 1,
      "title": "Nombre de la oportunidad",
      "detail": "Descripción con dato concreto",
      "estimated_gain_s": 0.10,
      "occurs_in": "descripción de dónde ocurre"
    }}
  ],
  "section_10_action_plan": {{
    "focuses": [
      {{
        "title": "Enfoque 1: nombre",
        "exercise": "Qué practicar",
        "objective": "Objetivo medible"
      }}
    ],
    "target_lap_time": 0.0,
    "target_lap_time_fmt": "0:00.000",
    "target_consistency_score": 10,
    "timeline": "X sesiones de práctica"
  }},
  "section_11_engineer_diagnosis": {{
    "what_is_working": ["punto positivo 1", "punto positivo 2"],
    "problems_detected": ["problema con dato 1"],
    "driving_style": ["característica del estilo de pilotaje 1"],
    "setup_recommendations": ["recomendación específica con números"],
    "next_session_target": "Meta concreta para la próxima sesión"
  }},
  "section_12_driving_coaching": {{
    "style_profile": "1-2 frases describiendo el estilo real del piloto basado en datos históricos y sesión actual. Sé directo y específico.",
    "recurring_habits": [
      {{
        "habit": "nombre corto del hábito",
        "evidence": "dato concreto que lo respalda (número)",
        "impact": "high|medium|low",
        "correction": "instrucción técnica específica para corregirlo"
      }}
    ],
    "technique_observations": [
      {{
        "area": "área técnica (ej: frenada T3, aceleración salida lenta)",
        "observation": "qué hace el piloto con dato concreto",
        "drill": "ejercicio ejecutable en la próxima sesión"
      }}
    ],
    "immediate_focus": "Una sola cosa concreta en la que enfocarse. Debe ser ejecutable y medible."
  }}
}}
"""


def analyze_session(
    session_summary: dict,
    best_lap_pre: dict,
    setup_data: dict | None = None,
    track_info: dict | None = None,
    prev_setup: dict | None = None,
    profile: KnowledgeProfile | None = None,
    plan: str = "free",
) -> tuple[dict, int, int]:
    """
    Análisis de sesión completa (secciones 8-11).
    Retorna (ai_result_dict, tokens_input, tokens_output).
    """
    compact_summary = {
        k: v for k, v in session_summary.items()
        if k not in ("theoretical_best_fmt", "best_s1_fmt", "best_s2_fmt", "best_s3_fmt",
                     "avg_lap_fmt", "worst_lap_fmt", "best_lap_fmt")
    }
    _SKIP = {"track", "car", "simulator"}
    compact_pre = {k: v for k, v in best_lap_pre.items() if k not in _SKIP}

    digest = build_digest(best_lap_pre)

    track_block = ""
    if track_info and track_info.get("display_name"):
        parts = [f"\nINFORMACIÓN DEL CIRCUITO: {track_info['display_name']}"]
        if track_info.get("country"):
            parts[0] += f" ({track_info['country']})"
        if track_info.get("length_m"):
            parts.append(f"Longitud: {track_info['length_m']:.0f}m | Curvas: {track_info.get('turns') or '?'}")
        if track_info.get("characteristics"):
            parts.append(f"Características: {', '.join(track_info['characteristics'])}")
        if track_info.get("sectors"):
            parts.append("Sectores:")
            for s in track_info["sectors"]:
                parts.append(f"  • {s}")
        if track_info.get("key_corners"):
            parts.append("Curvas clave:")
            for c in track_info["key_corners"]:
                parts.append(f"  • {c['name']} ({c.get('type','')}) — {c.get('tip','')}")
        if track_info.get("notes"):
            parts.append(f"Nota: {track_info['notes']}")
        track_block = "\n".join(parts)

    setup_block = ""
    if setup_data:
        _SETUP_SKIP = {"version", "__metadata__", "HEADER", "CAR"}
        compact_setup = {k: v for k, v in setup_data.items() if k.upper() not in _SETUP_SKIP}
        setup_block = f"\n\nSETUP DEL PILOTO:\n{json.dumps(compact_setup, ensure_ascii=False, separators=(',', ':'))}"

    prev_setup_block = ""
    if prev_setup and setup_data:
        _SETUP_SKIP = {"version", "__metadata__", "HEADER", "CAR"}
        _PRIORITY = {"TYRES": 0, "BRAKES": 1, "SUSPENSION": 2, "AERO": 3, "AERODYNAMICS": 3}
        changes: list[tuple[int, str]] = []
        for section, values in setup_data.items():
            if section.upper() in _SETUP_SKIP:
                continue
            prev_section = prev_setup.get(section)
            if isinstance(values, dict) and isinstance(prev_section, dict):
                priority = _PRIORITY.get(section.upper(), 9)
                for key, val in values.items():
                    prev_val = prev_section.get(key)
                    if prev_val is not None and prev_val != val:
                        changes.append((priority, f"  {section}.{key}: {prev_val} → {val}"))
        if changes:
            changes.sort(key=lambda x: x[0])
            top_changes = [c for _, c in changes[:15]]
            prev_setup_block = "\n\nCAMBIOS DE SETUP RESPECTO A SESIÓN ANTERIOR (misma pista/auto):\n" + "\n".join(top_changes)
            if len(changes) > 15:
                prev_setup_block += f"\n  ... y {len(changes) - 15} cambios más"
            prev_setup_block += "\nAnaliza si estos cambios mejoraron o empeoraron el rendimiento según los datos de la sesión."

    pilot_style_block = _build_pilot_style_block(profile)

    prompt = _SESSION_PROMPT.format(
        session_data=json.dumps(compact_summary, ensure_ascii=False, indent=2),
        digest=digest,
        best_lap_pre=json.dumps(compact_pre, ensure_ascii=False, indent=2),
        pilot_style_block=pilot_style_block,
    ) + track_block + setup_block + prev_setup_block

    session_max_tokens = 8000 if _is_gemini(plan) else 5000
    raw, tok_in, tok_out = _call_llm(plan, _SYSTEM, prompt, session_max_tokens)

    fallback = {
        "section_8_technical": {"strengths": [], "improvements": [], "setup_recommendations": []},
        "section_9_opportunities": [],
        "section_10_action_plan": {"focuses": [], "target_lap_time": 0, "timeline": "—"},
        "section_11_engineer_diagnosis": {
            "what_is_working": [], "problems_detected": [],
            "driving_style": [], "setup_recommendations": [],
            "next_session_target": "Parse error — ver logs",
        },
        "section_12_driving_coaching": {
            "style_profile": "",
            "recurring_habits": [],
            "technique_observations": [],
            "immediate_focus": "",
        },
    }
    return _parse_json(raw, fallback), tok_in, tok_out


_COMPARE_PROMPT = """\
Compara dos pilotos en la misma pista. Ambos datos son pre-análisis de su mejor vuelta.

SESIÓN A — {car_a} ({sim_a}):
{digest_a}
{pre_a}

SESIÓN B — {car_b} ({sim_b}):
{digest_b}
{pre_b}

DELTAS PRE-CALCULADOS (B - A, negativo = A es más rápido):
  Total: {delta_total:+.3f}s  S1: {delta_s1:+.3f}s  S2: {delta_s2:+.3f}s  S3: {delta_s3:+.3f}s

Devuelve exactamente este JSON:
{{
  "summary": "2-3 frases comparando ambas sesiones",
  "advantage_a": ["ventaja de A sobre B"],
  "advantage_b": ["ventaja de B sobre A"],
  "key_differences": [
    {{"area": "nombre del área", "detail": "descripción técnica", "favors": "A|B|tie"}}
  ],
  "recommendations": [
    {{"text": "recomendación accionable", "applies_to": "A|B|both"}}
  ],
  "verdict": "Una frase: quién tuvo mejor sesión y por qué"
}}
"""


def compare(
    pre_a: dict,
    meta_a: dict,
    pre_b: dict,
    meta_b: dict,
    delta_s1: float,
    delta_s2: float,
    delta_s3: float,
    delta_total: float,
    plan: str = "free",
) -> tuple[dict, int, int]:
    """
    Compara dos sesiones. Retorna (ai_comparison_dict, tokens_input, tokens_output).
    """
    _SKIP = {"track", "car", "simulator"}
    compact_a = {k: v for k, v in pre_a.items() if k not in _SKIP}
    compact_b = {k: v for k, v in pre_b.items() if k not in _SKIP}

    prompt = _COMPARE_PROMPT.format(
        car_a=meta_a.get("car", "A"),
        sim_a=meta_a.get("simulator", ""),
        digest_a=build_digest(pre_a),
        pre_a=json.dumps(compact_a, ensure_ascii=False, indent=2),
        car_b=meta_b.get("car", "B"),
        sim_b=meta_b.get("simulator", ""),
        digest_b=build_digest(pre_b),
        pre_b=json.dumps(compact_b, ensure_ascii=False, indent=2),
        delta_total=delta_total,
        delta_s1=delta_s1,
        delta_s2=delta_s2,
        delta_s3=delta_s3,
    )

    raw, tok_in, tok_out = _call_llm(plan, _SYSTEM, prompt, 1024)

    fallback = {
        "summary": raw[:300],
        "advantage_a": [], "advantage_b": [],
        "key_differences": [], "recommendations": [],
        "verdict": "Parse error — ver logs",
    }
    return _parse_json(raw, fallback), tok_in, tok_out

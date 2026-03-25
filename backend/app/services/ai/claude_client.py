"""
Cliente Claude para análisis de telemetría.

Usa claude-haiku-4-5 para mantener el costo bajo.
Recibe pre_analysis + KnowledgeProfile y devuelve
un dict estructurado con hallazgos y recomendaciones.
"""

from __future__ import annotations

import json
import logging

import anthropic
from json_repair import repair_json

from app.core.config import settings
from app.models.knowledge import KnowledgeProfile


_SYSTEM = """\
Eres un ingeniero de pista experto en sim racing. Analizas datos de telemetría \
y das feedback técnico directo, específico y accionable al piloto.

Reglas:
- Sé directo y conciso. No rellenes con frases vacías.
- Basa TODO en los números del pre-análisis. Si no hay dato, no lo inventes.
- Las recomendaciones deben ser ejecutables en la próxima sesión.
- Responde SIEMPRE con JSON válido, sin markdown, sin texto extra.
"""

_PROMPT_TEMPLATE = """\
SESIÓN ACTUAL:
{pre_analysis}

HISTORIAL DEL PILOTO (pista+auto):
{profile_summary}

Analiza la sesión y devuelve exactamente este JSON:
{{
  "summary": "2-3 frases resumiendo la sesión. Si hay problemas confirmados, menciónalos explícitamente.",
  "strengths": ["punto fuerte 1", "punto fuerte 2"],
  "issues": [
    {{"area": "nombre del área", "detail": "descripción técnica", "severity": "low|medium|high"}}
  ],
  "recommendations": [
    {{"text": "recomendación accionable", "zone": "zona de pista o null", "expected_gain_s": 0.0}}
  ],
  "setup_suggestions": ["sugerencia de setup 1"],
  "next_session_focus": "Una frase: qué trabajar en la próxima sesión"
}}
"""


def _build_profile_summary(profile: KnowledgeProfile | None, prev_recs: list | None = None) -> str:
    if profile is None:
        return "Sin historial previo en esta pista/auto."

    lines = [
        f"Sesiones en esta combinación: {profile.sessions_count}",
        f"Mejor vuelta histórica: {_fmt(profile.best_lap)}",
        f"Promedio histórico: {_fmt(profile.avg_lap)}",
    ]
    if profile.weak_sector:
        lines.append(f"Sector débil recurrente: {profile.weak_sector}")
    if profile.trend != 0:
        direction = "mejorando" if profile.trend > 0 else "empeorando"
        lines.append(f"Tendencia: {direction} ({profile.trend:+.3f}s/sesión)")
    if profile.corner_profiles and profile.corner_profiles.get("latest"):
        latest = profile.corner_profiles["latest"]
        if latest.get("handling"):
            lines.append(f"Comportamiento habitual: {latest['handling']}")

    # Problemas confirmados (≥3 sesiones con el mismo problema)
    recurring = profile.recurring_issues or {}
    confirmed = [(area, data) for area, data in recurring.items() if data.get("confirmed")]
    if confirmed:
        lines.append("\nPROBLEMAS CONFIRMADOS (detectados en 3+ sesiones — tratar como hechos, no hipótesis):")
        for area, data in confirmed:
            lines.append(f"  ✗ {area} — visto {data['count']} veces")

    unconfirmed = [(area, data) for area, data in recurring.items()
                   if not data.get("confirmed") and data.get("count", 0) >= 2]
    if unconfirmed:
        lines.append("\nProblemas repetidos (2 sesiones):")
        for area, data in unconfirmed:
            lines.append(f"  ? {area} — visto {data['count']} veces")

    # Recomendaciones anteriores y su resultado
    if prev_recs:
        lines.append("\nRECOMENDACIONES PREVIAS Y RESULTADO:")
        for rec in prev_recs:
            if rec.tested and rec.delta_improvement is not None:
                if rec.delta_improvement > 0.05:
                    result = f"✓ FUNCIONÓ (+{rec.delta_improvement:.3f}s de mejora)"
                elif rec.delta_improvement < -0.05:
                    result = f"✗ Empeoró ({rec.delta_improvement:.3f}s)"
                else:
                    result = "→ Sin cambio significativo"
            else:
                result = "→ Primera sesión aplicando esto"
            zone = f" [{rec.zone}]" if rec.zone else ""
            lines.append(f"  • {rec.text}{zone} — {result}")

    return "\n".join(lines)


def _fmt(seconds: float) -> str:
    if seconds <= 0:
        return "—"
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m}:{s:06.3f}"


def analyze(
    pre_analysis: dict,
    profile: KnowledgeProfile | None,
    prev_recs: list | None = None,
) -> tuple[dict, int, int]:
    """
    Llama Claude Haiku con el pre-análisis y el perfil del piloto.
    prev_recs: últimas recomendaciones (ya testeadas) para cerrar el ciclo.

    Retorna (ai_result_dict, tokens_input, tokens_output).
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    compact = {k: v for k, v in pre_analysis.items()
               if k not in ("track", "car", "simulator")}

    prompt = _PROMPT_TEMPLATE.format(
        pre_analysis=json.dumps(compact, ensure_ascii=False, indent=2),
        profile_summary=_build_profile_summary(profile, prev_recs),
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Quitar code fences si Claude los añadió (```json ... ```)
    if "```" in raw:
        lines = raw.split("\n")
        raw = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    # json_repair tolera trailing commas, newlines en strings, etc.
    try:
        result = json.loads(repair_json(raw))
    except Exception as e:
        logging.getLogger(__name__).error("Claude JSON irreparable: %s\nRaw: %.400s", e, raw)
        result = {
            "summary": raw[:300],
            "strengths": [],
            "issues": [],
            "recommendations": [],
            "setup_suggestions": [],
            "next_session_focus": "Parse error — ver logs",
        }

    tokens_in  = message.usage.input_tokens
    tokens_out = message.usage.output_tokens

    return result, tokens_in, tokens_out


_SESSION_PROMPT = """\
Eres un ingeniero de pista analizando UNA SESIÓN COMPLETA de sim racing (múltiples vueltas).

DATOS DE LA SESIÓN:
{session_data}

MEJOR VUELTA — pre-análisis técnico:
{best_lap_pre}

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
  }}
}}
"""


def analyze_session(
    session_summary: dict,
    best_lap_pre: dict,
    setup_data: dict | None = None,
) -> tuple[dict, int, int]:
    """
    Llama Claude Haiku con el resumen de sesión completa y el pre-análisis de la mejor vuelta.
    Genera las secciones 8-11 del reporte.

    Retorna (ai_result_dict, tokens_input, tokens_output).
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Compactar para no desperdiciar tokens
    compact_summary = {
        k: v for k, v in session_summary.items()
        if k not in ("theoretical_best_fmt", "best_s1_fmt", "best_s2_fmt", "best_s3_fmt",
                     "avg_lap_fmt", "worst_lap_fmt", "best_lap_fmt")
    }
    compact_pre = {k: v for k, v in best_lap_pre.items() if k not in ("track", "car", "simulator")}

    setup_block = ""
    if setup_data:
        setup_block = f"\n\nSETUP DEL PILOTO (archivo .ini):\n{json.dumps(setup_data, ensure_ascii=False, indent=2)}"

    prompt = _SESSION_PROMPT.format(
        session_data=json.dumps(compact_summary, ensure_ascii=False, indent=2),
        best_lap_pre=json.dumps(compact_pre, ensure_ascii=False, indent=2),
    ) + setup_block

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if "```" in raw:
        lines = raw.split("\n")
        raw = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()

    try:
        result = json.loads(repair_json(raw))
    except Exception as e:
        logging.getLogger(__name__).error("Claude session JSON irreparable: %s\nRaw: %.400s", e, raw)
        result = {
            "section_8_technical": {"strengths": [], "improvements": [], "setup_recommendations": []},
            "section_9_opportunities": [],
            "section_10_action_plan": {"focuses": [], "target_lap_time": 0, "timeline": "—"},
            "section_11_engineer_diagnosis": {"what_is_working": [], "problems_detected": [],
                                               "driving_style": [], "setup_recommendations": [],
                                               "next_session_target": "Parse error — ver logs"},
        }

    return result, message.usage.input_tokens, message.usage.output_tokens


_COMPARE_PROMPT = """\
Compara dos pilotos en la misma pista. Ambos datos son pre-análisis de su mejor vuelta.

SESIÓN A — {car_a} ({sim_a}):
{pre_a}

SESIÓN B — {car_b} ({sim_b}):
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
) -> tuple[dict, int, int]:
    """
    Llama Claude para comparar dos sesiones.

    Retorna (ai_comparison_dict, tokens_input, tokens_output).
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    compact_a = {k: v for k, v in pre_a.items() if k not in ("track", "car", "simulator")}
    compact_b = {k: v for k, v in pre_b.items() if k not in ("track", "car", "simulator")}

    prompt = _COMPARE_PROMPT.format(
        car_a=meta_a.get("car", "A"),
        sim_a=meta_a.get("simulator", ""),
        pre_a=json.dumps(compact_a, ensure_ascii=False, indent=2),
        car_b=meta_b.get("car", "B"),
        sim_b=meta_b.get("simulator", ""),
        pre_b=json.dumps(compact_b, ensure_ascii=False, indent=2),
        delta_total=delta_total,
        delta_s1=delta_s1,
        delta_s2=delta_s2,
        delta_s3=delta_s3,
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    if "```" in raw:
        lines = raw.split("\n")
        raw = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    try:
        result = json.loads(repair_json(raw))
    except Exception as e:
        logging.getLogger(__name__).error("Claude compare JSON irreparable: %s\nRaw: %.400s", e, raw)
        result = {
            "summary": raw[:300],
            "advantage_a": [],
            "advantage_b": [],
            "key_differences": [],
            "recommendations": [],
            "verdict": "Parse error — ver logs",
        }

    tokens_in  = message.usage.input_tokens
    tokens_out = message.usage.output_tokens

    return result, tokens_in, tokens_out

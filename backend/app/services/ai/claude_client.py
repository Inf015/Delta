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
  "summary": "2-3 frases resumiendo la sesión",
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


def _build_profile_summary(profile: KnowledgeProfile | None) -> str:
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
) -> tuple[dict, int, int]:
    """
    Llama Claude Haiku con el pre-análisis y el perfil del piloto.

    Retorna (ai_result_dict, tokens_input, tokens_output).
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Compactar pre_analysis para no desperdiciar tokens:
    # excluir el DataFrame (ya no está), mantener métricas clave
    compact = {k: v for k, v in pre_analysis.items()
               if k not in ("track", "car", "simulator")}

    prompt = _PROMPT_TEMPLATE.format(
        pre_analysis=json.dumps(compact, ensure_ascii=False, indent=2),
        profile_summary=_build_profile_summary(profile),
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

"""
Delta — PDF Report Generator (dark F1 theme)
=============================================
Generates a complete 11-section PDF from a pre-computed ``report`` dict.

Public API
----------
    generate_report_pdf(report: dict, output_path: str | Path) -> str
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
C_BG = HexColor("#0f0f0f")
C_SECTION = HexColor("#c0392b")
C_CARD = HexColor("#1a1a1a")
C_BORDER = HexColor("#2a2a2a")
C_TEXT = HexColor("#ffffff")
C_TEXT_SEC = HexColor("#9ca3af")
C_TEXT_MUTED = HexColor("#4b5563")
C_GREEN = HexColor("#22c55e")
C_PURPLE = HexColor("#a855f7")
C_ORANGE = HexColor("#f97316")
C_RED = HexColor("#ef4444")
C_YELLOW = HexColor("#eab308")

C_CARD_GREEN = HexColor("#052e16")      # dark green tint for best lap row
C_CARD_RED = HexColor("#2d0606")        # dark red tint for invalid laps
C_CARD_PURPLE = HexColor("#2d1b47")     # dark purple tint for best sector
C_ROW_ALT = HexColor("#141414")        # alternating row

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm


# ---------------------------------------------------------------------------
# Helpers — value safety
# ---------------------------------------------------------------------------

def _v(value: Any, fmt: str = "", default: str = "N/D") -> str:
    """Return a formatted string or default when value is None/falsy."""
    if value is None:
        return default
    if fmt:
        try:
            return format(value, fmt)
        except (TypeError, ValueError):
            return default
    return str(value)


def _safe(d: dict | None, key: str, default: Any = None) -> Any:
    if not d:
        return default
    return d.get(key, default)


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def _style(name: str, **kwargs) -> ParagraphStyle:
    base = dict(
        fontName="Helvetica",
        fontSize=9,
        textColor=C_TEXT,
        leading=13,
        spaceAfter=0,
        spaceBefore=0,
    )
    base.update(kwargs)
    return ParagraphStyle(name, **base)


S_NORMAL = _style("Normal")
S_MUTED = _style("Muted", textColor=C_TEXT_SEC)
S_SMALL = _style("Small", fontSize=7, textColor=C_TEXT_SEC)
S_BOLD = _style("Bold", fontName="Helvetica-Bold")
S_TITLE = _style("Title", fontName="Helvetica-Bold", fontSize=16, textColor=C_TEXT)
S_GREEN = _style("Green", textColor=C_GREEN)
S_GREEN_BOLD = _style("GreenBold", fontName="Helvetica-Bold", textColor=C_GREEN)
S_ORANGE = _style("Orange", textColor=C_ORANGE)
S_RED = _style("Red", textColor=C_RED)
S_PURPLE = _style("Purple", textColor=C_PURPLE)
S_YELLOW = _style("Yellow", textColor=C_YELLOW)
S_HEADER = _style(
    "Header",
    fontName="Helvetica-Bold",
    fontSize=11,
    textColor=colors.white,
    leading=16,
)
S_SECTION_NUM = _style(
    "SectionNum",
    fontName="Helvetica-Bold",
    fontSize=8,
    textColor=HexColor("#ff9999"),
)


# ---------------------------------------------------------------------------
# Custom Flowables
# ---------------------------------------------------------------------------

class DarkBackground(Flowable):
    """Fills the entire current page with the dark background colour."""

    def __init__(self):
        super().__init__()
        self.width = 0
        self.height = 0

    def draw(self):
        pass  # handled via onPage callback


class SectionHeader(Flowable):
    """Full-width F1-red section header bar."""

    BAR_H = 22

    def __init__(self, number: str, title: str, doc_width: float):
        super().__init__()
        self.number = number
        self.title = title
        self.width = doc_width
        self.height = self.BAR_H + 4

    def draw(self):
        c = self.canv
        c.setFillColor(C_SECTION)
        c.rect(0, 2, self.width, self.BAR_H, fill=1, stroke=0)

        c.setFillColor(HexColor("#ff9999"))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(6, 2 + self.BAR_H - 10, self.number.upper())

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(6, 2 + 5, self.title.upper())


class CoverBigTime(Flowable):
    """Centred large best-lap time in green for the cover page."""

    def __init__(self, time_str: str, doc_width: float):
        super().__init__()
        self.time_str = time_str
        self.width = doc_width
        self.height = 70

    def draw(self):
        c = self.canv
        c.setFillColor(C_GREEN)
        c.setFont("Helvetica-Bold", 48)
        c.drawCentredString(self.width / 2, 10, self.time_str)


class ScoreBar(Flowable):
    """Horizontal filled bar proportional to a 0-100 score."""

    BAR_W = 300
    BAR_H = 16

    def __init__(self, score: int):
        super().__init__()
        self.score = max(0, min(100, score))
        self.width = self.BAR_W
        self.height = self.BAR_H + 4

    def draw(self):
        c = self.canv
        # background
        c.setFillColor(C_CARD)
        c.roundRect(0, 2, self.BAR_W, self.BAR_H, 4, fill=1, stroke=0)
        # fill
        fill_w = int(self.BAR_W * self.score / 100)
        if self.score >= 80:
            fill_col = C_GREEN
        elif self.score >= 40:
            fill_col = C_ORANGE
        else:
            fill_col = C_RED
        if fill_w > 0:
            c.setFillColor(fill_col)
            c.roundRect(0, 2, fill_w, self.BAR_H, 4, fill=1, stroke=0)
        # label
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(self.BAR_W / 2, 6, f"{self.score} / 100")


class BiasBar(Flowable):
    """Front vs rear brake balance visual bar."""

    BAR_W = 280
    BAR_H = 14

    def __init__(self, front_pct: float, rear_pct: float):
        super().__init__()
        self.front = max(0.0, min(100.0, front_pct))
        self.rear = max(0.0, min(100.0, rear_pct))
        self.width = self.BAR_W
        self.height = self.BAR_H + 20

    def draw(self):
        c = self.canv
        total = self.front + self.rear or 100.0
        front_w = int(self.BAR_W * self.front / total)

        c.setFillColor(C_ORANGE)
        c.rect(0, 4, front_w, self.BAR_H, fill=1, stroke=0)

        c.setFillColor(HexColor("#334155"))
        c.rect(front_w, 4, self.BAR_W - front_w, self.BAR_H, fill=1, stroke=0)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(2, 4 + 3, f"Delantera {self.front:.1f}%")
        c.drawRightString(self.BAR_W - 2, 4 + 3, f"Trasera {self.rear:.1f}%")

        c.setFillColor(C_TEXT_SEC)
        c.setFont("Helvetica", 6)
        c.drawCentredString(self.BAR_W / 2, 0, "Balance de frenos")


# ---------------------------------------------------------------------------
# Background callback
# ---------------------------------------------------------------------------

def _dark_page(canvas, doc):
    """onPage callback — fills page background."""
    canvas.saveState()
    canvas.setFillColor(C_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Table styling helpers
# ---------------------------------------------------------------------------

def _card_table_style(
    data: list[list],
    col_widths: list[float] | None = None,
    extra: list | None = None,
) -> Table:
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), C_BORDER),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_TEXT_SEC),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_CARD, C_ROW_ALT]),
        ("TEXTCOLOR", (0, 1), (-1, -1), C_TEXT),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if extra:
        style_cmds.extend(extra)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    return t


def _metric_box(label: str, value: str, value_col=None) -> Table:
    """Small 1-column dark card: label + value."""
    if value_col is None:
        value_col = C_TEXT
    data = [
        [Paragraph(label, S_SMALL)],
        [Paragraph(f"<b>{value}</b>", _style("v", fontName="Helvetica-Bold", fontSize=13, textColor=value_col))],
    ]
    t = Table(data, colWidths=[None])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _two_col_grid(boxes: list, col_widths: list[float]) -> Table:
    """Place metric boxes in a 2-column layout."""
    pairs = []
    it = iter(boxes)
    for b in it:
        try:
            pairs.append([b, next(it)])
        except StopIteration:
            pairs.append([b, ""])
    t = Table(pairs, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


# ---------------------------------------------------------------------------
# Tyre temp colour
# ---------------------------------------------------------------------------

def _tyre_temp_color(t: float | None) -> HexColor:
    if t is None:
        return C_TEXT_MUTED
    if t < 80:
        return C_GREEN
    if t < 100:
        return C_YELLOW
    if t < 110:
        return C_ORANGE
    return C_RED


def _brake_temp_color(t: float | None) -> HexColor:
    if t is None:
        return C_TEXT_MUTED
    if t < 200:
        return C_GREEN
    if t < 400:
        return C_YELLOW
    if t < 600:
        return C_ORANGE
    return C_RED


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_0(report: dict, content_w: float) -> list:
    """Sección 0 — Información del Circuito."""
    track = report.get("section_0_track")
    if not track:
        return []

    story: list = []
    story.append(SectionHeader("Sección 0", "Información del Circuito", content_w))
    story.append(Spacer(1, 10))

    display_name = track.get("display_name") or track.get("raw_track_id", "Desconocido")
    country = track.get("country") or "País desconocido"
    track_type = track.get("track_type", "unknown")
    length_m = track.get("length_m")
    turns = track.get("turns")
    notes = track.get("notes")
    characteristics = track.get("characteristics") or []
    sectors = track.get("sectors") or []
    key_corners = track.get("key_corners") or []
    lap_record = track.get("lap_record")
    source = track.get("source", "unknown")

    type_label = "REAL" if track_type == "real" else "MOD / FICTICIO" if track_type == "fictional" else "DESCONOCIDO"
    type_color = C_GREEN if track_type == "real" else C_PURPLE if track_type == "fictional" else C_TEXT_MUTED

    # Header row
    header_items = [display_name]
    details = []
    if country:
        details.append(country)
    if length_m:
        details.append(f"{length_m / 1000:.3f} km")
    if turns:
        details.append(f"{turns} curvas")
    if source == "claude":
        details.append("Generado por IA")
    if details:
        header_items.append(" · ".join(details))

    hdr_data = [[
        Paragraph(f"<b>{header_items[0]}</b>", _style("t0n", fontName="Helvetica-Bold", fontSize=16, textColor=C_TEXT)),
        Paragraph(f"<b>{type_label}</b>", _style("t0t", fontName="Helvetica-Bold", fontSize=9, textColor=type_color)),
    ]]
    if len(header_items) > 1:
        hdr_data.append([
            Paragraph(header_items[1], S_MUTED),
            Paragraph(""),
        ])
    hdr_table = Table(hdr_data, colWidths=[content_w * 0.8, content_w * 0.2])
    hdr_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(hdr_table)
    story.append(Spacer(1, 8))

    # Characteristics tags
    if characteristics:
        tags_text = "  ·  ".join(characteristics)
        story.append(Paragraph(f"<b>Características:</b> {tags_text}", S_MUTED))
        story.append(Spacer(1, 8))

    # Map image
    map_path = track.get("map_path")
    if map_path:
        from pathlib import Path as _Path
        img_file = _Path(map_path)
        if img_file.exists():
            try:
                from reportlab.platypus import Image as RLImage
                max_w = content_w
                max_h = 80 * mm
                img = RLImage(str(img_file), width=max_w, height=max_h, kind="bound")
                story.append(img)
                story.append(Spacer(1, 8))
            except Exception:
                pass

    # Lap record
    if lap_record:
        rec_data = [[
            Paragraph("RÉCORD OFICIAL", _style("rk", fontSize=7, textColor=C_TEXT_MUTED, fontName="Helvetica-Bold")),
            Paragraph(f"<b>{lap_record.get('time', 'N/D')}</b>", _style("rt", fontName="Helvetica-Bold", fontSize=14, textColor=C_GREEN)),
            Paragraph(
                f"{lap_record.get('driver', '')} · {lap_record.get('series', '')} · {lap_record.get('year', '')}",
                _style("rd", fontSize=8, textColor=C_TEXT_SEC)
            ),
        ]]
        rec_table = Table(rec_data, colWidths=[content_w * 0.25, content_w * 0.25, content_w * 0.5])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
            ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 8))

    # Sectors
    if sectors:
        story.append(Paragraph("<b>Sectores</b>", _style("sh", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT_SEC)))
        story.append(Spacer(1, 4))
        sector_colors = [C_SECTION, HexColor("#2563eb"), C_GREEN]
        for i, sector in enumerate(sectors[:3]):
            col = sector_colors[i] if i < len(sector_colors) else C_TEXT_MUTED
            story.append(Paragraph(f"<b>{sector}</b>", _style(f"s{i}", fontSize=8, textColor=col)))
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 6))

    # Key corners
    if key_corners:
        story.append(Paragraph("<b>Curvas clave</b>", _style("ckh", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT_SEC)))
        story.append(Spacer(1, 4))
        corner_data = []
        for corner in key_corners[:6]:
            corner_data.append([
                Paragraph(f"<b>{corner.get('name', '')}</b>", _style("cn", fontName="Helvetica-Bold", fontSize=8, textColor=C_TEXT)),
                Paragraph(corner.get("type", ""), _style("ct", fontSize=7, textColor=C_TEXT_MUTED)),
                Paragraph(corner.get("tip", ""), _style("ctip", fontSize=7, textColor=C_TEXT_SEC)),
            ])
        if corner_data:
            third = content_w / 3
            corners_table = Table(corner_data, colWidths=[third * 0.9, third * 0.7, third * 1.4])
            corners_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_CARD, C_ROW_ALT]),
                ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(corners_table)
        story.append(Spacer(1, 6))

    # Notes
    if notes:
        story.append(Paragraph(f"<i>{notes}</i>", _style("nt", fontSize=8, textColor=C_TEXT_MUTED)))
        story.append(Spacer(1, 8))

    story.append(HRFlowable(width=content_w, thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 12))
    return story


def _cover(report: dict, content_w: float) -> list:
    meta = report.get("meta", {})
    s1 = report.get("section_1_summary", {})

    best_fmt = _safe(s1, "best_lap_fmt", "N/D")

    story = []

    # Top banner
    banner_data = [["DELTA — INFORME DE SESIÓN"]]
    banner = Table(banner_data, colWidths=[content_w])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_SECTION),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 16),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(banner)
    story.append(Spacer(1, 20))

    # Big time
    story.append(CoverBigTime(best_fmt, content_w))
    story.append(Paragraph("MEJOR VUELTA", _style("cbl", fontName="Helvetica-Bold", fontSize=9, textColor=C_GREEN, alignment=1)))
    story.append(Spacer(1, 24))

    # Pilot / session meta grid
    def _row(k, v):
        return [
            Paragraph(k, _style("ck", textColor=C_TEXT_SEC, fontSize=8)),
            Paragraph(f"<b>{v}</b>", _style("cv", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT)),
        ]

    track_display = (report.get("section_0_track") or {}).get("display_name") or meta.get("track")
    meta_rows = [
        _row("PILOTO", _v(meta.get("pilot"))),
        _row("CIRCUITO", _v(track_display)),
        _row("COCHE", _v(meta.get("car"))),
        _row("SIMULADOR", _v(meta.get("simulator"))),
        _row("FECHA", _v(meta.get("session_date"))),
        _row("TIPO DE SESIÓN", _v(meta.get("session_type"))),
        _row("COMPUESTO", _v(meta.get("tyre_compound"))),
    ]

    meta_table = Table(meta_rows, colWidths=[content_w * 0.35, content_w * 0.65])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 30))

    # Bottom bar
    bottom_data = [["Generado por Delta · SimTelemetry Pro"]]
    bottom = Table(bottom_data, colWidths=[content_w])
    bottom.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#1c1c1c")),
        ("TEXTCOLOR", (0, 0), (-1, -1), C_TEXT_MUTED),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(bottom)
    story.append(PageBreak())
    return story


def _section_1(report: dict, content_w: float) -> list:
    s = report.get("section_1_summary", {}) or {}
    story: list = []
    story.append(SectionHeader("Sección 1", "Resumen Ejecutivo", content_w))
    story.append(Spacer(1, 10))

    half = (content_w - 6) / 2

    # Row 1 — main lap stats
    boxes_r1 = [
        _metric_box("VUELTAS TOTALES", _v(s.get("total_laps"))),
        _metric_box("VUELTAS VÁLIDAS", _v(s.get("valid_laps"))),
        _metric_box("MEJOR VUELTA", _v(s.get("best_lap_fmt"), default="N/D"), C_GREEN),
        _metric_box("PEOR VUELTA", _v(s.get("worst_lap_fmt"), default="N/D"), C_RED),
        _metric_box("PROMEDIO", _v(s.get("avg_lap_fmt"), default="N/D")),
        _metric_box("DESVIACIÓN STD", f"{_v(s.get('section_3_consistency', {}) and report.get('section_3_consistency', {}).get('std_dev'), '.3f', 'N/D')} s"),
    ]

    def _pair_table(bxs: list) -> Table:
        rows = []
        it = iter(bxs)
        for b in it:
            try:
                rows.append([b, next(it)])
            except StopIteration:
                rows.append([b, ""])
        t = Table(rows, colWidths=[half, half])
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    # std_dev from consistency section
    std_dev = _v(report.get("section_3_consistency", {}) and report.get("section_3_consistency", {}).get("std_dev"), ".3f", "N/D")
    boxes_r1 = [
        _metric_box("VUELTAS TOTALES", _v(s.get("total_laps"))),
        _metric_box("VUELTAS VÁLIDAS", _v(s.get("valid_laps"))),
        _metric_box("MEJOR VUELTA", _v(s.get("best_lap_fmt")), C_GREEN),
        _metric_box("PEOR VUELTA", _v(s.get("worst_lap_fmt")), C_RED),
        _metric_box("PROMEDIO", _v(s.get("avg_lap_fmt"))),
        _metric_box("DESVIACIÓN STD", f"{std_dev} s"),
    ]
    story.append(_pair_table(boxes_r1))
    story.append(Spacer(1, 6))

    # Row 2 — theoretical best & telemetry
    fuel = s.get("fuel_used_per_lap")
    fuel_str = f"{fuel:.2f} L" if fuel is not None else "N/D"
    throttle = s.get("throttle_full_pct")
    throttle_str = f"{throttle:.1f}%" if throttle is not None else "N/D"
    speed = s.get("max_speed_kmh")
    speed_str = f"{speed:.1f} km/h" if speed is not None else "N/D"
    rpm = s.get("rpm_max")
    rpm_str = f"{rpm:.0f}" if rpm is not None else "N/D"

    boxes_r2 = [
        _metric_box("TEÓRICO ÓPTIMO", _v(s.get("theoretical_best_fmt")), C_PURPLE),
        _metric_box("GANANCIA POTENCIAL", f"{s.get('potential_gain', 0):.3f} s"),
        _metric_box("VEL. MÁXIMA", speed_str),
        _metric_box("ACELERADOR PLENO", throttle_str),
        _metric_box("RPM MÁXIMO", rpm_str),
        _metric_box("COMBUSTIBLE/VUELTA", fuel_str),
    ]
    story.append(_pair_table(boxes_r2))
    story.append(Spacer(1, 8))

    # Sector bests row
    third = (content_w - 6) / 3
    sector_data = [[
        Paragraph(f"<b>S1 MEJOR: {_v(s.get('best_s1_fmt'))}</b>", _style("s1", fontName="Helvetica-Bold", fontSize=10, textColor=C_PURPLE, alignment=1)),
        Paragraph(f"<b>S2 MEJOR: {_v(s.get('best_s2_fmt'))}</b>", _style("s2", fontName="Helvetica-Bold", fontSize=10, textColor=C_PURPLE, alignment=1)),
        Paragraph(f"<b>S3 MEJOR: {_v(s.get('best_s3_fmt'))}</b>", _style("s3", fontName="Helvetica-Bold", fontSize=10, textColor=C_PURPLE, alignment=1)),
    ]]
    sector_table = Table(sector_data, colWidths=[third, third, third])
    sector_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CARD_PURPLE),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(sector_table)
    story.append(PageBreak())
    return story


def _section_2(report: dict, content_w: float) -> list:
    rows = report.get("section_2_lap_table", []) or []
    story: list = []
    story.append(SectionHeader("Sección 2", "Tabla de Vueltas", content_w))
    story.append(Spacer(1, 8))

    MAX_ROWS = 50
    truncated = len(rows) > MAX_ROWS
    display_rows = rows[:MAX_ROWS]

    if not display_rows:
        story.append(Paragraph("No hay datos de vueltas disponibles.", S_MUTED))
        story.append(PageBreak())
        return story

    if truncated:
        story.append(Paragraph(
            f"Mostrando las primeras {MAX_ROWS} de {len(rows)} vueltas.",
            _style("trunc", textColor=C_ORANGE, fontSize=8),
        ))
        story.append(Spacer(1, 4))

    headers = ["#", "TIEMPO", "S1", "S2", "S3", "DELTA", "ESTADO"]
    col_w_raw = [0.05, 0.14, 0.12, 0.12, 0.12, 0.12, 0.33]
    col_widths = [content_w * r for r in col_w_raw]

    table_data = [headers]
    style_cmds: list = [
        ("BACKGROUND", (0, 0), (-1, 0), C_BORDER),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_TEXT_SEC),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("TEXTCOLOR", (0, 1), (-1, -1), C_TEXT),
    ]

    for i, lap in enumerate(display_rows, start=1):
        row_idx = i  # 0 = header
        lap_num = lap.get("lap_number", i)
        is_best = lap.get("is_best", False)
        valid = lap.get("valid", True)
        is_best_s1 = lap.get("is_best_s1", False)
        is_best_s2 = lap.get("is_best_s2", False)
        is_best_s3 = lap.get("is_best_s3", False)

        status = lap.get("status", "")
        delta_fmt = lap.get("delta_fmt", "")
        delta_val = lap.get("delta", 0.0) or 0.0

        delta_col = C_TEXT
        if isinstance(delta_val, (int, float)):
            if delta_val < 0:
                delta_col = C_GREEN
            elif delta_val > 0:
                delta_col = C_RED

        incidents = lap.get("incidents", []) or []
        incident_str = ""
        if incidents:
            parts = [f"[{inc.get('type', '?')}]" for inc in incidents[:3]]
            incident_str = " ".join(parts)

        state_display = status
        if incident_str:
            state_display = f"{status} {incident_str}"

        # Alternate row background
        bg = C_CARD if i % 2 == 0 else C_ROW_ALT
        if is_best:
            bg = C_CARD_GREEN
        elif not valid:
            bg = C_CARD_RED

        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg))

        # Best sector cell highlights
        if is_best_s1:
            style_cmds.append(("BACKGROUND", (2, row_idx), (2, row_idx), C_CARD_PURPLE))
            style_cmds.append(("TEXTCOLOR", (2, row_idx), (2, row_idx), C_PURPLE))
        if is_best_s2:
            style_cmds.append(("BACKGROUND", (3, row_idx), (3, row_idx), C_CARD_PURPLE))
            style_cmds.append(("TEXTCOLOR", (3, row_idx), (3, row_idx), C_PURPLE))
        if is_best_s3:
            style_cmds.append(("BACKGROUND", (4, row_idx), (4, row_idx), C_CARD_PURPLE))
            style_cmds.append(("TEXTCOLOR", (4, row_idx), (4, row_idx), C_PURPLE))

        if is_best:
            style_cmds.append(("TEXTCOLOR", (1, row_idx), (1, row_idx), C_GREEN))
            style_cmds.append(("FONTNAME", (1, row_idx), (1, row_idx), "Helvetica-Bold"))

        if incidents:
            style_cmds.append(("TEXTCOLOR", (6, row_idx), (6, row_idx), C_ORANGE))

        table_data.append([
            str(lap_num),
            lap.get("lap_time_fmt", ""),
            lap.get("s1_fmt", ""),
            lap.get("s2_fmt", ""),
            lap.get("s3_fmt", ""),
            delta_fmt,
            state_display,
        ])

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    story.append(t)
    story.append(PageBreak())
    return story


def _section_3(report: dict, content_w: float) -> list:
    s = report.get("section_3_consistency") or {}
    story: list = []
    story.append(SectionHeader("Sección 3", "Consistencia", content_w))
    story.append(Spacer(1, 12))

    score = s.get("score", 0) or 0
    label = s.get("label", "N/D")
    std_dev = s.get("std_dev")
    interpretation = s.get("interpretation") or "Sin datos de interpretación."

    if score >= 80:
        score_col = C_GREEN
    elif score >= 40:
        score_col = C_ORANGE
    else:
        score_col = C_RED

    score_data = [[
        Paragraph(f"<b>{score}</b>", _style("sc", fontName="Helvetica-Bold", fontSize=42, textColor=score_col)),
        [
            Paragraph(f"<b>/ 100</b>", _style("sc100", fontName="Helvetica-Bold", fontSize=18, textColor=C_TEXT_MUTED)),
            Spacer(1, 4),
            Paragraph(f"<b>{label}</b>", _style("lbl", fontName="Helvetica-Bold", fontSize=13, textColor=score_col)),
            Spacer(1, 4),
            Paragraph(f"Desviación estándar: {_v(std_dev, '.3f')} s", S_MUTED),
        ],
    ]]
    score_table = Table(score_data, colWidths=[content_w * 0.3, content_w * 0.7])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 12))
    story.append(ScoreBar(score))
    story.append(Spacer(1, 12))
    story.append(Paragraph(interpretation, S_MUTED))
    story.append(Spacer(1, 12))
    return story


def _corner_table(title: str, data_dict: dict | None, value_key: str, color_fn, unit: str, content_w: float) -> list:
    """Render a 4-corner (FL/FR/RL/RR) stats table."""
    story: list = []
    story.append(Paragraph(f"<b>{title}</b>", _style("ct", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT_SEC)))
    story.append(Spacer(1, 4))

    if not data_dict:
        story.append(Paragraph("Sin datos disponibles.", S_MUTED))
        story.append(Spacer(1, 8))
        return story

    corners = ["FL", "FR", "RL", "RR"]
    keys = list((data_dict.get("FL") or {}).keys()) if data_dict.get("FL") else ["avg", "max", "min"]

    header = [""] + [f"{k.upper()} ({unit})" for k in keys]
    col_w = [content_w * 0.15] + [(content_w * 0.85) / len(keys)] * len(keys)

    rows = [header]
    for corner in corners:
        cd = data_dict.get(corner) or {}
        row = [corner]
        for k in keys:
            val = cd.get(k)
            if val is not None:
                col = color_fn(cd.get("avg", val))
                row.append(Paragraph(f"<b>{val:.1f}</b>", _style(f"c{corner}{k}", fontName="Helvetica-Bold", fontSize=8, textColor=col, alignment=1)))
            else:
                row.append(Paragraph("N/D", _style("na", textColor=C_TEXT_MUTED, alignment=1)))
        rows.append(row)

    t = _card_table_style(rows, col_widths=col_w)
    story.append(t)
    story.append(Spacer(1, 8))
    return story


def _section_4(report: dict, content_w: float) -> list:
    s = report.get("section_4_tyres") or {}
    story: list = []
    story.append(SectionHeader("Sección 4", "Análisis de Gomas", content_w))
    story.append(Spacer(1, 8))

    if not s:
        story.append(Paragraph("Sin datos de gomas disponibles.", S_MUTED))
        story.append(Spacer(1, 8))
        return story

    # Temperatures
    story.extend(_corner_table("Temperatura de Gomas", s.get("temp"), "avg", _tyre_temp_color, "°C", content_w))

    # Pressures
    press = s.get("press")
    if press:
        story.append(Paragraph("<b>Presión de Gomas (psi / bar)</b>", _style("ptit", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT_SEC)))
        story.append(Spacer(1, 4))
        corners = ["FL", "FR", "RL", "RR"]
        keys = ["avg", "max", "min"]
        header = [""] + [k.upper() for k in keys]
        col_w = [content_w * 0.15] + [(content_w * 0.85) / 3] * 3
        rows = [header]
        for c in corners:
            cd = press.get(c) or {}
            row = [c] + [f"{cd.get(k, 0):.2f}" if cd.get(k) is not None else "N/D" for k in keys]
            rows.append(row)
        story.append(_card_table_style(rows, col_widths=col_w))
        story.append(Spacer(1, 8))

    # Camber diagnosis
    camber = s.get("camber_table")
    if camber:
        story.append(Paragraph("<b>Diagnóstico de Camber</b>", _style("camp", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT_SEC)))
        story.append(Spacer(1, 4))
        header = ["ESQUINA", "INNER", "MID", "OUTER", "DIAGNÓSTICO"]
        col_w = [cw * content_w for cw in [0.12, 0.12, 0.12, 0.12, 0.52]]
        rows = [header]
        for entry in camber:
            rows.append([
                entry.get("corner", ""),
                f"{entry['inner']:.2f}" if entry.get("inner") is not None else "N/D",
                f"{entry['mid']:.2f}" if entry.get("mid") is not None else "N/D",
                f"{entry['outer']:.2f}" if entry.get("outer") is not None else "N/D",
                entry.get("diagnosis", ""),
            ])
        story.append(_card_table_style(rows, col_widths=col_w))
        story.append(Spacer(1, 8))

    # Slip
    slip = s.get("slip")
    if slip:
        story.append(Paragraph("<b>Slip de Gomas</b>", _style("sl", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT_SEC)))
        story.append(Spacer(1, 4))
        header = [""] + ["AVG", "MAX"]
        col_w = [content_w * 0.15, content_w * 0.425, content_w * 0.425]
        rows = [header]
        for c in ["FL", "FR", "RL", "RR"]:
            cd = slip.get(c) or {}
            rows.append([c, f"{cd.get('avg', 0):.3f}", f"{cd.get('max', 0):.3f}"])
        story.append(_card_table_style(rows, col_widths=col_w))

    story.append(Spacer(1, 12))
    return story


def _section_5(report: dict, content_w: float) -> list:
    s = report.get("section_5_brakes") or {}
    story: list = []
    story.append(SectionHeader("Sección 5", "Frenos", content_w))
    story.append(Spacer(1, 8))

    if not s:
        story.append(Paragraph("Sin datos de frenos disponibles.", S_MUTED))
        story.append(Spacer(1, 8))
        return story

    # Brake temps
    temps = s.get("temp")
    if temps:
        story.extend(_corner_table("Temperatura de Frenos", temps, "avg", _brake_temp_color, "°C", content_w))

    # Balance bar
    balance = s.get("balance")
    if balance:
        front = balance.get("front_avg") or 0.0
        rear = balance.get("rear_avg") or 0.0
        story.append(Spacer(1, 8))
        story.append(BiasBar(front, rear))
        story.append(Spacer(1, 6))
        bias_label = balance.get("bias", "")
        if bias_label:
            _bias_es = {"front_heavy": "Delantera dominante", "rear_heavy": "Trasera dominante", "balanced": "Equilibrada"}
            story.append(Paragraph(f"Tendencia: <b>{_bias_es.get(bias_label, bias_label)}</b>", S_MUTED))

    # Warning
    warning = s.get("warning")
    if warning:
        story.append(Spacer(1, 8))
        story.append(Paragraph(f"AVISO: {warning}", _style("warn", textColor=C_ORANGE, fontName="Helvetica-Bold", fontSize=9)))

    story.append(Spacer(1, 12))
    return story


def _section_6(report: dict, content_w: float) -> list:
    s = report.get("section_6_dynamics") or {}
    story: list = []
    story.append(SectionHeader("Sección 6", "G-Forces y Dinámica", content_w))
    story.append(Spacer(1, 8))

    if not s:
        story.append(Paragraph("Sin datos de dinámica disponibles.", S_MUTED))
        story.append(Spacer(1, 8))
        return story

    # G-forces table
    gforces = s.get("g_forces")
    if gforces:
        story.append(Paragraph("<b>Fuerzas G</b>", _style("gf", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT_SEC)))
        story.append(Spacer(1, 4))
        header = ["MÉTRICA", "VALOR", "INTERPRETACIÓN"]
        col_w = [content_w * 0.25, content_w * 0.2, content_w * 0.55]
        rows = [header]
        for g in gforces:
            rows.append([
                g.get("metric", ""),
                g.get("value", ""),
                g.get("interpretation", ""),
            ])
        story.append(_card_table_style(rows, col_widths=col_w))
        story.append(Spacer(1, 10))

    # Suspension table
    susp = s.get("suspension")
    if susp:
        story.append(Paragraph("<b>Suspensión</b>", _style("su", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT_SEC)))
        story.append(Spacer(1, 4))
        header = ["ESQUINA", "MEDIA (mm)", "RANGO (mm)", "MÍN (mm)", "MÁX (mm)"]
        col_w = [content_w * 0.18, content_w * 0.205, content_w * 0.205, content_w * 0.205, content_w * 0.205]
        rows = [header]
        for entry in susp:
            rows.append([
                entry.get("corner", ""),
                f"{entry.get('avg_mm', 0):.2f}",
                f"{entry.get('range_mm', 0):.2f}",
                f"{entry.get('min_mm', 0):.2f}",
                f"{entry.get('max_mm', 0):.2f}",
            ])
        story.append(_card_table_style(rows, col_widths=col_w))

    story.append(Spacer(1, 12))
    return story


def _section_7(report: dict, content_w: float) -> list:
    s = report.get("section_7_setup") or {}
    story: list = []
    story.append(SectionHeader("Sección 7", "Setup del Coche", content_w))
    story.append(Spacer(1, 8))

    has_setup = s.get("has_setup_data", False)

    if not has_setup:
        note = s.get("note") or "No hay datos de setup disponibles."
        story.append(Paragraph(note, S_MUTED))
        story.append(Spacer(1, 8))
        return story

    source = s.get("source", "")
    if source:
        story.append(Paragraph(f"Fuente: <b>{source.upper()}</b>", S_SMALL))
        story.append(Spacer(1, 6))

    # Tyre pressures
    tyre_press = s.get("tyre_pressures")
    if tyre_press:
        story.append(Paragraph("<b>Presiones de Gomas (configuración)</b>", _style("tp", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT_SEC)))
        story.append(Spacer(1, 4))
        header = ["POSICIÓN", "PRESIÓN"]
        col_w = [content_w * 0.4, content_w * 0.6]
        rows = [header]
        for item in tyre_press:
            if isinstance(item, dict):
                rows.append([str(item.get("position", "")), str(item.get("value", ""))])
            else:
                rows.append([str(item), ""])
        story.append(_card_table_style(rows, col_widths=col_w))
        story.append(Spacer(1, 10))

    # Raw .ini groups
    raw = s.get("raw")
    if raw and isinstance(raw, dict):
        _KNOWN_GROUPS = ["electronics", "tyres", "brakes", "suspension", "differential", "aero", "fuel", "engine"]
        for group_name, group_data in raw.items():
            if not isinstance(group_data, dict):
                continue
            # Show section label
            story.append(Paragraph(f"<b>[{group_name.upper()}]</b>", _style("sg", fontName="Helvetica-Bold", fontSize=9, textColor=C_TEXT_SEC)))
            story.append(Spacer(1, 3))
            header = ["PARÁMETRO", "VALOR"]
            col_w = [content_w * 0.55, content_w * 0.45]
            rows = [header]
            for k, v in group_data.items():
                if isinstance(v, (list, tuple)):
                    # 4-corner values
                    rows.append([k, " / ".join(str(x) for x in v)])
                else:
                    rows.append([k, str(v)])
            if len(rows) > 1:
                story.append(_card_table_style(rows, col_widths=col_w))
            story.append(Spacer(1, 6))

    story.append(Spacer(1, 12))
    return story


def _bullet_list(items: list[str], style: ParagraphStyle, prefix: str = "•") -> list:
    out = []
    for item in items:
        out.append(Paragraph(f"{prefix} {item}", style))
        out.append(Spacer(1, 3))
    return out


def _section_8(report: dict, content_w: float) -> list:
    s = report.get("section_8_technical")
    story: list = []
    story.append(SectionHeader("Sección 8", "Análisis Técnico", content_w))
    story.append(Spacer(1, 10))

    if not s:
        story.append(Paragraph("Sin análisis técnico disponible.", S_MUTED))
        story.append(PageBreak())
        return story

    strengths = s.get("strengths") or []
    improvements = s.get("improvements") or []
    setup_rec = s.get("setup_recommendations") or []

    if strengths:
        story.append(Paragraph("<b>FORTALEZAS</b>", _style("str", fontName="Helvetica-Bold", fontSize=10, textColor=C_GREEN)))
        story.append(Spacer(1, 5))
        story.extend(_bullet_list(strengths, _style("sb", textColor=C_GREEN, fontSize=9)))
        story.append(Spacer(1, 8))

    if improvements:
        story.append(Paragraph("<b>ÁREAS DE MEJORA</b>", _style("imp", fontName="Helvetica-Bold", fontSize=10, textColor=C_ORANGE)))
        story.append(Spacer(1, 5))
        story.extend(_bullet_list(improvements, _style("ib", textColor=C_ORANGE, fontSize=9)))
        story.append(Spacer(1, 8))

    if setup_rec:
        story.append(Paragraph("<b>RECOMENDACIONES DE SETUP</b>", _style("sr", fontName="Helvetica-Bold", fontSize=10, textColor=C_YELLOW)))
        story.append(Spacer(1, 5))
        story.extend(_bullet_list(setup_rec, _style("srb", textColor=C_YELLOW, fontSize=9)))

    story.append(PageBreak())
    return story


def _section_9(report: dict, content_w: float) -> list:
    opps = report.get("section_9_opportunities") or []
    story: list = []
    story.append(SectionHeader("Sección 9", "Top Oportunidades de Mejora", content_w))
    story.append(Spacer(1, 10))

    if not opps:
        story.append(Paragraph("Sin oportunidades detectadas.", S_MUTED))
        story.append(PageBreak())
        return story

    for opp in opps:
        rank = opp.get("rank", "?")
        title = opp.get("title", "")
        detail = opp.get("detail", "")
        gain = opp.get("estimated_gain_s")
        occurs = opp.get("occurs_in", "")

        card_data = [[
            Paragraph(f"<b>#{rank} — {title}</b>", _style("ot", fontName="Helvetica-Bold", fontSize=10, textColor=C_TEXT)),
            Paragraph(
                f"+{gain:.3f} s" if gain is not None else "N/D",
                _style("og", fontName="Helvetica-Bold", fontSize=12, textColor=C_GREEN, alignment=2),
            ),
        ]]
        card_table = Table(card_data, colWidths=[content_w * 0.75, content_w * 0.25])
        card_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
            ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(card_table)
        story.append(Spacer(1, 3))

        detail_data = [[
            Paragraph(detail, _style("od", textColor=C_TEXT_SEC, fontSize=8)),
            Paragraph(f"Ocurre en: {occurs}", _style("oo", textColor=C_TEXT_MUTED, fontSize=7, alignment=2)),
        ]]
        detail_table = Table(detail_data, colWidths=[content_w * 0.75, content_w * 0.25])
        detail_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#111111")),
            ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(detail_table)
        story.append(Spacer(1, 8))

    story.append(PageBreak())
    return story


def _section_10(report: dict, content_w: float) -> list:
    s = report.get("section_10_action_plan")
    story: list = []
    story.append(SectionHeader("Sección 10", "Plan de Acción", content_w))
    story.append(Spacer(1, 10))

    if not s:
        story.append(Paragraph("Sin plan de acción disponible.", S_MUTED))
        story.append(PageBreak())
        return story

    # Focuses
    focuses = s.get("focuses") or []
    for focus in focuses:
        title = focus.get("title", "")
        exercise = focus.get("exercise", "")
        objective = focus.get("objective", "")

        rows = [
            [Paragraph(f"<b>{title}</b>", _style("ft", fontName="Helvetica-Bold", fontSize=10, textColor=C_TEXT))],
            [Paragraph(f"Ejercicio: {exercise}", _style("fe", textColor=C_TEXT_SEC, fontSize=8))],
            [Paragraph(f"Objetivo: {objective}", _style("fo", textColor=C_GREEN, fontSize=8))],
        ]
        card = Table(rows, colWidths=[content_w])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
            ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(card)
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 8))

    # Targets
    target_fmt = s.get("target_lap_time_fmt", "N/D")
    target_cs = s.get("target_consistency_score", "N/D")
    timeline = s.get("timeline", "N/D")

    target_rows = [
        ["TIEMPO OBJETIVO", Paragraph(f"<b>{target_fmt}</b>", _style("tf", fontName="Helvetica-Bold", fontSize=12, textColor=C_GREEN))],
        ["CONSISTENCIA OBJETIVO", Paragraph(f"<b>{target_cs} / 100</b>", _style("tcs", fontName="Helvetica-Bold", fontSize=12, textColor=C_YELLOW))],
        ["PLAZO", Paragraph(f"<b>{timeline}</b>", _style("tl", fontName="Helvetica-Bold", fontSize=10, textColor=C_TEXT))],
    ]
    target_table = Table(target_rows, colWidths=[content_w * 0.4, content_w * 0.6])
    target_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
        ("TEXTCOLOR", (0, 0), (0, -1), C_TEXT_SEC),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (0, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(target_table)
    story.append(PageBreak())
    return story


def _section_11(report: dict, content_w: float) -> list:
    s = report.get("section_11_engineer_diagnosis")
    story: list = []
    story.append(SectionHeader("Sección 11", "Diagnóstico del Ingeniero", content_w))
    story.append(Spacer(1, 10))

    if not s:
        story.append(Paragraph("Sin diagnóstico de ingeniero disponible.", S_MUTED))
        story.append(PageBreak())
        return story

    working = s.get("what_is_working") or []
    problems = s.get("problems_detected") or []
    driving_style = s.get("driving_style") or []
    setup_rec = s.get("setup_recommendations") or []
    next_target = s.get("next_session_target", "")

    if working:
        story.append(Paragraph("<b>QUÉ ESTÁ FUNCIONANDO</b>", _style("w", fontName="Helvetica-Bold", fontSize=10, textColor=C_GREEN)))
        story.append(Spacer(1, 5))
        story.extend(_bullet_list(working, _style("wb", textColor=C_GREEN, fontSize=9)))
        story.append(Spacer(1, 8))

    if problems:
        story.append(Paragraph("<b>PROBLEMAS DETECTADOS</b>", _style("pr", fontName="Helvetica-Bold", fontSize=10, textColor=C_RED)))
        story.append(Spacer(1, 5))
        story.extend(_bullet_list(problems, _style("pb", textColor=C_RED, fontSize=9)))
        story.append(Spacer(1, 8))

    if driving_style:
        story.append(Paragraph("<b>ESTILO DE CONDUCCIÓN</b>", _style("ds", fontName="Helvetica-Bold", fontSize=10, textColor=C_TEXT)))
        story.append(Spacer(1, 5))
        story.extend(_bullet_list(driving_style, _style("dsb", textColor=C_TEXT_SEC, fontSize=9)))
        story.append(Spacer(1, 8))

    if setup_rec:
        story.append(Paragraph("<b>RECOMENDACIONES DE SETUP</b>", _style("srr", fontName="Helvetica-Bold", fontSize=10, textColor=C_YELLOW)))
        story.append(Spacer(1, 5))
        story.extend(_bullet_list(setup_rec, _style("srrb", textColor=C_YELLOW, fontSize=9)))
        story.append(Spacer(1, 12))

    if next_target:
        target_data = [[Paragraph(f"PRÓXIMA SESIÓN: {next_target}", _style("nt", fontName="Helvetica-Bold", fontSize=11, textColor=C_GREEN, alignment=1))]]
        target_table = Table(target_data, colWidths=[content_w])
        target_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_CARD_GREEN),
            ("GRID", (0, 0), (-1, -1), 0.5, C_GREEN),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(target_table)

    return story  # last section — no PageBreak needed


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def generate_report_pdf(report: dict, output_path: str | Path) -> str:
    """
    Genera PDF completo de 11 secciones desde el dict de reporte.
    Retorna la ruta absoluta del PDF generado.
    """
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content_w = PAGE_W - 2 * MARGIN

    doc = BaseDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title="Delta — Informe de Sesión",
        author="Delta SimTelemetry Pro",
    )

    frame = Frame(
        MARGIN,
        MARGIN,
        content_w,
        PAGE_H - 2 * MARGIN,
        id="main",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )

    template = PageTemplate(id="main", frames=[frame], onPage=_dark_page)
    doc.addPageTemplates([template])

    story: list = []

    # Cover
    story.extend(_cover(report, content_w))

    # Section 0 — Track info (if available)
    story.extend(_section_0(report, content_w))

    # Section 1
    story.extend(_section_1(report, content_w))

    # Section 2
    story.extend(_section_2(report, content_w))

    # Section 3
    story.extend(_section_3(report, content_w))

    # Section 4
    story.extend(_section_4(report, content_w))

    # Section 5
    story.extend(_section_5(report, content_w))

    # Section 6
    story.extend(_section_6(report, content_w))

    # Section 7
    story.extend(_section_7(report, content_w))

    # Section 8 — start fresh after the telemetry data sections
    story.append(PageBreak())
    story.extend(_section_8(report, content_w))

    # Section 9
    story.extend(_section_9(report, content_w))

    # Section 10
    story.extend(_section_10(report, content_w))

    # Section 11
    story.extend(_section_11(report, content_w))

    doc.build(story)

    return str(output_path)

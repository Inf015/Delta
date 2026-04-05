"""
Server-side telemetry chart generation for PDF reports.
Uses matplotlib with dark F1 theme. Returns BytesIO PNG images.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any

import numpy as np


def _plt():
    """Lazy import — sets Agg backend before pyplot is imported."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def speed_throttle_chart(points: list[dict[str, Any]]) -> BytesIO:
    """Speed line (top) + Throttle/Brake area (bottom)."""
    plt = _plt()
    import matplotlib.gridspec as gridspec

    d        = [p["d"]        for p in points]
    speed    = [p["speed"]    for p in points]
    throttle = [p["throttle"] for p in points]
    brake    = [p["brake"]    for p in points]

    fig = plt.figure(figsize=(12, 5), facecolor="#111111")
    gs  = gridspec.GridSpec(2, 1, height_ratios=[3, 2], hspace=0.06)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    for ax in (ax1, ax2):
        ax.set_facecolor("#111111")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for sp in ax.spines.values():
            sp.set_color("#2a2a2a")
        ax.grid(True, color="#1e1e1e", linewidth=0.5, zorder=0)
        ax.tick_params(colors="#555555", labelsize=7)

    # Speed
    ax1.plot(d, speed, color="#d4d4d4", linewidth=1.5, zorder=3)
    ax1.fill_between(d, speed, alpha=0.08, color="#d4d4d4")
    ax1.set_ylabel("Velocidad (km/h)", color="#666666", fontsize=7)
    ax1.yaxis.label.set_color("#666666")
    plt.setp(ax1.get_xticklabels(), visible=False)

    # Throttle + Brake
    ax2.fill_between(d, throttle, alpha=0.22, color="#00cc44")
    ax2.plot(d, throttle, color="#00cc44", linewidth=1.2, label="Throttle", zorder=3)
    ax2.fill_between(d, brake,    alpha=0.28, color="#dd3333")
    ax2.plot(d, brake,    color="#dd3333", linewidth=1.2, label="Brake",    zorder=3)
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("%", color="#666666", fontsize=7)
    ax2.set_xlabel("Distancia de vuelta", color="#666666", fontsize=7)
    ax2.yaxis.label.set_color("#666666")
    ax2.xaxis.label.set_color("#666666")
    ax2.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax2.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    legend = ax2.legend(
        loc="upper right", fontsize=6,
        facecolor="#1a1a1a", edgecolor="#2a2a2a", labelcolor="#aaaaaa",
    )

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="#111111")
    plt.close(fig)
    buf.seek(0)
    return buf


def velocity_map_chart(points: list[dict[str, Any]]) -> BytesIO:
    """Track layout coloured by speed (blue→green→yellow→red)."""
    plt = _plt()
    from matplotlib.collections import LineCollection

    x  = np.array([p["x"]     for p in points])
    z  = np.array([-p["z"]    for p in points])   # flip Z → north up
    sp = np.array([p["speed"] for p in points])

    fig, ax = plt.subplots(figsize=(10, 6.5), facecolor="#111111")
    ax.set_facecolor("#111111")
    ax.set_aspect("equal")
    ax.axis("off")

    pts  = np.stack([x, z], axis=1)
    segs = np.stack([pts[:-1], pts[1:]], axis=1)

    # Gray base
    lc_base = LineCollection(segs, linewidths=14, colors="#2a2a2a",
                              capstyle="round", joinstyle="round")
    ax.add_collection(lc_base)

    # Speed-coloured layer
    norm = plt.Normalize(sp.min(), sp.max())
    lc   = LineCollection(segs, cmap="RdYlGn", norm=norm, linewidths=7,
                          capstyle="round", joinstyle="round")
    lc.set_array(sp[:-1])
    ax.add_collection(lc)

    ax.autoscale()
    ax.margins(0.05)

    cbar = fig.colorbar(lc, ax=ax, orientation="vertical", fraction=0.025, pad=0.01)
    cbar.set_label("km/h", color="#888", fontsize=8)
    cbar.ax.tick_params(labelsize=7, colors="#666666")
    cbar.outline.set_edgecolor("#2a2a2a")

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor="#111111")
    plt.close(fig)
    buf.seek(0)
    return buf


def gear_map_chart(points: list[dict[str, Any]]) -> BytesIO:
    """Track layout coloured by gear."""
    plt = _plt()
    from matplotlib.collections import LineCollection
    from matplotlib.colors import ListedColormap, BoundaryNorm
    import matplotlib.patches as mpatches

    GEAR_COLORS = [
        "#444444",  # 0 neutral
        "#1144dd",  # 1
        "#0099ff",  # 2
        "#00ccaa",  # 3
        "#00cc44",  # 4
        "#cccc00",  # 5
        "#ff8800",  # 6
        "#ff2200",  # 7
        "#ff00aa",  # 8
    ]

    x = np.array([p["x"]    for p in points])
    z = np.array([-p["z"]   for p in points])
    g = np.array([p["gear"] for p in points], dtype=float)

    fig, ax = plt.subplots(figsize=(10, 6.5), facecolor="#111111")
    ax.set_facecolor("#111111")
    ax.set_aspect("equal")
    ax.axis("off")

    pts  = np.stack([x, z], axis=1)
    segs = np.stack([pts[:-1], pts[1:]], axis=1)

    lc_base = LineCollection(segs, linewidths=14, colors="#2a2a2a",
                              capstyle="round", joinstyle="round")
    ax.add_collection(lc_base)

    max_g = max(int(g.max()), 7)
    cmap  = ListedColormap(GEAR_COLORS[: max_g + 1])
    bounds = np.arange(-0.5, max_g + 1.5, 1)
    norm  = BoundaryNorm(bounds, cmap.N)

    lc = LineCollection(segs, cmap=cmap, norm=norm, linewidths=7,
                        capstyle="round", joinstyle="round")
    lc.set_array(g[:-1])
    ax.add_collection(lc)

    ax.autoscale()
    ax.margins(0.05)

    used = sorted({int(gi) for gi in g if gi > 0})
    patches = [
        mpatches.Patch(color=GEAR_COLORS[min(gi, 8)], label=f"{gi}ª")
        for gi in used
    ]
    legend = ax.legend(
        handles=patches, loc="lower right", fontsize=7,
        facecolor="#1a1a1a", edgecolor="#2a2a2a", labelcolor="#cccccc",
        title="Marcha", title_fontsize=7,
    )
    legend.get_title().set_color("#888888")

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor="#111111")
    plt.close(fig)
    buf.seek(0)
    return buf

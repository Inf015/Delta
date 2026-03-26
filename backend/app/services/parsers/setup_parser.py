"""
Parser de archivos .ini de setup de Assetto Corsa.
Convierte el formato [SECTION] / VALUE=x en un dict estructurado.
"""
from __future__ import annotations

import configparser
from pathlib import Path


def parse_setup(path: str | Path) -> dict | None:
    """
    Parsea un archivo .ini de setup de AC.
    Retorna dict estructurado o None si el archivo no es válido.
    """
    cfg = configparser.ConfigParser(strict=False)
    try:
        cfg.read(str(path), encoding="utf-8")
    except Exception:
        return None

    if not cfg.sections():
        return None

    def val(section: str) -> float | None:
        try:
            return float(cfg[section]["value"])
        except (KeyError, ValueError):
            return None

    def corner(prefix: str) -> dict:
        return {
            k: v for k, v in {
                "LF": val(f"{prefix}_LF"),
                "RF": val(f"{prefix}_RF"),
                "LR": val(f"{prefix}_LR"),
                "RR": val(f"{prefix}_RR"),
            }.items() if v is not None
        }

    setup: dict = {}

    # ── Coche ─────────────────────────────────────────────────────────────────
    try:
        setup["car"] = cfg["CAR"]["model"]
    except KeyError:
        pass

    # ── Suspensión ────────────────────────────────────────────────────────────
    susp: dict = {}
    spring = corner("SPRING_RATE")
    if spring:
        susp["spring_rate_nm"] = spring
    bump = corner("DAMP_BUMP")
    if bump:
        susp["damper_bump"] = bump
    fast_bump = corner("DAMP_FAST_BUMP")
    if fast_bump:
        susp["damper_fast_bump"] = fast_bump
    rebound = corner("DAMP_REBOUND")
    if rebound:
        susp["damper_rebound"] = rebound
    fast_rebound = corner("DAMP_FAST_REBOUND")
    if fast_rebound:
        susp["damper_fast_rebound"] = fast_rebound
    camber = corner("CAMBER")
    if camber:
        susp["camber_deg"] = camber
    toe = corner("TOE_OUT")
    if toe:
        susp["toe_out"] = toe
    rod = corner("ROD_LENGTH")
    if rod:
        susp["rod_length_mm"] = rod
    packer = corner("PACKER_RANGE")
    if packer:
        susp["packer_range_mm"] = packer
    bumpstop = corner("BUMPSTOP")
    if bumpstop:
        susp["bumpstop"] = bumpstop

    arb_f = val("ARB_FRONT")
    arb_r = val("ARB_REAR")
    if arb_f is not None or arb_r is not None:
        susp["arb"] = {k: v for k, v in {"front": arb_f, "rear": arb_r}.items() if v is not None}

    if susp:
        setup["suspension"] = susp

    # ── Neumáticos ────────────────────────────────────────────────────────────
    tyres: dict = {}
    pressure = corner("PRESSURE")
    if pressure:
        tyres["pressure_psi"] = pressure
    compound = val("TYRES")
    if compound is not None:
        tyres["compound"] = round(compound)
    if tyres:
        setup["tyres"] = tyres

    # ── Frenos ────────────────────────────────────────────────────────────────
    front_bias = val("FRONT_BIAS")
    if front_bias is not None:
        setup["brakes"] = {"front_bias_pct": round(front_bias, 1)}

    # ── Diferencial ───────────────────────────────────────────────────────────
    diff: dict = {k: v for k, v in {
        "power": val("DIFF_POWER"),
        "coast": val("DIFF_COAST"),
        "preload": val("DIFF_PRELOAD"),
    }.items() if v is not None}
    if diff:
        setup["diff"] = diff

    # ── Aerodinámica ──────────────────────────────────────────────────────────
    aero: dict = {}
    for key in cfg.sections():
        if key.startswith("WING_"):
            v = val(key)
            if v is not None:
                aero[key.lower()] = int(v)
    if aero:
        setup["aero"] = aero

    # ── Electrónica ───────────────────────────────────────────────────────────
    electronics: dict = {k: v for k, v in {
        "abs": val("ABS"),
        "tc": val("TRACTION_CONTROL"),
    }.items() if v is not None}
    if electronics:
        setup["electronics"] = {k: int(v) for k, v in electronics.items()}

    # ── Combustible y transmisión ─────────────────────────────────────────────
    fuel = val("FUEL")
    if fuel is not None:
        setup["fuel_l"] = int(fuel)
    final_ratio = val("FINAL_RATIO")
    if final_ratio is not None:
        setup["final_ratio"] = final_ratio

    return setup if setup else None

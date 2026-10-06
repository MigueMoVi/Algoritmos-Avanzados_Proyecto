"""Conversión entre horas 'HH:MM' y minutos desde las 00:00."""

from __future__ import annotations


def hhmm_to_min(text: str) -> float:
    """'06:15' -> 375.0"""
    h, m = str(text).strip().split(":")
    return int(h) * 60 + float(m)


def min_to_hhmm(minutes: float) -> str:
    """375.0 -> '06:15' (redondeo al minuto más cercano)."""
    total = int(round(minutes))
    return f"{total // 60:02d}:{total % 60:02d}"


def min_to_hhmm_s(minutes: float) -> str:
    """Con décimas de minuto, útil para el ejemplo manual: 502.7 -> '08:22.7'."""
    h = int(minutes // 60)
    m = minutes - 60 * h
    return f"{h:02d}:{m:04.1f}"

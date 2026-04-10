"""Decisión del siguiente grupo en verde (Fase 2)."""

from __future__ import annotations

from typing import Mapping


def siguiente_grupo_es_ns(
    estado: Mapping[str, float | bool | int],
    *,
    peso_cola: float = 1.0,
    peso_espera: float = 0.08,
    umbral_empate: float = 0.75,
) -> bool:
    cn = float(estado.get("cola_ns", 0) or 0)
    ce = float(estado.get("cola_ew", 0) or 0)
    en = float(estado.get("espera_promedio_ns", 0) or 0)
    ee = float(estado.get("espera_promedio_ew", 0) or 0)
    sn = peso_cola * cn + peso_espera * en
    se = peso_cola * ce + peso_espera * ee
    if abs(sn - se) < umbral_empate:
        ult = estado.get("ultimo_verde_fue_ns")
        if isinstance(ult, bool):
            return not ult
        return False
    return sn >= se

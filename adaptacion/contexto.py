"""
Clasificación heurística del contexto de tráfico para seleccionar cromosoma del banco.
"""

from __future__ import annotations

from typing import Mapping


def clasificar_contexto_trafico(estado: Mapping[str, float | int]) -> str:
    """
    Devuelve una etiqueta en {"bajo", "pico", "desbalanceado", "mixto"}
    según densidad, colas por eje y desequilibrio.
    """
    dens = float(estado.get("densidad_vehicular", 0.0) or 0.0)
    cola_ns = float(estado.get("cola_ns", 0) or 0)
    cola_ew = float(estado.get("cola_ew", 0) or 0)
    long_max = max(cola_ns, cola_ew, 1e-6)
    desbalance = abs(cola_ns - cola_ew) / long_max

    if dens < 0.22 and long_max < 2.5:
        return "bajo"
    if desbalance > 0.55 and long_max >= 1.5:
        return "desbalanceado"
    if dens > 0.45 or long_max >= 5.0:
        return "pico"
    return "mixto"

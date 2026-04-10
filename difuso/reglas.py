"""
Reglas difusas del tipo Mamdani.

Se mantiene un conjunto reducido (9 reglas) para claridad pedagógica; el controlador
pondera consecuentes y defuzzifica el tiempo de verde deseado.
"""

from __future__ import annotations

from typing import List, Tuple

# Cada regla: ((t_densidad, t_espera, t_cola), t_verde)
# t_* en {0: bajo, 1: medio, 2: alto} índices a funciones de membresía
REGLAS_BASE: List[Tuple[Tuple[int, int, int], int]] = [
    ((0, 0, 0), 0),  # tráfico muy fluido -> verde corto
    ((0, 0, 1), 1),
    ((0, 1, 0), 1),
    ((1, 0, 0), 0),
    ((1, 1, 0), 1),
    ((1, 1, 1), 2),  # congestión fuerte -> verde largo
    ((2, 2, 2), 2),
    ((2, 1, 1), 2),
    ((0, 2, 2), 2),  # mucha espera/cola aunque densidad baja -> verde largo
]


def etiqueta_termino(indice: int) -> str:
    return ("bajo", "medio", "alto")[indice]


def describir_reglas_texto() -> str:
    """Resumen legible para README o defensa."""
    lineas = []
    for ant, cons in REGLAS_BASE:
        d, e, c = map(etiqueta_termino, ant)
        v = ("corto", "medio", "largo")[cons]
        lineas.append(f"Si densidad={d}, espera={e}, cola={c} -> verde {v}")
    return "\n".join(lineas)

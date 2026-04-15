
from __future__ import annotations

from typing import List, Tuple


def _consecuencia_regla(i_d: int, i_e: int, i_c: int) -> int:
    if i_c == 2 and i_e >= 1:
        return 2
    if i_e == 2 and i_d >= 1:
        return 2
    severidad = 0.22 * i_d + 0.38 * i_e + 0.40 * i_c
    if severidad >= 1.22:
        return 2
    if severidad <= 0.38:
        return 0
    return 1


REGLAS_BASE: List[Tuple[Tuple[int, int, int], int]] = [
    ((i_d, i_e, i_c), _consecuencia_regla(i_d, i_e, i_c))
    for i_d in range(3)
    for i_e in range(3)
    for i_c in range(3)
]


def etiqueta_termino(indice: int) -> str:
    return ("bajo", "medio", "alto")[indice]


def describir_reglas_texto() -> str:
    lineas = []
    for ant, cons in REGLAS_BASE:
        d, e, c = map(etiqueta_termino, ant)
        v = ("corto", "medio", "largo")[cons]
        lineas.append(f"Si densidad={d}, espera={e}, cola={c} -> verde {v}")
    return "\n".join(lineas)

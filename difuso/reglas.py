

from __future__ import annotations

from typing import List, Tuple
    
REGLAS_BASE: List[Tuple[Tuple[int, int, int], int]] = [
    ((0, 0, 0), 0),
    ((0, 0, 1), 1),
    ((0, 1, 0), 1),
    ((1, 0, 0), 0),
    ((1, 1, 0), 1),
    ((1, 1, 1), 2),
    ((2, 2, 2), 2),
    ((2, 1, 1), 2),
    ((0, 2, 2), 2),
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

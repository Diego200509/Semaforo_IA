from __future__ import annotations

from random import Random

import config
from simulacion.vehiculo import DireccionMovimiento, Maniobra

NUM_CARRILES_POR_DIRECCION: int = 2

SEPARACION_LATERAL_CARRIL: float = float(getattr(config, "SEPARACION_CARRILES_MISMO_SENTIDO", 18.0))

CARRIL_PRINCIPAL_RECTO: int = 0
CARRIL_SECUNDARIO_GIRO: int = 1


def carril_para_maniobra(maniobra: Maniobra) -> int:
    return CARRIL_PRINCIPAL_RECTO if maniobra == Maniobra.RECTO else CARRIL_SECUNDARIO_GIRO


def _delta_recto_vs_giro(carril: int) -> float:
    c = max(0, min(NUM_CARRILES_POR_DIRECCION - 1, int(carril)))
    step = float(getattr(config, "SEPARACION_CARRILES_MISMO_SENTIDO", SEPARACION_LATERAL_CARRIL))
    return (0.5 - c) * step


def offset_spawn_lateral(direccion: DireccionMovimiento, carril: int) -> tuple[float, float]:
    mid = float(getattr(config, "OFFSET_CENTRO_GRUPO_CARRIL", 28.0))
    d = _delta_recto_vs_giro(carril)
    if direccion == DireccionMovimiento.HACIA_SUR:
        return mid + d, 0.0
    if direccion == DireccionMovimiento.HACIA_NORTE:
        return -(mid + d), 0.0
    if direccion == DireccionMovimiento.HACIA_ESTE:
        return 0.0, mid + d
    return 0.0, -(mid + d)


def elegir_carril_aleatorio(rng: Random, n: int = NUM_CARRILES_POR_DIRECCION) -> int:
    return int(rng.randint(0, max(0, n - 1)))

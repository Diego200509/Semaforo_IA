"""
Varios carriles por aproximación (Fase 2).

Por cada sentido hay dos carriles lógicos (recto y giro), ambos en la **misma mitad**
de la vía respecto al eje central, para no mezclar trayectorias con el sentido opuesto.

Carril 0: recto (carril exterior, más alejado del eje central).
Carril 1: giro (carril interior, más cercano al eje central).
"""

from __future__ import annotations

from random import Random

import config
from simulacion.vehiculo import DireccionMovimiento, Maniobra

NUM_CARRILES_POR_DIRECCION: int = 2

# Compatibilidad: separación entre recto y giro en el mismo sentido.
SEPARACION_LATERAL_CARRIL: float = float(getattr(config, "SEPARACION_CARRILES_MISMO_SENTIDO", 18.0))

# Índices semánticos (compatibles con offset_spawn_lateral 0 / 1).
CARRIL_PRINCIPAL_RECTO: int = 0
CARRIL_SECUNDARIO_GIRO: int = 1


def carril_para_maniobra(maniobra: Maniobra) -> int:
    """Recto → carril principal; cualquier giro → carril secundario."""
    return CARRIL_PRINCIPAL_RECTO if maniobra == Maniobra.RECTO else CARRIL_SECUNDARIO_GIRO


def _delta_recto_vs_giro(carril: int) -> float:
    """Recto (0) más exterior; giro (1) más interior, respecto al eje central."""
    c = max(0, min(NUM_CARRILES_POR_DIRECCION - 1, int(carril)))
    step = float(getattr(config, "SEPARACION_CARRILES_MISMO_SENTIDO", SEPARACION_LATERAL_CARRIL))
    return (0.5 - c) * step


def offset_spawn_lateral(direccion: DireccionMovimiento, carril: int) -> tuple[float, float]:
    """Desplazamiento (dx, dy) desde el centro del cruce al eje del carril.

    Cada sentido ocupa solo su mitad de la calle (circulación a la derecha); recto y giro
    comparten esa mitad con distinto alejamiento del centro, sin cruzar el eje hacia el otro sentido.
    """
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
    """Solo para pruebas o escenarios legacy; el spawn normal usa `carril_para_maniobra`."""
    return int(rng.randint(0, max(0, n - 1)))

"""Tipos de vehículo (Fase 2): velocidad, tamaño y peso en congestión."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict


class TipoVehiculo(Enum):
    MOTO = auto()
    AUTO = auto()
    BUS = auto()
    CAMION = auto()


@dataclass(frozen=True)
class EspecificacionTipoVehiculo:
    factor_velocidad: float
    radio_px: int
    factor_peso: float
    factor_despeje: float


_TABLA: Dict[TipoVehiculo, EspecificacionTipoVehiculo] = {
    TipoVehiculo.MOTO: EspecificacionTipoVehiculo(1.12, 6, 0.35, 0.75),
    TipoVehiculo.AUTO: EspecificacionTipoVehiculo(1.0, 9, 1.0, 1.0),
    TipoVehiculo.BUS: EspecificacionTipoVehiculo(0.72, 12, 2.2, 1.45),
    TipoVehiculo.CAMION: EspecificacionTipoVehiculo(0.62, 11, 2.5, 1.55),
}


def especificacion(tipo: TipoVehiculo) -> EspecificacionTipoVehiculo:
    return _TABLA[tipo]

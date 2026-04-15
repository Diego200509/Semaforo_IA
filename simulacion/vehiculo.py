from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

import config
from simulacion.tipos_trafico import TipoVehiculo, especificacion


class DireccionMovimiento(Enum):

    HACIA_SUR = auto()
    HACIA_NORTE = auto()
    HACIA_ESTE = auto()
    HACIA_OESTE = auto()


class Maniobra(Enum):
    RECTO = auto()
    IZQUIERDA = auto()
    DERECHA = auto()


def direccion_salida_cruce(entrada: DireccionMovimiento, maniobra: Maniobra) -> DireccionMovimiento:
    if maniobra == Maniobra.RECTO:
        return entrada
    if entrada == DireccionMovimiento.HACIA_SUR:
        return DireccionMovimiento.HACIA_ESTE if maniobra == Maniobra.IZQUIERDA else DireccionMovimiento.HACIA_OESTE
    if entrada == DireccionMovimiento.HACIA_NORTE:
        return DireccionMovimiento.HACIA_OESTE if maniobra == Maniobra.IZQUIERDA else DireccionMovimiento.HACIA_ESTE
    if entrada == DireccionMovimiento.HACIA_ESTE:
        return DireccionMovimiento.HACIA_SUR if maniobra == Maniobra.IZQUIERDA else DireccionMovimiento.HACIA_NORTE
    return DireccionMovimiento.HACIA_NORTE if maniobra == Maniobra.IZQUIERDA else DireccionMovimiento.HACIA_SUR


@dataclass
class Vehiculo:
    identificador: int
    x: float
    y: float
    direccion: DireccionMovimiento
    tipo: TipoVehiculo = TipoVehiculo.AUTO
    maniobra: Maniobra = Maniobra.RECTO
    carril: int = 0
    direccion_movimiento: DireccionMovimiento | None = None
    velocidad: float = 0.0
    tiempo_espera: float = 0.0
    cruzo: bool = False
    detenido: bool = field(default=False)
    ingreso_cruce_autorizado: bool = False

    def actualizar_espera(self, dt: float, umbral_velocidad: float = 8.0) -> None:
        if self.velocidad < umbral_velocidad:
            self.tiempo_espera += dt

    def radio_dibujo(self) -> int:
        return int(especificacion(self.tipo).radio_px)

    def velocidad_libre_objetivo(self, velocidad_base: float) -> float:
        return float(velocidad_base) * float(especificacion(self.tipo).factor_velocidad)

    def factor_despeje(self) -> float:
        return float(especificacion(self.tipo).factor_despeje)

    def peso_congestion_efectivo(self) -> float:
        e = especificacion(self.tipo)
        return float(e.factor_peso) * float(e.factor_despeje)

    def separacion_respecto(self, otro: "Vehiculo") -> float:
        ra = float(especificacion(self.tipo).radio_px)
        rb = float(especificacion(otro.tipo).radio_px)
        extra = float(getattr(config, "GAP_VISUAL_ENTRE_VEHICULOS", 0.0))
        base_px = float(getattr(config, "SEPARACION_BASE_CENTROS_PX", 4.0))
        base = base_px + ra + rb + extra
        fd = max(self.factor_despeje(), otro.factor_despeje())
        return base * (0.82 + 0.12 * fd)

"""
Control de fases del sem?foro NS/EW con modo adaptativo (Fase 2).
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Optional

import config


class FaseSemaforo(Enum):
    VERDE_NS = auto()
    AMARILLO_NS = auto()
    VERDE_EW = auto()
    AMARILLO_EW = auto()


class Semaforo:
    def __init__(self) -> None:
        self.fase = FaseSemaforo.VERDE_NS
        self.tiempo_en_fase: float = 0.0
        self.duracion_verde_actual: float = float(config.VERDE_FIJO_NS)
        self.duracion_verde_ns: float = float(config.VERDE_FIJO_NS)
        self.duracion_verde_ew: float = float(config.VERDE_FIJO_EW)
        self._modo_tiempo_fijo: bool = True
        self._fase_adaptativa: bool = False
        self._siguiente_verde_ns: bool | None = None
        self.ultimo_verde_fue_ns: bool = True

    def configurar_modo(self, tiempo_fijo: bool) -> None:
        self._modo_tiempo_fijo = tiempo_fijo

    def configurar_fase_adaptativa(self, activo: bool) -> None:
        self._fase_adaptativa = bool(activo)

    def programar_siguiente_verde_ns(self, es_ns: bool) -> None:
        self._siguiente_verde_ns = bool(es_ns)

    @property
    def modo_tiempo_fijo(self) -> bool:
        return self._modo_tiempo_fijo

    @property
    def fase_adaptativa_activa(self) -> bool:
        return self._fase_adaptativa and not self._modo_tiempo_fijo

    def aplicar_tiempo_verde(self, segundos: float, para_fase: Optional[FaseSemaforo] = None) -> None:
        s = max(float(config.VERDE_MIN), min(float(config.VERDE_MAX), float(segundos)))
        if para_fase is None:
            if self.fase == FaseSemaforo.VERDE_NS:
                self.duracion_verde_ns = s
            elif self.fase == FaseSemaforo.VERDE_EW:
                self.duracion_verde_ew = s
            else:
                if self.fase == FaseSemaforo.AMARILLO_NS:
                    self.duracion_verde_ew = s
                else:
                    self.duracion_verde_ns = s
        else:
            if para_fase in (FaseSemaforo.VERDE_NS, FaseSemaforo.AMARILLO_NS):
                self.duracion_verde_ns = s
            else:
                self.duracion_verde_ew = s

    def verde_ns(self) -> bool:
        return self.fase == FaseSemaforo.VERDE_NS

    def verde_ew(self) -> bool:
        return self.fase == FaseSemaforo.VERDE_EW

    def puede_avanzar_ns(self) -> bool:
        return self.verde_ns()

    def puede_avanzar_ew(self) -> bool:
        return self.verde_ew()

    def actualizar(self, dt: float) -> None:
        self.tiempo_en_fase += dt

        if self.fase == FaseSemaforo.VERDE_NS:
            limite = self.duracion_verde_ns if not self._modo_tiempo_fijo else float(config.VERDE_FIJO_NS)
            if self.tiempo_en_fase >= limite:
                self._cambiar_a(FaseSemaforo.AMARILLO_NS)

        elif self.fase == FaseSemaforo.AMARILLO_NS:
            if self.tiempo_en_fase >= config.DURACION_AMARILLO:
                if self.fase_adaptativa_activa and self._siguiente_verde_ns is not None:
                    if self._siguiente_verde_ns:
                        self._cambiar_a(FaseSemaforo.VERDE_NS)
                        self.duracion_verde_actual = (
                            self.duracion_verde_ns if not self._modo_tiempo_fijo else float(config.VERDE_FIJO_NS)
                        )
                    else:
                        self._cambiar_a(FaseSemaforo.VERDE_EW)
                        self.duracion_verde_actual = (
                            self.duracion_verde_ew if not self._modo_tiempo_fijo else float(config.VERDE_FIJO_EW)
                        )
                    self._siguiente_verde_ns = None
                else:
                    self._cambiar_a(FaseSemaforo.VERDE_EW)
                    self.duracion_verde_actual = (
                        self.duracion_verde_ew if not self._modo_tiempo_fijo else float(config.VERDE_FIJO_EW)
                    )

        elif self.fase == FaseSemaforo.VERDE_EW:
            limite = self.duracion_verde_ew if not self._modo_tiempo_fijo else float(config.VERDE_FIJO_EW)
            if self.tiempo_en_fase >= limite:
                self._cambiar_a(FaseSemaforo.AMARILLO_EW)

        elif self.fase == FaseSemaforo.AMARILLO_EW:
            if self.tiempo_en_fase >= config.DURACION_AMARILLO:
                if self.fase_adaptativa_activa and self._siguiente_verde_ns is not None:
                    if self._siguiente_verde_ns:
                        self._cambiar_a(FaseSemaforo.VERDE_NS)
                        self.duracion_verde_actual = (
                            self.duracion_verde_ns if not self._modo_tiempo_fijo else float(config.VERDE_FIJO_NS)
                        )
                    else:
                        self._cambiar_a(FaseSemaforo.VERDE_EW)
                        self.duracion_verde_actual = (
                            self.duracion_verde_ew if not self._modo_tiempo_fijo else float(config.VERDE_FIJO_EW)
                        )
                    self._siguiente_verde_ns = None
                else:
                    self._cambiar_a(FaseSemaforo.VERDE_NS)
                    self.duracion_verde_actual = (
                        self.duracion_verde_ns if not self._modo_tiempo_fijo else float(config.VERDE_FIJO_NS)
                    )

    def _cambiar_a(self, nueva: FaseSemaforo) -> None:
        if self.fase == FaseSemaforo.VERDE_NS and nueva == FaseSemaforo.AMARILLO_NS:
            self.ultimo_verde_fue_ns = True
        elif self.fase == FaseSemaforo.VERDE_EW and nueva == FaseSemaforo.AMARILLO_EW:
            self.ultimo_verde_fue_ns = False
        self.fase = nueva
        self.tiempo_en_fase = 0.0

    def fase_para_grupo_ns(self) -> str:
        if self.verde_ns():
            return "VERDE"
        if self.fase == FaseSemaforo.AMARILLO_NS:
            return "AMARILLO"
        return "ROJO"

    def fase_para_grupo_ew(self) -> str:
        if self.verde_ew():
            return "VERDE"
        if self.fase == FaseSemaforo.AMARILLO_EW:
            return "AMARILLO"
        return "ROJO"

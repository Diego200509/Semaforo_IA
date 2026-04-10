"""
Callback del motor que actualiza parámetros difusos según el banco de cromosomas (Fase 2).
"""

from __future__ import annotations

from typing import Callable, Optional

from adaptacion.banco import BancoCromosomas
from adaptacion.contexto import clasificar_contexto_trafico
from difuso.controlador import ControladorDifuso
from difuso.variables import ParametrosMembresia


def crear_callback_difuso_contextual(
    banco: Optional[BancoCromosomas],
    parametros_base: ParametrosMembresia,
) -> Callable[[dict], float]:
    """
    En cada nuevo verde, clasifica el tráfico y aplica el cromosoma del banco si existe.
    """
    control = ControladorDifuso(parametros_base)

    def callback(estado: dict) -> float:
        if banco is not None and banco.por_contexto:
            etiqueta = clasificar_contexto_trafico(estado)
            crom = banco.cromosoma(etiqueta) or banco.cromosoma("mixto")
            if crom is not None:
                control.actualizar_parametros(crom.decodificar())
        return control.inferir_tiempo_verde(estado)

    return callback

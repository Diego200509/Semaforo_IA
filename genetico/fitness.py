"""
Evaluación de individuos: simula con el motor programático y agrega métricas.

La función compuesta penaliza espera y cola y premia vehículos atendidos; el GA maximiza
el valor retornado (`fitness`).

Fase 2: evaluación multi-escenario con promedio ponderado.
"""

from __future__ import annotations

import hashlib
from typing import Tuple

import config
from difuso.controlador import ControladorDifuso
from genetico.cromosoma import Cromosoma
from simulacion.entorno import MotorSimulacionProgramatico


def _normalizar_metricas(metricas: dict) -> tuple[float, float, float]:
    """Lleva magnitudes a escala comparable ~[0, 1]."""
    espera = float(metricas.get("tiempo_espera_promedio_muestras", 0.0))
    cola = float(metricas.get("longitud_cola_promedio_muestras", 0.0))
    atendidos = float(metricas.get("vehiculos_atendidos", 0.0))

    esp_n = min(1.0, espera / max(1e-6, config.ESPERA_MAX_UNIVERSO))
    cola_n = min(1.0, cola / max(1e-6, config.COLA_MAX_UNIVERSO))
    t_sim = max(1e-6, float(metricas.get("tiempo_simulado", 1.0)))
    ritmo = atendidos / t_sim
    atend_n = min(1.0, ritmo / 1.2)
    return esp_n, cola_n, atend_n


def coste_desde_metricas(metricas: dict) -> float:
    """Menor es mejor."""
    esp_n, cola_n, atend_n = _normalizar_metricas(metricas)
    return (
        config.PESO_TIEMPO_ESPERA * esp_n
        + config.PESO_LONGITUD_COLA * cola_n
        - config.PESO_VEHICULOS_ATENDIDOS * atend_n
    )


def fitness_desde_metricas(metricas: dict) -> float:
    """Mayor es mejor (maximización en el GA)."""
    return -coste_desde_metricas(metricas)


def _semilla_escenario(semilla_base: int, etiqueta_escenario: str) -> int:
    h = int(hashlib.md5(etiqueta_escenario.encode("utf-8")).hexdigest()[:8], 16)
    return (semilla_base + h) % (2**31 - 1)


def _simular_un_escenario(
    cromosoma: Cromosoma,
    semilla: int,
    escenario: str,
    duracion: float,
    dt: float,
) -> Tuple[float, dict]:
    control = ControladorDifuso(cromosoma.decodificar())
    motor = MotorSimulacionProgramatico(
        semilla=semilla,
        modo_tiempo_fijo=False,
        callback_tiempo_verde=control,
        escenario=escenario,
        duracion_planeada=duracion,
        fase_adaptativa=True,
    )
    motor.reiniciar(semilla=semilla)

    tiempo = 0.0
    while tiempo < duracion:
        motor.actualizar(dt)
        tiempo += dt

    metricas = motor.obtener_metricas()
    return fitness_desde_metricas(metricas), metricas


def evaluar_cromosoma(
    cromosoma: Cromosoma,
    semilla: int,
    duracion: float | None = None,
    dt: float | None = None,
    escenario: str | None = None,
    multi_escenario: bool | None = None,
) -> tuple[float, dict]:
    """
    Ejecuta simulación(es) con el controlador parametrizado por `cromosoma`.

    Si `multi_escenario` es True (o por defecto `config.USA_ENTRENAMIENTO_MULTI_ESCENARIO`)
    y no se pasa `escenario`, el fitness es el promedio ponderado sobre
    `ESCENARIOS_ENTRENAMIENTO_GA`.

    Retorna (fitness, métricas de la última corrida o de la última del bloque multi).
    """
    duracion = duracion if duracion is not None else config.DURACION_EVALUACION_FITNESS
    dt = dt if dt is not None else config.DT_SIMULACION_RAPIDA

    usar_multi = multi_escenario
    if usar_multi is None:
        usar_multi = bool(config.USA_ENTRENAMIENTO_MULTI_ESCENARIO)

    if usar_multi and escenario is None:
        escenarios = tuple(config.ESCENARIOS_ENTRENAMIENTO_GA)
        pesos = tuple(config.PESOS_ENTRENAMIENTO_MULTI_ESCENARIO)
        if len(pesos) != len(escenarios):
            pesos = tuple(1.0 / len(escenarios) for _ in escenarios)
        acc = 0.0
        wsum = 0.0
        ultimo_m: dict = {}
        for i, esc in enumerate(escenarios):
            w = float(pesos[i])
            semi = _semilla_escenario(semilla, esc)
            fit, ultimo_m = _simular_un_escenario(cromosoma, semi, esc, duracion, dt)
            acc += fit * w
            wsum += w
        return acc / max(wsum, 1e-9), ultimo_m

    esc = escenario if escenario is not None else config.ESCENARIO_ENTRENAMIENTO_GA
    return _simular_un_escenario(cromosoma, semilla, esc, duracion, dt)

from __future__ import annotations

import hashlib
from typing import Tuple

import config
from difuso.controlador import ControladorDifuso
from genetico.cromosoma import Cromosoma
from simulacion.entorno import MotorSimulacionProgramatico


def _normalizar_metricas(metricas: dict) -> dict[str, float]:
    espera = float(metricas.get("tiempo_espera_promedio_muestras", 0.0))
    cola = float(metricas.get("longitud_cola_promedio_muestras", 0.0))
    espera_max = float(metricas.get("tiempo_espera_maximo", 0.0))
    cola_max = float(metricas.get("longitud_cola_maxima", 0.0))
    demora_promedio = float(metricas.get("demora_promedio_por_vehiculo", 0.0))
    atendidos = float(metricas.get("vehiculos_atendidos", 0.0))

    esp_n = min(1.0, espera / max(1e-6, config.ESPERA_MAX_UNIVERSO))
    cola_n = min(1.0, cola / max(1e-6, config.COLA_MAX_UNIVERSO))
    espera_max_n = min(1.0, espera_max / max(1e-6, config.ESPERA_MAX_UNIVERSO))
    cola_max_n = min(1.0, cola_max / max(1e-6, config.COLA_MAX_UNIVERSO))
    demora_promedio_n = min(1.0, demora_promedio / max(1e-6, config.ESPERA_MAX_UNIVERSO))
    t_sim = max(1e-6, float(metricas.get("tiempo_simulado", 1.0)))
    ritmo = atendidos / t_sim
    atend_n = min(1.0, ritmo / 1.2)
    return {
        "espera_promedio": esp_n,
        "cola_promedio": cola_n,
        "espera_maxima": espera_max_n,
        "cola_maxima": cola_max_n,
        "demora_promedio_por_vehiculo": demora_promedio_n,
        "throughput": atend_n,
    }


def coste_desde_metricas(metricas: dict) -> float:
    normalizadas = _normalizar_metricas(metricas)
    return (
        config.PESO_TIEMPO_ESPERA * normalizadas["espera_promedio"]
        + config.PESO_LONGITUD_COLA * normalizadas["cola_promedio"]
        + config.PESO_TIEMPO_ESPERA_MAXIMA * normalizadas["espera_maxima"]
        + config.PESO_COLA_MAXIMA * normalizadas["cola_maxima"]
        + config.PESO_DEMORA_PROMEDIO_POR_VEHICULO * normalizadas["demora_promedio_por_vehiculo"]
        - config.PESO_VEHICULOS_ATENDIDOS * normalizadas["throughput"]
    )


def fitness_desde_metricas(metricas: dict) -> float:
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
    perfil_entrenamiento: str | None = None,
) -> Tuple[float, dict]:
    control = ControladorDifuso(cromosoma.decodificar())
    motor = MotorSimulacionProgramatico(
        semilla=semilla,
        modo_tiempo_fijo=False,
        callback_tiempo_verde=control,
        escenario=escenario,
        duracion_planeada=duracion,
        fase_adaptativa=True,
        perfil_entrenamiento=perfil_entrenamiento,
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
    perfil_entrenamiento: str | None = None,
) -> tuple[float, dict]:
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
            fit, ultimo_m = _simular_un_escenario(
                cromosoma,
                semi,
                esc,
                duracion,
                dt,
                perfil_entrenamiento=perfil_entrenamiento,
            )
            acc += fit * w
            wsum += w
        return acc / max(wsum, 1e-9), ultimo_m

    esc = escenario if escenario is not None else config.ESCENARIO_ENTRENAMIENTO_GA
    return _simular_un_escenario(
        cromosoma,
        semilla,
        esc,
        duracion,
        dt,
        perfil_entrenamiento=perfil_entrenamiento,
    )

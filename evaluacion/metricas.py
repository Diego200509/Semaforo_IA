"""
Utilidades para interpretar las métricas agregadas que expone el motor de simulación.

Mantiene el cálculo de fitness en `genetico.fitness`; aquí solo formateo y derivados.
"""

from __future__ import annotations

from typing import Mapping

import config


def triple_metricas_presentacion(metricas: Mapping[str, float]) -> tuple[float, float, int]:
    """
    Extrae las tres magnitudes usadas en informes de comparación GA:
    espera promedio (muestras), cola promedio (muestras), vehículos atendidos.
    """
    esp = float(metricas.get("tiempo_espera_promedio_muestras", 0.0))
    cola = float(metricas.get("longitud_cola_promedio_muestras", 0.0))
    at = int(round(float(metricas.get("vehiculos_atendidos", 0.0))))
    return esp, cola, at


def resumen_legible(metricas: Mapping[str, float]) -> str:
    """Texto compacto para consola o informes."""
    esp = float(metricas.get("tiempo_espera_promedio_muestras", 0.0))
    cola = float(metricas.get("longitud_cola_promedio_muestras", 0.0))
    at = int(round(float(metricas.get("vehiculos_atendidos", 0.0))))
    t = float(metricas.get("tiempo_simulado", 0.0))
    mx = float(metricas.get("tiempo_espera_maximo", 0.0))
    det = float(metricas.get("vehiculos_detenidos_promedio_muestras", 0.0))
    thr = throughput(metricas)
    return (
        f"Espera prom. (muestras): {esp:.2f} s | Cola prom.: {cola:.2f} veh. | "
        f"Atendidos: {at} | Tiempo sim.: {t:.1f} s | "
        f"Espera máx.: {mx:.2f} s | Detenidos prom.: {det:.2f} | Throughput: {thr:.3f} veh/s"
    )


def throughput(metricas: Mapping[str, float]) -> float:
    """Vehículos atendidos por unidad de tiempo (aprox. productividad del cruce)."""
    t = float(metricas.get("tiempo_simulado", 0.0))
    if t <= 1e-6:
        return 0.0
    return float(metricas.get("vehiculos_atendidos", 0.0)) / t


def referencias_normalizacion() -> dict:
    """Documenta escalas usadas en informes (útiles para defensa)."""
    return {
        "espera_max_referencia": config.ESPERA_MAX_UNIVERSO,
        "cola_max_referencia": config.COLA_MAX_UNIVERSO,
        "pesos_fitness": {
            "espera": config.PESO_TIEMPO_ESPERA,
            "cola": config.PESO_LONGITUD_COLA,
            "atendidos": config.PESO_VEHICULOS_ATENDIDOS,
        },
    }

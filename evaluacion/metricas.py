from __future__ import annotations

from typing import Mapping

import config


def triple_metricas_presentacion(metricas: Mapping[str, float]) -> tuple[float, float, int]:
    esp = float(metricas.get("tiempo_espera_promedio_muestras", 0.0))
    cola = float(metricas.get("longitud_cola_promedio_muestras", 0.0))
    at = int(round(float(metricas.get("vehiculos_atendidos", 0.0))))
    return esp, cola, at


def resumen_legible(metricas: Mapping[str, float]) -> str:
    esp = float(metricas.get("tiempo_espera_promedio_muestras", 0.0))
    cola = float(metricas.get("longitud_cola_promedio_muestras", 0.0))
    at = int(round(float(metricas.get("vehiculos_atendidos", 0.0))))
    t = float(metricas.get("tiempo_simulado", 0.0))
    mx = float(metricas.get("tiempo_espera_maximo", 0.0))
    cola_max = float(metricas.get("longitud_cola_maxima", 0.0))
    demora = float(metricas.get("demora_promedio_por_vehiculo", 0.0))
    det = float(metricas.get("vehiculos_detenidos_promedio_muestras", 0.0))
    deseq_esp = float(metricas.get("desequilibrio_espera_ejes", 0.0))
    deseq_cola = float(metricas.get("desequilibrio_cola_ejes", 0.0))
    thr = throughput(metricas)
    return (
        f"Espera prom. (muestras): {esp:.2f} s | Cola prom.: {cola:.2f} veh. | "
        f"Atendidos: {at} | Tiempo sim.: {t:.1f} s | "
        f"Espera max.: {mx:.2f} s | Cola max.: {cola_max:.2f} veh. | "
        f"Demora prom./veh.: {demora:.2f} s | Detenidos prom.: {det:.2f} | "
        f"Deseq. espera ejes: {deseq_esp:.2f} s | Deseq. cola ejes: {deseq_cola:.2f} | "
        f"Throughput: {thr:.3f} veh/s"
    )


def throughput(metricas: Mapping[str, float]) -> float:
    t = float(metricas.get("tiempo_simulado", 0.0))
    if t <= 1e-6:
        return 0.0
    return float(metricas.get("vehiculos_atendidos", 0.0)) / t


def referencias_normalizacion() -> dict:
    return {
        "espera_max_referencia": config.ESPERA_MAX_UNIVERSO,
        "cola_max_referencia": config.COLA_MAX_UNIVERSO,
        "pesos_fitness": {
            "espera": config.PESO_TIEMPO_ESPERA,
            "cola": config.PESO_LONGITUD_COLA,
            "espera_maxima": config.PESO_TIEMPO_ESPERA_MAXIMA,
            "cola_maxima": config.PESO_COLA_MAXIMA,
            "demora_promedio_por_vehiculo": config.PESO_DEMORA_PROMEDIO_POR_VEHICULO,
            "desequilibrio_espera_ejes": config.PESO_DESEQUILIBRIO_ESPERA_EJES,
            "desequilibrio_cola_ejes": config.PESO_DESEQUILIBRIO_COLA_EJES,
            "atendidos": config.PESO_VEHICULOS_ATENDIDOS,
        },
    }

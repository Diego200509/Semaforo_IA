"""Métricas, gráficas y comparación de estrategias de control."""

from evaluacion.comparacion import (
    ResultadoComparacionDifusoGA,
    ResultadoPromedioEstrategia,
    ejecutar_comparacion,
    ejecutar_comparacion_difuso_vs_ga,
    ejecutar_comparacion_promedios_multisemilla,
    metricas_promedio_por_escenario_y_estrategia,
    promediar_metricas,
)
from evaluacion.metricas import resumen_legible, triple_metricas_presentacion

__all__ = [
    "ResultadoComparacionDifusoGA",
    "ResultadoPromedioEstrategia",
    "ejecutar_comparacion",
    "ejecutar_comparacion_difuso_vs_ga",
    "ejecutar_comparacion_promedios_multisemilla",
    "metricas_promedio_por_escenario_y_estrategia",
    "promediar_metricas",
    "resumen_legible",
    "triple_metricas_presentacion",
]

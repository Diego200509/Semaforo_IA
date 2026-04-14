"""
Compara políticas de control con la misma duración y semilla(s).

- `ejecutar_comparacion_promedios_multisemilla`: modo `comparar` (3 estrategias × N semillas).
- `ejecutar_comparacion`: tres escenarios con una semilla (`comparar_completo`).
- `metricas_promedio_por_escenario_y_estrategia`: datos para gráfica por escenario de tráfico.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import config
from difuso.controlador import ControladorDifuso
from difuso.variables import parametros_por_defecto
from genetico.cromosoma import Cromosoma
from genetico.fitness import coste_desde_metricas
from simulacion.entorno import MotorSimulacionProgramatico
from simulacion.escenarios import NOMBRES_ESCENARIOS_VALIDOS


@dataclass
class ResultadoEscenario:
    nombre: str
    metricas: dict
    coste: float


@dataclass
class ResultadoComparacionDifusoGA:
    """Métricas finales de dos corridas: difuso sin entrenar vs difuso con cromosoma GA."""

    metricas_sin_ga: dict
    metricas_con_ga: Optional[dict]
    semilla: int
    duracion: float


@dataclass
class ResultadoPromedioEstrategia:
    """Promedio de métricas sobre varias semillas para una misma política."""

    nombre: str
    metricas_promedio: dict
    coste_promedio: float
    semillas: List[int]


def _ruta_cromosoma_entrenado(perfil_entrenamiento: str | None = None):
    return config.obtener_perfil_entrenamiento(perfil_entrenamiento).archivo_mejor_cromosoma


def promediar_metricas(metricas_list: List[dict]) -> dict:
    """Promedia claves numéricas; ignora `segmentos_mixto`."""
    if not metricas_list:
        return {}
    claves = set()
    for m in metricas_list:
        claves.update(m.keys())
    out: dict = {}
    for k in claves:
        if k == "segmentos_mixto":
            continue
        vals = []
        for m in metricas_list:
            if k not in m:
                continue
            try:
                vals.append(float(m[k]))
            except (TypeError, ValueError):
                continue
        if vals:
            out[k] = sum(vals) / len(vals)
    return out


def _simular_fijo(
    semilla: int,
    duracion: float,
    dt: float,
    escenario: str,
    duracion_planeada: float | None = None,
    perfil_entrenamiento: str | None = None,
) -> dict:
    dur_p = float(duracion_planeada if duracion_planeada is not None else duracion)
    motor = MotorSimulacionProgramatico(
        semilla=semilla,
        modo_tiempo_fijo=True,
        callback_tiempo_verde=None,
        escenario=escenario,
        duracion_planeada=dur_p,
        perfil_entrenamiento=perfil_entrenamiento,
    )
    motor.reiniciar(semilla=semilla)
    t = 0.0
    while t < duracion:
        motor.actualizar(dt)
        t += dt
    return motor.obtener_metricas()


def _simular_difuso(
    semilla: int,
    duracion: float,
    dt: float,
    control: ControladorDifuso,
    escenario: str,
    duracion_planeada: float | None = None,
    perfil_entrenamiento: str | None = None,
) -> dict:
    dur_p = float(duracion_planeada if duracion_planeada is not None else duracion)
    motor = MotorSimulacionProgramatico(
        semilla=semilla,
        modo_tiempo_fijo=False,
        callback_tiempo_verde=control,
        escenario=escenario,
        duracion_planeada=dur_p,
        fase_adaptativa=True,
        perfil_entrenamiento=perfil_entrenamiento,
    )
    motor.reiniciar(semilla=semilla)
    t = 0.0
    while t < duracion:
        motor.actualizar(dt)
        t += dt
    return motor.obtener_metricas()


def ejecutar_comparacion(
    semilla: int | None = None,
    duracion: float | None = None,
    dt: float | None = None,
    escenario: str | None = None,
    perfil_entrenamiento: str | None = None,
) -> List[ResultadoEscenario]:
    """
    Comparación resumida para `comparar_completo`.

    Si el llamador fuerza `semilla` o `escenario`, se conserva la corrida simple.
    Si no, se usa un resumen más robusto: promedio en varias semillas y escenarios.
    """
    duracion = duracion if duracion is not None else config.DURACION_ESCENARIO_COMPARACION
    dt = dt if dt is not None else config.DT_SIMULACION_RAPIDA
    corrida_simple = (semilla is not None) or (escenario is not None)
    semillas = [int(semilla)] if semilla is not None else list(config.SEEDS_COMPARACION_COMPLETA)
    escenarios = (
        [(escenario or config.ESCENARIO_COMPARAR_COMPLETO).strip().lower()]
        if corrida_simple
        else [str(e).strip().lower() for e in config.ESCENARIOS_COMPARACION_COMPLETA]
    )

    resultados: List[ResultadoEscenario] = []

    mats_fijo = [
        _simular_fijo(s, duracion, dt, esc, duracion, perfil_entrenamiento)
        for esc in escenarios
        for s in semillas
    ]
    resultados.append(
        ResultadoEscenario(
            "Tiempo fijo",
            promediar_metricas(mats_fijo),
            sum(coste_desde_metricas(m) for m in mats_fijo) / len(mats_fijo),
        )
    )

    mats_base = [
        _simular_difuso(
            s,
            duracion,
            dt,
            ControladorDifuso(parametros_por_defecto()),
            esc,
            duracion,
            perfil_entrenamiento,
        )
        for esc in escenarios
        for s in semillas
    ]
    resultados.append(
        ResultadoEscenario(
            "Difuso (base)",
            promediar_metricas(mats_base),
            sum(coste_desde_metricas(m) for m in mats_base) / len(mats_base),
        )
    )

    ruta_crom = _ruta_cromosoma_entrenado(perfil_entrenamiento)
    if ruta_crom.is_file():
        crom = Cromosoma.cargar_json(ruta_crom)
        mats_ga = [
            _simular_difuso(
                s,
                duracion,
                dt,
                ControladorDifuso(crom.decodificar()),
                esc,
                duracion,
                perfil_entrenamiento,
            )
            for esc in escenarios
            for s in semillas
        ]
        resultados.append(
            ResultadoEscenario(
                "Difuso + GA",
                promediar_metricas(mats_ga),
                sum(coste_desde_metricas(m) for m in mats_ga) / len(mats_ga),
            )
        )

    return resultados


def ejecutar_comparacion_promedios_multisemilla(
    semillas: List[int] | None = None,
    duracion: float | None = None,
    dt: float | None = None,
    escenario: str | None = None,
    perfil_entrenamiento: str | None = None,
) -> List[ResultadoPromedioEstrategia]:
    """
    Para cada estrategia (fijo, difuso base, difuso+GA) ejecuta una corrida por semilla
    y devuelve métricas y coste promediados.
    """
    semillas = list(semillas if semillas is not None else config.SEEDS_COMPARACION_MULTISEMILLA)
    duracion = float(duracion if duracion is not None else config.DURACION_COMPARAR_DIFUSO_GA)
    dt = float(dt if dt is not None else config.DT_SIMULACION_RAPIDA)
    esc = (escenario or config.ESCENARIO_POR_DEFECTO).strip().lower()

    salida: List[ResultadoPromedioEstrategia] = []

    mats_fijo: List[dict] = []
    for s in semillas:
        mats_fijo.append(_simular_fijo(s, duracion, dt, esc, duracion, perfil_entrenamiento))
    costes_f = [coste_desde_metricas(m) for m in mats_fijo]
    salida.append(
        ResultadoPromedioEstrategia(
            "Tiempo fijo",
            promediar_metricas(mats_fijo),
            sum(costes_f) / len(costes_f),
            semillas,
        )
    )

    mats_base: List[dict] = []
    ctrl_base = ControladorDifuso(parametros_por_defecto())
    for s in semillas:
        mats_base.append(_simular_difuso(s, duracion, dt, ctrl_base, esc, duracion, perfil_entrenamiento))
    costes_b = [coste_desde_metricas(m) for m in mats_base]
    salida.append(
        ResultadoPromedioEstrategia(
            "Difuso (base)",
            promediar_metricas(mats_base),
            sum(costes_b) / len(costes_b),
            semillas,
        )
    )

    ruta_crom = _ruta_cromosoma_entrenado(perfil_entrenamiento)
    if ruta_crom.is_file():
        crom = Cromosoma.cargar_json(ruta_crom)
        ctrl_opt = ControladorDifuso(crom.decodificar())
        mats_ga: List[dict] = []
        for s in semillas:
            mats_ga.append(_simular_difuso(s, duracion, dt, ctrl_opt, esc, duracion, perfil_entrenamiento))
        costes_g = [coste_desde_metricas(m) for m in mats_ga]
        salida.append(
            ResultadoPromedioEstrategia(
                "Difuso + GA",
                promediar_metricas(mats_ga),
                sum(costes_g) / len(costes_g),
                semillas,
            )
        )

    return salida


def metricas_promedio_por_escenario_y_estrategia(
    semillas: List[int] | None = None,
    duracion: float | None = None,
    dt: float | None = None,
    perfil_entrenamiento: str | None = None,
) -> Dict[str, Dict[str, dict]]:
    """
    Para cada escenario de tráfico y cada estrategia, métricas promediadas en `semillas`.
    Claves de primer nivel: bajo, pico, desbalanceado, mixto.
    Segundo nivel: Tiempo fijo, Difuso (base), Difuso + GA (si hay JSON).
    """
    semillas = list(semillas if semillas is not None else config.SEEDS_COMPARACION_MULTISEMILLA)
    duracion = float(duracion if duracion is not None else config.DURACION_COMPARAR_DIFUSO_GA)
    dt = float(dt if dt is not None else config.DT_SIMULACION_RAPIDA)

    escenarios = [e for e in NOMBRES_ESCENARIOS_VALIDOS]
    out: Dict[str, Dict[str, dict]] = {}
    ruta_crom = _ruta_cromosoma_entrenado(perfil_entrenamiento)

    for esc in escenarios:
        out[esc] = {}
        mats_fijo = [_simular_fijo(s, duracion, dt, esc, duracion, perfil_entrenamiento) for s in semillas]
        out[esc]["Tiempo fijo"] = promediar_metricas(mats_fijo)

        ctrl_base = ControladorDifuso(parametros_por_defecto())
        mats_b = [
            _simular_difuso(s, duracion, dt, ctrl_base, esc, duracion, perfil_entrenamiento)
            for s in semillas
        ]
        out[esc]["Difuso (base)"] = promediar_metricas(mats_b)

        if ruta_crom.is_file():
            crom = Cromosoma.cargar_json(ruta_crom)
            ctrl_opt = ControladorDifuso(crom.decodificar())
            mats_g = [
                _simular_difuso(s, duracion, dt, ctrl_opt, esc, duracion, perfil_entrenamiento)
                for s in semillas
            ]
            out[esc]["Difuso + GA"] = promediar_metricas(mats_g)

    return out


def ejecutar_comparacion_difuso_vs_ga(
    semilla: int | None = None,
    duracion: float | None = None,
    dt: float | None = None,
    escenario: str | None = None,
    perfil_entrenamiento: str | None = None,
) -> ResultadoComparacionDifusoGA:
    """Dos corridas con la misma semilla (difuso base vs GA)."""
    semilla = semilla if semilla is not None else config.SEED_COMPARACION
    duracion = duracion if duracion is not None else config.DURACION_COMPARAR_DIFUSO_GA
    dt = dt if dt is not None else config.DT_SIMULACION_RAPIDA
    esc = (escenario or config.ESCENARIO_POR_DEFECTO).strip().lower()

    ctrl_base = ControladorDifuso(parametros_por_defecto())
    m_sin = _simular_difuso(semilla, duracion, dt, ctrl_base, esc, duracion)

    m_con: Optional[dict] = None
    ruta_crom = _ruta_cromosoma_entrenado(perfil_entrenamiento)
    if ruta_crom.is_file():
        crom = Cromosoma.cargar_json(ruta_crom)
        ctrl_opt = ControladorDifuso(crom.decodificar())
        m_con = _simular_difuso(semilla, duracion, dt, ctrl_opt, esc, duracion)

    return ResultadoComparacionDifusoGA(
        metricas_sin_ga=m_sin,
        metricas_con_ga=m_con,
        semilla=semilla,
        duracion=duracion,
    )

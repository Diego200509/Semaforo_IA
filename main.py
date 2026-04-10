"""
Punto de entrada: coordina simulación, control difuso, algoritmo genético y evaluación.

El flujo respeta la interfaz `MotorSimulacion` para que el núcleo inteligente no dependa
de Pygame ni de un motor externo concreto.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Literal, Optional

import config
from adaptacion.banco import cargar_banco
from adaptacion.callback_difuso import crear_callback_difuso_contextual
from difuso.controlador import ControladorDifuso
from difuso.variables import parametros_por_defecto
from evaluacion.comparacion import ejecutar_comparacion, ejecutar_comparacion_promedios_multisemilla
from evaluacion.metricas import resumen_legible
from genetico.cromosoma import Cromosoma
from genetico.ga import ejecutar_entrenamiento_banco, ejecutar_ga
from simulacion.entorno import MotorSimulacionPygame, MotorSimulacionProgramatico
from simulacion.escenarios import NOMBRES_ESCENARIOS_VALIDOS

MensajeParametros = Literal["ga", "default", "banco"]
CallbackVerde = Callable[[dict], float]


def _resolver_callback_difuso(
    parser: argparse.ArgumentParser,
    *,
    usar_default: bool,
    usar_ga: bool,
    mejor_cromosoma_legacy: bool,
    adaptacion_banco: bool,
    ruta_banco: Path | None,
) -> tuple[Optional[CallbackVerde], MensajeParametros]:
    ruta = config.ARCHIVO_MEJOR_CROMOSOMA
    existe = ruta.is_file()
    base = parametros_por_defecto()

    if adaptacion_banco:
        rb = ruta_banco or config.ARCHIVO_BANCO_CROMOSOMAS
        if not rb.is_file():
            parser.error(
                f"No se encontró el banco de cromosomas en {rb}. "
                "Genera uno con: python main.py --modo entrenar_banco"
            )
        banco = cargar_banco(rb)
        return crear_callback_difuso_contextual(banco, base), "banco"

    if usar_default:
        return ControladorDifuso(base), "default"

    if usar_ga or mejor_cromosoma_legacy:
        if not existe:
            parser.error(
                f"No se encontró {ruta.name}: entrena antes con "
                "`python main.py --modo entrenar` o quita --usar-ga / --mejor-cromosoma."
            )
        crom = Cromosoma.cargar_json(ruta)
        return ControladorDifuso(crom.decodificar()), "ga"

    if existe:
        crom = Cromosoma.cargar_json(ruta)
        return ControladorDifuso(crom.decodificar()), "ga"
    return ControladorDifuso(base), "default"


def _imprimir_aviso_parametros(msg: MensajeParametros) -> None:
    if msg == "ga":
        print("Usando parámetros optimizados del GA (un solo cromosoma)")
    elif msg == "banco":
        print("Usando banco de cromosomas con adaptación contextual (Fase 2)")
    else:
        print("Usando parámetros por defecto")


def _duracion_planeada_visual(escenario: str) -> float:
    if escenario == "mixto":
        return float(config.DURACION_PLAN_VISUAL_MIXTO)
    return float(config.DURACION_REFERENCIA_MIXTO)


def modo_simulacion_visual(
    parser: argparse.ArgumentParser,
    usar_default: bool,
    usar_ga: bool,
    mejor_cromosoma_legacy: bool,
    tiempo_fijo: bool,
    escenario: str,
    verbose_escenario: bool,
    adaptacion_banco: bool,
    ruta_banco: Path | None,
    fase_adaptativa: bool,
) -> None:
    if tiempo_fijo:
        control = None
    else:
        control, msg = _resolver_callback_difuso(
            parser,
            usar_default=usar_default,
            usar_ga=usar_ga,
            mejor_cromosoma_legacy=mejor_cromosoma_legacy,
            adaptacion_banco=adaptacion_banco,
            ruta_banco=ruta_banco,
        )
        _imprimir_aviso_parametros(msg)

    print(f"Escenario de tráfico: {escenario}")

    motor = MotorSimulacionPygame(
        semilla=config.SEMILLA_ALEATORIA,
        modo_tiempo_fijo=tiempo_fijo,
        callback_tiempo_verde=control,
        escenario=escenario,
        duracion_planeada=_duracion_planeada_visual(escenario),
        verbose_escenario=verbose_escenario,
        fase_adaptativa=fase_adaptativa,
    )
    motor.reiniciar(semilla=config.SEMILLA_ALEATORIA)
    print("Ventana gráfica: cierra la ventana o pulsa ESC para salir.")
    if tiempo_fijo:
        print("Modo: tiempos fijos (sin difuso).")
    else:
        print("Modo: control difuso activo.")
        if fase_adaptativa:
            print("Fase semafórica: adaptativa (prioridad por colas / esperas).")
        else:
            print("Fase semafórica: ciclo fijo NS ↔ EW.")
    motor.ejecutar_bucle_visual(max_segundos=None)


def modo_simulacion_programatica(
    parser: argparse.ArgumentParser,
    segundos: float,
    usar_default: bool,
    usar_ga: bool,
    mejor_cromosoma_legacy: bool,
    tiempo_fijo: bool,
    escenario: str,
    verbose_escenario: bool,
    adaptacion_banco: bool,
    ruta_banco: Path | None,
    fase_adaptativa: bool,
) -> None:
    if tiempo_fijo:
        control = None
    else:
        control, msg = _resolver_callback_difuso(
            parser,
            usar_default=usar_default,
            usar_ga=usar_ga,
            mejor_cromosoma_legacy=mejor_cromosoma_legacy,
            adaptacion_banco=adaptacion_banco,
            ruta_banco=ruta_banco,
        )
        _imprimir_aviso_parametros(msg)

    print(f"Escenario de tráfico: {escenario}")

    motor = MotorSimulacionProgramatico(
        semilla=config.SEMILLA_ALEATORIA,
        modo_tiempo_fijo=tiempo_fijo,
        callback_tiempo_verde=control,
        escenario=escenario,
        duracion_planeada=segundos,
        verbose_escenario=verbose_escenario,
        fase_adaptativa=fase_adaptativa,
    )
    motor.reiniciar(semilla=config.SEMILLA_ALEATORIA)
    t = 0.0
    dt = 1.0 / config.FPS
    while t < segundos:
        motor.actualizar(dt)
        t += dt
    m = motor.obtener_metricas()
    print(resumen_legible(m))
    if escenario == "mixto" and m.get("segmentos_mixto"):
        print("\n--- Resumen por tramo (mixto) ---")
        for seg in m["segmentos_mixto"]:
            print(
                f"  {seg['nombre']}: {seg['t_inicio']:.1f}–{seg['t_fin']:.1f} s | "
                f"espera prom. {seg['espera_promedio_muestras']:.2f} s | "
                f"atendidos {seg['vehiculos_atendidos']}"
            )


def modo_entrenar() -> None:
    from evaluacion.graficas import graficar_evolucion_fitness

    print("Entrenando GA (puede tardar varios minutos)...")
    if config.USA_ENTRENAMIENTO_MULTI_ESCENARIO:
        print(f"Fitness: promedio ponderado sobre escenarios {config.ESCENARIOS_ENTRENAMIENTO_GA}")
    else:
        print(f"Escenario de tráfico en fitness: {config.ESCENARIO_ENTRENAMIENTO_GA}")
    mejor, historial = ejecutar_ga(semilla_base=config.SEMILLA_ALEATORIA)
    mejor.guardar_json(config.ARCHIVO_MEJOR_CROMOSOMA)
    print(f"Mejor cromosoma guardado en: {config.ARCHIVO_MEJOR_CROMOSOMA}")
    graficar_evolucion_fitness(historial, mostrar=False)
    print(f"Gráfica de evolución: {config.ARCHIVO_GRAFICA_EVOLUCION_FITNESS}")


def modo_entrenar_banco() -> None:
    print("Entrenando banco de cromosomas (4 GA secuenciales; puede tardar mucho)...")
    ejecutar_entrenamiento_banco(semilla_base=config.SEMILLA_ALEATORIA)
    print(f"Banco guardado en: {config.ARCHIVO_BANCO_CROMOSOMAS}")


def modo_comparar(duracion: float, escenario: str) -> None:
    """Promedios multisemilla (3 estrategias) + gráfica por escenario de tráfico."""
    from evaluacion.comparacion import metricas_promedio_por_escenario_y_estrategia
    from evaluacion.graficas import (
        graficar_comparacion_por_escenario,
        graficar_estrategias_promedio_multimetrica,
    )

    if not config.ARCHIVO_MEJOR_CROMOSOMA.is_file():
        print(
            "Aviso: no hay mejor_cromosoma.json; la comparación solo incluirá "
            "'Tiempo fijo' y 'Difuso (base)'."
        )

    print()
    print("===== COMPARACIÓN (promedio en semillas) =====")
    print(f"Semillas: {config.SEEDS_COMPARACION_MULTISEMILLA}")
    print(f"Duración por corrida: {duracion:.1f} s")
    print(f"Escenario de tráfico (bloque principal): {escenario}")
    print()

    resultados = ejecutar_comparacion_promedios_multisemilla(
        duracion=duracion,
        escenario=escenario,
    )
    for r in resultados:
        print(f"=== {r.nombre} (promedio, n={len(r.semillas)}) ===")
        print(resumen_legible(r.metricas_promedio))
        print(f"Coste promedio: {r.coste_promedio:.4f} (menor es mejor)\n")

    graficar_estrategias_promedio_multimetrica(resultados, mostrar=False)
    print(f"Gráfica estrategias (promedios): {config.ARCHIVO_GRAFICA_ESTRATEGIAS_PROMEDIO}")

    print("Calculando matriz escenario × estrategia (puede tardar un poco)...")
    matriz = metricas_promedio_por_escenario_y_estrategia(duracion=duracion)
    graficar_comparacion_por_escenario(matriz, mostrar=False)
    print(f"Gráfica por escenario: {config.ARCHIVO_GRAFICA_POR_ESCENARIO}")


def modo_comparar_completo() -> None:
    from evaluacion.graficas import graficar_barras_comparacion

    if not config.ARCHIVO_MEJOR_CROMOSOMA.is_file():
        print(
            "Aviso: no existe archivo de cromosoma optimizado; la comparación será solo "
            "'fijo' vs 'difuso base'. Ejecuta antes: python main.py --modo entrenar"
        )
    print(f"Escenario tráfico: {config.ESCENARIO_COMPARAR_COMPLETO} | Semilla: {config.SEED_COMPARACION}")
    resultados = ejecutar_comparacion()
    for r in resultados:
        print(f"\n=== {r.nombre} ===")
        print(resumen_legible(r.metricas))
        print(f"Coste compuesto: {r.coste:.4f} (menor es mejor)")
    graficar_barras_comparacion(
        [r.nombre for r in resultados],
        [r.coste for r in resultados],
        mostrar=False,
    )
    print(f"\nGráfica de barras guardada en: {config.ARCHIVO_GRAFICA_COMPARACION_COSTES}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sistema inteligente de semáforos (difuso + GA + simulación desacoplada)."
    )
    parser.add_argument(
        "--modo",
        choices=[
            "sim_visual",
            "sim_prog",
            "entrenar",
            "entrenar_banco",
            "comparar",
            "comparar_completo",
        ],
        default="sim_visual",
        help=(
            "sim_visual / sim_prog: simulación; entrenar: GA (multi-escenario si config); "
            "entrenar_banco: Fase 2, un cromosoma por contexto; "
            "comparar / comparar_completo: evaluación."
        ),
    )
    parser.add_argument(
        "--escenario",
        choices=list(NOMBRES_ESCENARIOS_VALIDOS),
        default=config.ESCENARIO_POR_DEFECTO,
        help="Perfil de generación de tráfico: bajo | pico | desbalanceado | mixto.",
    )
    parser.add_argument(
        "--verbose-escenario",
        action="store_true",
        help="En mixto, imprime en consola cada cambio de tramo de tráfico (también en visual).",
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--usar-default",
        action="store_true",
        help="Fuerza parámetros difusos por defecto (ignora mejor_cromosoma.json).",
    )
    grupo.add_argument(
        "--usar-ga",
        action="store_true",
        help="Fuerza carga de mejor_cromosoma.json (error si no existe).",
    )
    grupo.add_argument(
        "--mejor-cromosoma",
        action="store_true",
        help="(Compatibilidad) Equivalente a --usar-ga.",
    )
    parser.add_argument(
        "--tiempo-fijo",
        action="store_true",
        help="Desactiva el difuso y usa tiempos fijos de config (línea base).",
    )
    parser.add_argument(
        "--adaptacion-banco",
        action="store_true",
        help="Fase 2: usa banco_cromosomas.json y elige cromosoma según contexto de tráfico.",
    )
    parser.add_argument(
        "--banco-cromosomas",
        type=Path,
        default=None,
        help="Ruta al JSON del banco (por defecto: banco_cromosomas.json en la raíz del proyecto).",
    )
    parser.add_argument(
        "--no-fase-adaptativa",
        action="store_true",
        help="Fase 2: ciclo NS↔EW fijo en lugar de prioridad por colas.",
    )
    parser.add_argument(
        "--segundos",
        type=float,
        default=None,
        help=(
            "Duración en segundos: en sim_prog el valor por defecto es 90; "
            f"en comparar es {config.DURACION_COMPARAR_DIFUSO_GA:.0f}."
        ),
    )
    args = parser.parse_args(argv)

    seg_prog = args.segundos if args.segundos is not None else 90.0
    seg_comparar = args.segundos if args.segundos is not None else config.DURACION_COMPARAR_DIFUSO_GA

    esc = args.escenario.strip().lower()
    verbose_mix = args.verbose_escenario or (esc == "mixto")

    if args.tiempo_fijo and args.adaptacion_banco:
        parser.error("--adaptacion-banco no es compatible con --tiempo-fijo.")

    fase_adaptativa = (not args.no_fase_adaptativa) and (not args.tiempo_fijo)

    if args.modo == "sim_visual":
        modo_simulacion_visual(
            parser,
            usar_default=args.usar_default,
            usar_ga=args.usar_ga,
            mejor_cromosoma_legacy=args.mejor_cromosoma,
            tiempo_fijo=args.tiempo_fijo,
            escenario=esc,
            verbose_escenario=verbose_mix,
            adaptacion_banco=args.adaptacion_banco,
            ruta_banco=args.banco_cromosomas,
            fase_adaptativa=fase_adaptativa,
        )
    elif args.modo == "sim_prog":
        modo_simulacion_programatica(
            parser,
            seg_prog,
            usar_default=args.usar_default,
            usar_ga=args.usar_ga,
            mejor_cromosoma_legacy=args.mejor_cromosoma,
            tiempo_fijo=args.tiempo_fijo,
            escenario=esc,
            verbose_escenario=verbose_mix,
            adaptacion_banco=args.adaptacion_banco,
            ruta_banco=args.banco_cromosomas,
            fase_adaptativa=fase_adaptativa,
        )
    elif args.modo == "entrenar":
        modo_entrenar()
    elif args.modo == "entrenar_banco":
        modo_entrenar_banco()
    elif args.modo == "comparar":
        modo_comparar(seg_comparar, esc)
    elif args.modo == "comparar_completo":
        modo_comparar_completo()
    else:
        parser.error("Modo no reconocido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

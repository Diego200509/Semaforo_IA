
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import config

from evaluacion.metricas import triple_metricas_presentacion


def _preparar_ruta_salida(ruta: Path) -> Path:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    return ruta


def _pyplot():
    import matplotlib.pyplot as plt

    return plt


def graficar_evolucion_fitness(
    historial: Sequence[float],
    ruta_salida: Path | None = None,
    mostrar: bool = False,
) -> None:
    plt = _pyplot()
    ruta_salida = _preparar_ruta_salida(ruta_salida or config.ARCHIVO_GRAFICA_EVOLUCION_FITNESS)
    plt.figure(figsize=(8, 4))
    plt.plot(range(1, len(historial) + 1), list(historial), marker="o", linewidth=1.5)
    plt.xlabel("Generación")
    plt.ylabel("Mejor fitness")
    plt.title("Evolución del mejor individuo (GA)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=150)
    if mostrar:
        plt.show()
    plt.close()


def graficar_barras_comparacion(
    etiquetas: Sequence[str],
    costes: Sequence[float],
    ruta_salida: Path | None = None,
    mostrar: bool = False,
) -> None:
    plt = _pyplot()
    colores = ["#5c7cfa", "#51cf66", "#ff922b", "#cc5de8"]
    ruta_salida = _preparar_ruta_salida(ruta_salida or config.ARCHIVO_GRAFICA_COMPARACION_COSTES)
    plt.figure(figsize=(8, 4))
    plt.bar(
        list(etiquetas),
        list(costes),
        color=colores[: len(etiquetas)],
    )
    plt.ylabel("Coste (menor es mejor)")
    plt.title("Comparación de estrategias de semáforo")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=150)
    if mostrar:
        plt.show()
    plt.close()


def graficar_comparacion_sin_ga_vs_ga(
    metricas_sin_ga: Mapping[str, float],
    metricas_con_ga: Optional[Mapping[str, float]],
    ruta_salida: Path | None = None,
    mostrar: bool = False,
) -> None:
    import numpy as np

    plt = _pyplot()
    ruta_salida = _preparar_ruta_salida(ruta_salida or config.ARCHIVO_GRAFICA_COMPARAR_GA)

    labels_x = ["Espera prom. (s)", "Cola prom. (veh.)", "Atendidos"]
    claves = (
        "tiempo_espera_promedio_muestras",
        "longitud_cola_promedio_muestras",
        "vehiculos_atendidos",
    )

    v_sin = [float(metricas_sin_ga.get(k, 0.0)) for k in claves]
    if metricas_con_ga is not None:
        v_con = [float(metricas_con_ga.get(k, 0.0)) for k in claves]
    else:
        v_con = None

    x = np.arange(len(labels_x))
    width = 0.35
    fig, ax = plt.subplots(figsize=(10, 5))

    color_sin = "#5c7cfa"
    color_con = "#51cf66"

    if v_con is not None:
        alturas_sin = []
        alturas_con = []
        for a, b in zip(v_sin, v_con):
            m = max(abs(a), abs(b), 1e-9)
            alturas_sin.append(100.0 * a / m)
            alturas_con.append(100.0 * b / m)

        bars_sin = ax.bar(x - width / 2, alturas_sin, width, label="Sin GA (difuso base)", color=color_sin)
        bars_con = ax.bar(x + width / 2, alturas_con, width, label="Con GA (optimizado)", color=color_con)

        def _etiquetar(barras, valores_reales: list[float]) -> None:
            for bar, val in zip(barras, valores_reales):
                h = bar.get_height()
                txt = f"{val:.2f}" if abs(val - int(val)) > 1e-3 else f"{int(val)}"
                ax.annotate(
                    txt,
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        _etiquetar(bars_sin, v_sin)
        _etiquetar(bars_con, v_con)
    else:
        m = max((abs(v) for v in v_sin), default=1e-9)
        alturas = [100.0 * v / m for v in v_sin]
        bars = ax.bar(x, alturas, width * 1.5, label="Sin GA (no hay mejor_cromosoma.json)", color=color_sin)
        for bar, val in zip(bars, v_sin):
            h = bar.get_height()
            txt = f"{val:.2f}" if abs(val - int(val)) > 1e-3 else f"{int(val)}"
            ax.annotate(
                txt,
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    ax.set_ylabel("Valor relativo dentro de cada métrica (%)")
    ax.set_title("Comparación difuso base vs parámetros optimizados por GA")
    ax.set_xticks(x)
    ax.set_xticklabels(labels_x)
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, 115)

    esp_s, cola_s, at_s = triple_metricas_presentacion(metricas_sin_ga)
    pie = f"Resumen numérico — Sin GA: Espera={esp_s:.2f}s | Cola={cola_s:.2f} | Atendidos={at_s}"
    if v_con is not None and metricas_con_ga is not None:
        esp_c, cola_c, at_c = triple_metricas_presentacion(metricas_con_ga)
        pie += f"  |  Con GA: Espera={esp_c:.2f}s | Cola={cola_c:.2f} | Atendidos={at_c}"
    fig.text(0.5, 0.02, pie, ha="center", fontsize=8, style="italic")

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)
    plt.savefig(ruta_salida, dpi=150)
    if mostrar:
        plt.show()
    plt.close()


def graficar_estrategias_promedio_multimetrica(
    resultados: Sequence[Any],
    ruta_salida: Path | None = None,
    mostrar: bool = False,
) -> None:
    import numpy as np

    plt = _pyplot()
    ruta_salida = _preparar_ruta_salida(ruta_salida or config.ARCHIVO_GRAFICA_ESTRATEGIAS_PROMEDIO)

    etiquetas_metricas = [
        ("tiempo_espera_promedio_muestras", "Espera prom. (s)"),
        ("longitud_cola_promedio_muestras", "Cola prom."),
        ("vehiculos_atendidos", "Atendidos"),
        ("tiempo_espera_maximo", "Espera máx. (s)"),
        ("vehiculos_detenidos_promedio_muestras", "Detenidos prom."),
        ("throughput", "Throughput (veh/s)"),
    ]

    nombres_est = [str(r.nombre) for r in resultados]
    x = np.arange(len(etiquetas_metricas))
    width = 0.22
    fig, ax = plt.subplots(figsize=(12, 5))
    colores = ["#5c7cfa", "#51cf66", "#ff922b", "#cc5de8"]

    for i, r in enumerate(resultados):
        m = r.metricas_promedio
        vals = [float(m.get(clave, 0.0)) for clave, _ in etiquetas_metricas]
        maxv = max(abs(v) for v in vals) or 1e-9
        norm = [100.0 * v / maxv for v in vals]
        offset = (i - (len(resultados) - 1) / 2) * width
        bars = ax.bar(x + offset, norm, width, label=nombres_est[i], color=colores[i % len(colores)])

        for bar, vreal in zip(bars, vals):
            h = bar.get_height()
            txt = f"{vreal:.2f}" if abs(vreal - int(vreal)) > 1e-2 else f"{int(vreal)}"
            ax.annotate(
                txt,
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 2),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
                rotation=90,
            )

    ax.set_ylabel("Valor relativo por métrica (%)")
    ax.set_title("Estrategias de control — métricas promedio (multisemilla)")
    ax.set_xticks(x)
    ax.set_xticklabels([lbl for _, lbl in etiquetas_metricas], rotation=15, ha="right")
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=150)
    if mostrar:
        plt.show()
    plt.close()


def graficar_comparacion_por_escenario(
    datos: Mapping[str, Mapping[str, Mapping[str, float]]],
    ruta_salida: Path | None = None,
    mostrar: bool = False,
) -> None:
    import numpy as np

    from genetico.fitness import coste_desde_metricas

    plt = _pyplot()
    ruta_salida = _preparar_ruta_salida(ruta_salida or config.ARCHIVO_GRAFICA_POR_ESCENARIO)

    escenarios = list(datos.keys())
    estrategias: list[str] = []
    for e in escenarios:
        estrategias.extend(datos[e].keys())
    estrategias = sorted(set(estrategias))

    x = np.arange(len(escenarios))
    width = 0.22
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    colores = ["#5c7cfa", "#51cf66", "#ff922b"]

    for i, est in enumerate(estrategias):
        esperanzas = []
        costes = []
        for esc in escenarios:
            m = datos[esc].get(est, {})
            esperanzas.append(float(m.get("tiempo_espera_promedio_muestras", 0.0)))
            costes.append(coste_desde_metricas(m) if m else 0.0)
        offset = (i - (len(estrategias) - 1) / 2) * width
        ax1.bar(x + offset, esperanzas, width, label=est, color=colores[i % len(colores)])
        ax2.bar(x + offset, costes, width, label=est, color=colores[i % len(colores)])

    ax1.set_ylabel("Espera prom. (s)")
    ax1.set_title("Métricas por escenario de tráfico (promedio en semillas)")
    ax1.legend(loc="upper right")
    ax1.grid(axis="y", alpha=0.3)

    ax2.set_ylabel("Coste (menor es mejor)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(escenarios)
    ax2.legend(loc="upper right")
    ax2.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=150)
    if mostrar:
        plt.show()
    plt.close()

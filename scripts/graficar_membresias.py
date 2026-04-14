"""
Genera graficas de funciones de membresia del sistema difuso.

Uso:
    python scripts/graficar_membresias.py

Salida:
    - graficas/membresias_base.png
    - graficas/membresias_final.png (si existe cromosoma_final.json)
"""

from __future__ import annotations

import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import matplotlib.pyplot as plt  # noqa: E402

import config  # noqa: E402
from difuso.variables import aplicar_trimf, construir_universos, parametros_por_defecto  # noqa: E402
from genetico.cromosoma import Cromosoma  # noqa: E402


def _graficar_parametros(parametros, titulo: str, ruta_salida: Path) -> None:
    u_d, u_e, u_c, u_v = construir_universos()
    figuras = [
        ("Densidad vehicular", u_d, parametros.densidad),
        ("Tiempo de espera", u_e, parametros.espera),
        ("Longitud de cola", u_c, parametros.cola),
        ("Tiempo de verde", u_v, parametros.verde),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    colores = ("#2b8a3e", "#f08c00", "#c92a2a")
    etiquetas = ("bajo", "medio", "alto")

    for ax, (nombre, universo, puntos) in zip(axes.flatten(), figuras):
        bajo, medio, alto = aplicar_trimf(universo, puntos)
        for mf, color, etiqueta in zip((bajo, medio, alto), colores, etiquetas):
            ax.plot(universo, mf, color=color, linewidth=2, label=etiqueta)
        ax.set_title(nombre)
        ax.set_xlabel("Valor normalizado")
        ax.set_ylabel("Pertenencia")
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.05)
        ax.grid(True, alpha=0.25)
        ax.legend(loc="upper right")

    fig.suptitle(titulo)
    fig.tight_layout()
    fig.subplots_adjust(top=0.90)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta_salida, dpi=150)
    plt.close(fig)


def main() -> int:
    config.CARPETA_GRAFICAS.mkdir(parents=True, exist_ok=True)

    ruta_base = config.CARPETA_GRAFICAS / "membresias_base.png"
    _graficar_parametros(
        parametros_por_defecto(),
        "Funciones de membresia - parametros base",
        ruta_base,
    )
    print(f"Grafica generada: {ruta_base}")

    perfil_final = config.obtener_perfil_entrenamiento("final")
    ruta_cromosoma = perfil_final.archivo_mejor_cromosoma
    if not ruta_cromosoma.is_file():
        print(
            "Aviso: no existe cromosoma_final.json. "
            "Solo se genero la grafica de membresias base."
        )
        return 0

    crom = Cromosoma.cargar_json(ruta_cromosoma)
    ruta_final = config.CARPETA_GRAFICAS / "membresias_final.png"
    _graficar_parametros(
        crom.decodificar(),
        "Funciones de membresia - perfil final entrenado",
        ruta_final,
    )
    print(f"Grafica generada: {ruta_final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

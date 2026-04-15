from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  
from difuso.controlador import ControladorDifuso  
from simulacion.entorno import MotorSimulacionProgramatico  
from simulacion.semaforo import FaseSemaforo  


def main() -> None:
    p = argparse.ArgumentParser(description="Muestra verdes NS vs EW y estado por eje.")
    p.add_argument("--escenario", default="desbalanceado", choices=("bajo", "pico", "desbalanceado", "mixto"))
    p.add_argument("--segundos", type=float, default=120.0)
    p.add_argument("--semilla", type=int, default=42)
    args = p.parse_args()

    ctrl = ControladorDifuso()
    motor = MotorSimulacionProgramatico(
        semilla=args.semilla,
        modo_tiempo_fijo=False,
        callback_tiempo_verde=ctrl,
        escenario=args.escenario,
        duracion_planeada=args.segundos,
        fase_adaptativa=True,
    )
    motor.reiniciar(semilla=args.semilla)

    dt = 1.0 / float(config.FPS)
    t = 0.0
    fase_prev: FaseSemaforo | None = None

    print(f"Escenario={args.escenario!r}, difuso=ON, tiempo fijo=OFF, dt={dt:.4f}s\n")

    while t < args.segundos:
        motor.actualizar(dt)
        sem = motor.interseccion.semaforo
        f = sem.fase

        if fase_prev is not None and f != fase_prev:
            if f in (FaseSemaforo.VERDE_NS, FaseSemaforo.VERDE_EW):
                st = motor.obtener_estado_trafico()
                grupo = "NS" if f == FaseSemaforo.VERDE_NS else "EW"
                dur = sem.duracion_verde_ns if f == FaseSemaforo.VERDE_NS else sem.duracion_verde_ew
                print(
                    f"t={t:6.1f}s  VERDE {grupo:2}  ->  {dur:4.1f}s   "
                    f"cola_ns={st['cola_ns']:.0f} cola_ew={st['cola_ew']:.0f}   "
                    f"espera_ns={st['espera_ns']:.1f}s espera_ew={st['espera_ew']:.1f}s"
                )

        fase_prev = f
        t += dt

    print("\nListo. Si NS y EW tienen cargas distintas, los segundos de verde deberían diferir.")


if __name__ == "__main__":
    main()

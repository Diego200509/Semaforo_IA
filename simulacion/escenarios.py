from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import config
from simulacion.vehiculo import DireccionMovimiento


def _pesos_equilibrados() -> Dict[DireccionMovimiento, float]:
    p = 1.0 / 4.0
    return {
        DireccionMovimiento.HACIA_SUR: p,
        DireccionMovimiento.HACIA_NORTE: p,
        DireccionMovimiento.HACIA_ESTE: p,
        DireccionMovimiento.HACIA_OESTE: p,
    }


def _pesos_ns_dominante() -> Dict[DireccionMovimiento, float]:
    return {
        DireccionMovimiento.HACIA_SUR: 0.38,
        DireccionMovimiento.HACIA_NORTE: 0.38,
        DireccionMovimiento.HACIA_ESTE: 0.12,
        DireccionMovimiento.HACIA_OESTE: 0.12,
    }


@dataclass(frozen=True)
class PerfilGeneracion:
    nombre: str
    factor_intervalo: float
    prob_intento: float
    pesos_direccion: Dict[DireccionMovimiento, float]

    def intervalo_spawn_efectivo(self) -> float:
        return max(0.35, float(config.INTERVALO_SPAWN_BASE) * self.factor_intervalo)


SEGMENTOS_MIXTO_REFERENCIA: List[Tuple[float, float, str]] = [
    (0.0, 40.0, "bajo"),
    (40.0, 80.0, "pico"),
    (80.0, 120.0, "desbalanceado"),
]

PERFILES: Dict[str, PerfilGeneracion] = {
    "bajo": PerfilGeneracion(
        nombre="bajo",
        factor_intervalo=1.35,
        prob_intento=0.88,
        pesos_direccion=_pesos_equilibrados(),
    ),
    "pico": PerfilGeneracion(
        nombre="pico",
        factor_intervalo=0.52,
        prob_intento=0.97,
        pesos_direccion=_pesos_equilibrados(),
    ),
    "desbalanceado": PerfilGeneracion(
        nombre="desbalanceado",
        factor_intervalo=0.95,
        prob_intento=0.93,
        pesos_direccion=_pesos_ns_dominante(),
    ),
}


def _normalizar_pesos(pesos: Dict[DireccionMovimiento, float]) -> Tuple[List[DireccionMovimiento], List[float]]:
    dirs = list(DireccionMovimiento)
    w = [max(0.0, float(pesos.get(d, 0.0))) for d in dirs]
    s = sum(w) or 1.0
    return dirs, [x / s for x in w]


class ControlGeneracionTrafico:

    def __init__(self, nombre_escenario: str, duracion_total: float) -> None:
        self.nombre_escenario = nombre_escenario
        self.duracion_total = max(1.0, float(duracion_total))
        self._es_mixto = nombre_escenario == "mixto"
        self._perfil_actual_nombre: str = ""
        self._segmentos_escalados: List[Tuple[float, float, str]] = []
        if self._es_mixto:
            ref = 120.0
            escala = self.duracion_total / ref
            self._segmentos_escalados = [
                (a * escala, b * escala, tag) for a, b, tag in SEGMENTOS_MIXTO_REFERENCIA
            ]
        else:
            if nombre_escenario not in PERFILES:
                raise ValueError(f"Escenario desconocido: {nombre_escenario}")
        self._inicializado = False

    def reiniciar(self) -> None:
        self._perfil_actual_nombre = ""
        self._inicializado = False

    def sincronizar(self, tiempo_simulado: float, callback_cambio) -> PerfilGeneracion:
        perfil = self._perfil_para_tiempo(tiempo_simulado)
        if not self._inicializado:
            self._inicializado = True
            self._perfil_actual_nombre = perfil.nombre
            if self._es_mixto:
                callback_cambio("", perfil.nombre, tiempo_simulado)
            return perfil
        if perfil.nombre != self._perfil_actual_nombre:
            anterior = self._perfil_actual_nombre
            self._perfil_actual_nombre = perfil.nombre
            callback_cambio(anterior, perfil.nombre, tiempo_simulado)
        return perfil

    def _perfil_para_tiempo(self, t: float) -> PerfilGeneracion:
        if not self._es_mixto:
            return PERFILES[self.nombre_escenario]
        t = min(max(0.0, t), self.duracion_total)
        n = len(self._segmentos_escalados)
        for i, (a, b, tag) in enumerate(self._segmentos_escalados):
            ultimo = i == n - 1
            if ultimo:
                if t >= a:
                    return PERFILES[tag]
            elif a <= t < b:
                return PERFILES[tag]
        return PERFILES[self._segmentos_escalados[-1][2]]


NOMBRES_ESCENARIOS_VALIDOS = ("bajo", "pico", "desbalanceado", "mixto")


def crear_control_generacion(nombre: str, duracion_total: float) -> ControlGeneracionTrafico:
    clave = nombre.strip().lower()
    if clave not in NOMBRES_ESCENARIOS_VALIDOS:
        raise ValueError(f"Escenario no válido: {nombre}. Use: {NOMBRES_ESCENARIOS_VALIDOS}")
    return ControlGeneracionTrafico(clave, duracion_total)

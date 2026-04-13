from __future__ import annotations

from typing import Dict, Mapping

import numpy as np

import config
from difuso.reglas import REGLAS_BASE
from difuso.variables import (
    ParametrosMembresia,
    aplicar_trimf,
    construir_universos,
    defuzz_centroide,
    interp_membresia,
    parametros_por_defecto,
)


class ControladorDifuso:

    def __init__(self, parametros: ParametrosMembresia | None = None) -> None:
        self.parametros = parametros or parametros_por_defecto()
        self._u_d, self._u_e, self._u_c, self._u_v = construir_universos()
        self._reconstruir_funciones()

    def _reconstruir_funciones(self) -> None:
        p = self.parametros
        self._mf_d = aplicar_trimf(self._u_d, p.densidad)
        self._mf_e = aplicar_trimf(self._u_e, p.espera)
        self._mf_c = aplicar_trimf(self._u_c, p.cola)
        self._mf_v = aplicar_trimf(self._u_v, p.verde)

    def actualizar_parametros(self, parametros: ParametrosMembresia) -> None:
        self.parametros = parametros
        self._reconstruir_funciones()

    def _normalizar_entradas(self, estado: Mapping[str, float]) -> tuple[float, float, float]:
        dens_raw = estado.get("densidad_ponderada", estado.get("densidad_vehicular", 0.0))
        dens = float(np.clip(float(dens_raw), 0.0, 1.0))
        eje = estado.get("inferir_para_grupo_ns", None)
        if eje is True:
            cola_preverde = estado.get("cola_ns_preverde", None)
            cola = float(cola_preverde if cola_preverde is not None else estado.get("cola_ns", 0.0))
            esp = float(estado.get("espera_ns", estado.get("tiempo_espera_promedio", 0.0)))
        elif eje is False:
            cola_preverde = estado.get("cola_ew_preverde", None)
            cola = float(cola_preverde if cola_preverde is not None else estado.get("cola_ew", 0.0))
            esp = float(estado.get("espera_ew", estado.get("tiempo_espera_promedio", 0.0)))
        else:
            esp = float(estado.get("tiempo_espera_promedio", 0.0))
            cola = float(estado.get("longitud_cola", 0.0))
        esp_n = float(np.clip(esp / max(1e-6, config.ESPERA_MAX_UNIVERSO), 0.0, 1.0))
        cola_n = float(np.clip(cola / max(1e-6, config.COLA_MAX_UNIVERSO), 0.0, 1.0))
        return dens, esp_n, cola_n

    def _grados_por_variable(
        self, valor: float, universo: np.ndarray, mf_triple: tuple[np.ndarray, np.ndarray, np.ndarray]
    ) -> np.ndarray:
        bajo, medio, alto = mf_triple
        return np.array(
            [
                interp_membresia(universo, bajo, valor),
                interp_membresia(universo, medio, valor),
                interp_membresia(universo, alto, valor),
            ]
        )

    def inferir_tiempo_verde(self, estado: Mapping[str, float]) -> float:
        d, e, c = self._normalizar_entradas(estado)
        g_d = self._grados_por_variable(d, self._u_d, self._mf_d)
        g_e = self._grados_por_variable(e, self._u_e, self._mf_e)
        g_c = self._grados_por_variable(c, self._u_c, self._mf_c)

        agregado = np.zeros_like(self._u_v)
        for (i_d, i_e, i_c), i_v in REGLAS_BASE:
            activacion = min(g_d[i_d], g_e[i_e], g_c[i_c])
            if activacion <= 0:
                continue
            cons = self._mf_v[i_v] * activacion
            agregado = np.maximum(agregado, cons)

        salida_norm = defuzz_centroide(self._u_v, agregado)
        salida_norm = float(np.clip(salida_norm, 0.0, 1.0))

        verde = config.VERDE_MIN + salida_norm * (config.VERDE_MAX - config.VERDE_MIN)
        return float(np.clip(verde, config.VERDE_MIN, config.VERDE_MAX))

    def __call__(self, estado: Dict) -> float:
        return self.inferir_tiempo_verde(estado)

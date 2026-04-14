from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import skfuzzy as fuzz


@dataclass
class ParametrosMembresia:

    densidad: Tuple[float, float, float, float, float]
    espera: Tuple[float, float, float, float, float]
    cola: Tuple[float, float, float, float, float]
    verde: Tuple[float, float, float, float, float]


def parametros_por_defecto() -> ParametrosMembresia:
    return ParametrosMembresia(
        densidad=(0.0, 0.08, 0.28, 0.52, 0.78),
        espera=(0.0, 0.1, 0.32, 0.55, 0.8),
        cola=(0.0, 0.1, 0.32, 0.55, 0.82),
        verde=(0.0, 0.12, 0.38, 0.68, 1.0),
    )


def construir_universos() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    paso = 0.01
    u = np.arange(0, 1.0001, paso)
    return u.copy(), u.copy(), u.copy(), u.copy()


def _vertices_trimf_seguros(a: float, b: float, c: float) -> list[float]:
    a, b, c = float(a), float(b), float(c)
    eps = 1e-5
    if c - a < eps:
        return [0.0, 0.5, 1.0]
    b = float(np.clip(b, a + eps, c - eps))
    return [a, b, c]


def trimf(universo: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    return fuzz.trimf(universo, _vertices_trimf_seguros(a, b, c))


def aplicar_trimf(
    universo: np.ndarray, puntos: Tuple[float, float, float, float, float]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    a, b, c, d, e = puntos
    # Extremos con "hombro" para no perder activación al saturar en 0 o 1.
    bajo = fuzz.trapmf(universo, [a, a, b, c])
    medio = trimf(universo, b, c, d)
    alto = fuzz.trapmf(universo, [c, d, e, e])
    return bajo, medio, alto


def interp_membresia(universo: np.ndarray, mf: np.ndarray, x: float) -> float:
    return float(fuzz.interp_membership(universo, mf, x))


def defuzz_centroide(universo: np.ndarray, agregado: np.ndarray) -> float:
    if float(np.max(agregado)) < 1e-9:
        # Fallback conservador: cercano al ciclo fijo de referencia y no a un verde excesivo.
        return 0.30
    return float(fuzz.defuzz(universo, agregado, "centroid"))

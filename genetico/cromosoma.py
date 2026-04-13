from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import numpy as np

from difuso.variables import ParametrosMembresia


def _ordenar_grupo(cinco: Sequence[float]) -> tuple[float, float, float, float, float]:
    vals = sorted(float(x) for x in cinco)
    return vals[0], vals[1], vals[2], vals[3], vals[4]


@dataclass
class Cromosoma:
    genes: List[float]

    @staticmethod
    def longitud_esperada() -> int:
        return 20

    def __post_init__(self) -> None:
        if len(self.genes) != self.longitud_esperada():
            raise ValueError(f"Se esperaban {self.longitud_esperada()} genes.")

    @classmethod
    def aleatorio(cls, rng: random.Random | None = None) -> "Cromosoma":
        r = rng or random.Random()
        genes = [r.random() for _ in range(cls.longitud_esperada())]
        return cls(genes)

    def decodificar(self) -> ParametrosMembresia:
        g = self.genes
        densidad = _ordenar_grupo(g[0:5])
        espera = _ordenar_grupo(g[5:10])
        cola = _ordenar_grupo(g[10:15])
        verde = _ordenar_grupo(g[15:20])
        return ParametrosMembresia(
            densidad=densidad,
            espera=espera,
            cola=cola,
            verde=verde,
        )

    def copia(self) -> "Cromosoma":
        return Cromosoma(list(self.genes))

    def mutar(self, prob: float, rng: random.Random, sigma: float = 0.08) -> None:
        for i in range(len(self.genes)):
            if rng.random() < prob:
                self.genes[i] = float(np.clip(self.genes[i] + rng.gauss(0, sigma), 0.0, 1.0))

    @staticmethod
    def cruce(padre_a: "Cromosoma", padre_b: "Cromosoma", rng: random.Random) -> tuple["Cromosoma", "Cromosoma"]:
        alpha = 0.35
        h1, h2 = [], []
        for a, b in zip(padre_a.genes, padre_b.genes):
            lo, hi = min(a, b), max(a, b)
            span = hi - lo
            c1 = rng.uniform(lo - alpha * span, hi + alpha * span)
            c2 = rng.uniform(lo - alpha * span, hi + alpha * span)
            h1.append(float(np.clip(c1, 0.0, 1.0)))
            h2.append(float(np.clip(c2, 0.0, 1.0)))
        return Cromosoma(h1), Cromosoma(h2)

    def a_dict(self) -> dict:
        return {"genes": self.genes}

    @classmethod
    def desde_dict(cls, data: dict) -> "Cromosoma":
        return cls(list(data["genes"]))

    def guardar_json(self, ruta: Path) -> None:
        ruta.write_text(json.dumps(self.a_dict(), indent=2), encoding="utf-8")

    @classmethod
    def cargar_json(cls, ruta: Path) -> "Cromosoma":
        data = json.loads(ruta.read_text(encoding="utf-8"))
        return cls.desde_dict(data)

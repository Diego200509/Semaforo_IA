"""
Banco de cromosomas pre-entrenados por escenario (Fase 2).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from genetico.cromosoma import Cromosoma

ETIQUETAS_VALIDAS: Tuple[str, ...] = ("bajo", "pico", "desbalanceado", "mixto")


@dataclass
class BancoCromosomas:
    por_contexto: Dict[str, Cromosoma]

    def cromosoma(self, etiqueta: str) -> Cromosoma | None:
        return self.por_contexto.get(etiqueta)

    def etiquetas(self) -> List[str]:
        return sorted(self.por_contexto.keys())


def guardar_banco(ruta: Path, banco: BancoCromosomas) -> None:
    data = {
        "version": 2,
        "cromosomas": {k: v.a_dict() for k, v in banco.por_contexto.items()},
    }
    ruta.write_text(json.dumps(data, indent=2), encoding="utf-8")


def cargar_banco(ruta: Path) -> BancoCromosomas:
    raw = json.loads(ruta.read_text(encoding="utf-8"))
    if isinstance(raw.get("cromosomas"), dict):
        por: Dict[str, Cromosoma] = {}
        for k, v in raw["cromosomas"].items():
            if isinstance(v, dict) and "genes" in v:
                por[str(k)] = Cromosoma.desde_dict(v)
        return BancoCromosomas(por_contexto=por)
    raise ValueError("Formato de banco no reconocido (se espera cromosomas dict).")

from __future__ import annotations

from typing import Mapping

import config


def siguiente_grupo_es_ns(
    estado: Mapping[str, float | bool | int],
    *,
    perfil_entrenamiento: str | None = None,
    peso_cola: float | None = None,
    peso_espera: float | None = None,
    umbral_empate: float | None = None,
) -> bool:
    params = config.obtener_parametros_politica_fase(perfil_entrenamiento)
    peso_cola = float(params["peso_cola"] if peso_cola is None else peso_cola)
    peso_espera = float(params["peso_espera"] if peso_espera is None else peso_espera)
    umbral_empate = float(params["umbral_empate"] if umbral_empate is None else umbral_empate)

    cn = float(estado.get("cola_ns", 0) or 0)
    ce = float(estado.get("cola_ew", 0) or 0)
    en = float(estado.get("espera_promedio_ns", 0) or 0)
    ee = float(estado.get("espera_promedio_ew", 0) or 0)
    sn = peso_cola * cn + peso_espera * en
    se = peso_cola * ce + peso_espera * ee
    if abs(sn - se) < umbral_empate:
        ult = estado.get("ultimo_verde_fue_ns")
        if isinstance(ult, bool):
            return not ult
        return False
    return sn >= se

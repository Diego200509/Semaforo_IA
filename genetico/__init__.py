"""Optimización genética de parámetros del sistema difuso."""

from genetico.cromosoma import Cromosoma
from genetico.fitness import evaluar_cromosoma

__all__ = ["Cromosoma", "evaluar_cromosoma", "ejecutar_ga"]


def __getattr__(name: str):
    if name == "ejecutar_ga":
        from genetico.ga import ejecutar_ga

        return ejecutar_ga
    raise AttributeError(name)

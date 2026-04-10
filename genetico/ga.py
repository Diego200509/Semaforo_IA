"""
Algoritmo genético con **DEAP**: selección por torneo, cruce BLX (`cxBlend`),
mutación gaussiana por gen y registro de estadísticas vía `eaSimple`.

El cromosoma sigue siendo `genetico.cromosoma.Cromosoma`; el mejor individuo
se obtiene del `HallOfFame`.
"""

from __future__ import annotations

import random
from typing import List, Tuple

import numpy as np
from deap import algorithms, base, creator, tools

import config
from genetico.cromosoma import Cromosoma
from genetico.fitness import evaluar_cromosoma


def _registrar_tipos_deap() -> None:
    """Evita error si se vuelve a importar el módulo (FitnessMax ya definido)."""
    try:
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    except RuntimeError:
        pass
    try:
        creator.create("Individual", list, fitness=creator.FitnessMax)
    except RuntimeError:
        pass


def _clip_genes(ind: list) -> None:
    for i in range(len(ind)):
        ind[i] = float(np.clip(ind[i], 0.0, 1.0))


def _mate_blend(ind1: list, ind2: list, alpha: float) -> tuple:
    tools.cxBlend(ind1, ind2, alpha)
    _clip_genes(ind1)
    _clip_genes(ind2)
    return ind1, ind2


def _mut_gauss(ind: list, mu: float, sigma: float, indpb: float) -> tuple:
    """Misma idea que `Cromosoma.mutar`: probabilidad por gen + recorte a [0, 1]."""
    tools.mutGaussian(ind, mu=mu, sigma=sigma, indpb=indpb)
    _clip_genes(ind)
    return (ind,)


def _semilla_evaluacion(individual: list, semilla_base: int) -> int:
    """Semilla determinista por genoma (estable dentro del proceso)."""
    acc = 0
    for x in individual:
        acc = (acc * 31 + int(float(x) * 1_000_000)) % (2**31 - 1)
    return semilla_base + acc * 9973 + 13


def ejecutar_ga(
    semilla_base: int | None = None,
    escenario_fitness: str | None = None,
    multi_escenario: bool | None = None,
) -> Tuple[Cromosoma, List[float]]:
    """
    Evoluciona una población y devuelve el mejor cromosoma y la serie de mejores fitness
    por generación (misma longitud que `GENERACIONES_GA`, sin incluir la estadística inicial).
    """
    semilla_base = semilla_base if semilla_base is not None else config.SEMILLA_ALEATORIA
    random.seed(semilla_base)
    np.random.seed(semilla_base % (2**32))

    _registrar_tipos_deap()

    def evaluar_individuo(individual: list) -> tuple[float, ...]:
        sem = _semilla_evaluacion(individual, semilla_base)
        crom = Cromosoma([float(x) for x in individual])
        fit, _ = evaluar_cromosoma(
            crom,
            semilla=sem,
            escenario=escenario_fitness,
            multi_escenario=multi_escenario,
        )
        return (fit,)

    toolbox = base.Toolbox()
    toolbox.register("attr_float", random.random)
    toolbox.register(
        "individual",
        tools.initRepeat,
        creator.Individual,
        toolbox.attr_float,
        n=Cromosoma.longitud_esperada(),
    )
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", evaluar_individuo)
    toolbox.register("mate", _mate_blend, alpha=0.35)
    toolbox.register("mutate", _mut_gauss, mu=0.0, sigma=0.08, indpb=config.PROB_MUTACION)
    toolbox.register("select", tools.selTournament, tournsize=3)

    pop = toolbox.population(n=config.POBLACION_GA)
    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("max", np.max)

    _, logbook = algorithms.eaSimple(
        pop,
        toolbox,
        cxpb=config.PROB_CRUCE,
        mutpb=1.0,
        ngen=config.GENERACIONES_GA,
        stats=stats,
        halloffame=hof,
        verbose=False,
    )

    mejor = Cromosoma([float(x) for x in hof[0]])
    # Gen 0 = población inicial; dejamos una entrada por generación evolutiva.
    todos_max = list(logbook.select("max"))
    historial = [float(x) for x in todos_max[1 : 1 + config.GENERACIONES_GA]]
    if len(historial) < config.GENERACIONES_GA:
        historial = [float(x) for x in todos_max[1:]]
    return mejor, historial


def ejecutar_entrenamiento_banco(semilla_base: int | None = None):
    """
    Entrena un cromosoma por cada etiqueta de contexto (un escenario GA cada uno).
    """
    from adaptacion.banco import BancoCromosomas, ETIQUETAS_VALIDAS, guardar_banco

    semilla_base = semilla_base if semilla_base is not None else config.SEMILLA_ALEATORIA
    por: dict = {}
    for i, esc in enumerate(ETIQUETAS_VALIDAS):
        mejor, _ = ejecutar_ga(
            semilla_base=semilla_base + 10007 * i + 3,
            escenario_fitness=esc,
            multi_escenario=False,
        )
        por[esc] = mejor
    banco = BancoCromosomas(por_contexto=por)
    guardar_banco(config.ARCHIVO_BANCO_CROMOSOMAS, banco)
    return banco

"""
Algoritmo genético con **DEAP**: selección por torneo, cruce BLX (`cxBlend`),
mutación gaussiana por gen y registro de estadísticas.

El cromosoma sigue siendo `genetico.cromosoma.Cromosoma`; el mejor individuo
se obtiene del `HallOfFame`. La evaluación usa semillas compartidas por
generación para que todos los individuos compitan bajo el mismo tráfico.
"""

from __future__ import annotations

import copy
import random
from typing import List, Tuple

import numpy as np
from deap import base, creator, tools

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


def _semillas_compartidas_generacion(
    semilla_base: int,
    generacion: int,
    cantidad: int = 3,
) -> tuple[int, ...]:
    """
    Genera un conjunto fijo de semillas por generación.

    Todos los individuos evaluados en la misma generación usan exactamente estas
    semillas, de modo que la comparación dependa del controlador y no de "suerte"
    en el tráfico.
    """
    rng = random.Random(semilla_base + 10_007 * generacion + 97)
    return tuple(rng.randrange(1, 2**31 - 1) for _ in range(max(1, int(cantidad))))


def _evaluar_poblacion_generacion(
    poblacion: list,
    *,
    generacion: int,
    semilla_base: int,
    perfil_entrenamiento: str,
    escenario_fitness: str | None,
    multi_escenario: bool | None,
) -> None:
    """
    Evalúa solo individuos inválidos usando el mismo bloque de semillas compartidas.
    """
    perfil_cfg = config.obtener_perfil_entrenamiento(perfil_entrenamiento)
    semillas = _semillas_compartidas_generacion(
        semilla_base,
        generacion,
        cantidad=perfil_cfg.semillas_compartidas_por_generacion,
    )
    invalidos = [ind for ind in poblacion if not ind.fitness.valid]
    for individual in invalidos:
        crom = Cromosoma([float(x) for x in individual])
        fitnesses: list[float] = []
        for semilla in semillas:
            fit, _ = evaluar_cromosoma(
                crom,
                semilla=semilla,
                duracion=perfil_cfg.duracion_evaluacion_fitness,
                escenario=escenario_fitness,
                multi_escenario=multi_escenario,
                perfil_entrenamiento=perfil_cfg.clave,
            )
            fitnesses.append(float(fit))
        # Promedio sobre el mismo conjunto compartido: comparación justa dentro de la generación.
        individual.fitness.values = (sum(fitnesses) / len(fitnesses),)


def _cantidad_elites(tamano_poblacion: int) -> int:
    """
    Limita el elitismo configurado para que siempre sea compatible con la población actual.
    """
    return max(0, min(int(config.ELITISMO), int(tamano_poblacion)))


def ejecutar_ga(
    semilla_base: int | None = None,
    escenario_fitness: str | None = None,
    multi_escenario: bool | None = None,
    perfil_entrenamiento: str | None = None,
) -> Tuple[Cromosoma, List[float]]:
    """
    Evoluciona una población y devuelve el mejor cromosoma y la serie de mejores fitness
    por generación (misma longitud que `GENERACIONES_GA`, sin incluir la estadística inicial).
    """
    semilla_base = semilla_base if semilla_base is not None else config.SEMILLA_ALEATORIA
    perfil_cfg = config.obtener_perfil_entrenamiento(perfil_entrenamiento)
    random.seed(semilla_base)
    np.random.seed(semilla_base % (2**32))

    _registrar_tipos_deap()

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
    toolbox.register("clone", copy.deepcopy)
    toolbox.register("mate", _mate_blend, alpha=0.35)
    # La mutacion tambien depende del perfil para que PRUEBA explore mas sin tocar FINAL.
    toolbox.register(
        "mutate",
        _mut_gauss,
        mu=0.0,
        sigma=perfil_cfg.sigma_mutacion_ga,
        indpb=perfil_cfg.prob_mutacion_ga,
    )
    toolbox.register("select", tools.selTournament, tournsize=3)

    pop = toolbox.population(n=perfil_cfg.poblacion_ga)
    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("max", np.max)
    logbook = tools.Logbook()
    logbook.header = ["gen", "nevals", "max"]

    _evaluar_poblacion_generacion(
        pop,
        generacion=0,
        semilla_base=semilla_base,
        perfil_entrenamiento=perfil_cfg.clave,
        escenario_fitness=escenario_fitness,
        multi_escenario=multi_escenario,
    )
    hof.update(pop)
    record = stats.compile(pop) if stats else {}
    logbook.record(gen=0, nevals=len(pop), **record)

    for gen in range(1, perfil_cfg.generaciones_ga + 1):
        print(f"Generación {gen}/{perfil_cfg.generaciones_ga} [{perfil_cfg.etiqueta_ui}]")
        # Elitismo real: estos individuos pasan intactos a la siguiente generación.
        n_elites = _cantidad_elites(len(pop))
        elites = list(map(toolbox.clone, tools.selBest(pop, n_elites)))

        offspring = toolbox.select(pop, len(pop) - n_elites)
        offspring = list(map(toolbox.clone, offspring))

        for hijo1, hijo2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < config.PROB_CRUCE:
                toolbox.mate(hijo1, hijo2)
                del hijo1.fitness.values
                del hijo2.fitness.values

        for mutante in offspring:
            toolbox.mutate(mutante)
            if mutante.fitness.valid:
                del mutante.fitness.values

        _evaluar_poblacion_generacion(
            offspring,
            generacion=gen,
            semilla_base=semilla_base,
            perfil_entrenamiento=perfil_cfg.clave,
            escenario_fitness=escenario_fitness,
            multi_escenario=multi_escenario,
        )

        pop[:] = elites + offspring
        hof.update(pop)
        record = stats.compile(pop) if stats else {}
        logbook.record(gen=gen, nevals=len(offspring), **record)

    mejor = Cromosoma([float(x) for x in hof[0]])
    # Gen 0 = población inicial; dejamos una entrada por generación evolutiva.
    todos_max = list(logbook.select("max"))
    historial = [float(x) for x in todos_max[1 : 1 + perfil_cfg.generaciones_ga]]
    if len(historial) < perfil_cfg.generaciones_ga:
        historial = [float(x) for x in todos_max[1:]]
    return mejor, historial


def ejecutar_entrenamiento_banco(
    semilla_base: int | None = None,
    perfil_entrenamiento: str | None = None,
):
    """
    Entrena un cromosoma por cada etiqueta de contexto (un escenario GA cada uno).
    """
    from adaptacion.banco import BancoCromosomas, ETIQUETAS_VALIDAS, guardar_banco

    semilla_base = semilla_base if semilla_base is not None else config.SEMILLA_ALEATORIA
    perfil_cfg = config.obtener_perfil_entrenamiento(perfil_entrenamiento)
    por: dict = {}
    for i, esc in enumerate(ETIQUETAS_VALIDAS):
        print(f"\n=== Entrenando escenario: {esc} ===")
        mejor, _ = ejecutar_ga(
            semilla_base=semilla_base + 10007 * i + 3,
            escenario_fitness=esc,
            multi_escenario=False,
            perfil_entrenamiento=perfil_cfg.clave,
        )
        por[esc] = mejor
    banco = BancoCromosomas(por_contexto=por)
    guardar_banco(perfil_cfg.archivo_banco_cromosomas, banco)
    return banco

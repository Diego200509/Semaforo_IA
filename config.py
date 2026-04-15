from dataclasses import dataclass
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent
CARPETA_ASSETS = RAIZ_PROYECTO / "assets"
CARPETA_CARROS = CARPETA_ASSETS / "carros"
CARPETA_SEMAFOROS = CARPETA_ASSETS / "semaforos"
CARPETA_FONDOS = CARPETA_ASSETS / "fondos"
CARPETA_GRAFICAS = RAIZ_PROYECTO / "graficas"


def asegurar_carpeta_graficas() -> None:
    CARPETA_GRAFICAS.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class PerfilEntrenamiento:

    clave: str
    etiqueta_ui: str
    poblacion_ga: int
    generaciones_ga: int
    semillas_compartidas_por_generacion: int
    duracion_evaluacion_fitness: float
    prob_mutacion_ga: float
    sigma_mutacion_ga: float
    peso_cola_fase: float
    peso_espera_fase: float
    umbral_empate_fase: float
    archivo_mejor_cromosoma: Path
    archivo_grafica_evolucion: Path
    archivo_grafica_estrategias_promedio: Path
    archivo_grafica_por_escenario: Path
    archivo_grafica_comparacion_costes: Path


PERFIL_ENTRENAMIENTO_POR_DEFECTO = "final"
PESO_COLA_FASE = 1.0
PESO_ESPERA_FASE = 0.08
UMBRAL_EMPATE_FASE = 0.75

PERFILES_ENTRENAMIENTO = {
    "prueba": PerfilEntrenamiento(
        clave="prueba",
        etiqueta_ui="PRUEBA",
        poblacion_ga=14,
        generaciones_ga=10,
        semillas_compartidas_por_generacion=2,
        duracion_evaluacion_fitness=45.0,
        prob_mutacion_ga=0.16,
        sigma_mutacion_ga=0.10,
        peso_cola_fase=PESO_COLA_FASE,
        peso_espera_fase=PESO_ESPERA_FASE,
        umbral_empate_fase=UMBRAL_EMPATE_FASE,
        archivo_mejor_cromosoma=RAIZ_PROYECTO / "cromosoma_prueba.json",
        archivo_grafica_evolucion=CARPETA_GRAFICAS / "evolucion_fitness_prueba.png",
        archivo_grafica_estrategias_promedio=CARPETA_GRAFICAS / "comparacion_estrategias_promedio_prueba.png",
        archivo_grafica_por_escenario=CARPETA_GRAFICAS / "comparacion_por_escenario_prueba.png",
        archivo_grafica_comparacion_costes=CARPETA_GRAFICAS / "comparacion_costes_prueba.png",
    ),
    "final": PerfilEntrenamiento(
        clave="final",
        etiqueta_ui="FINAL",
        poblacion_ga=24,
        generaciones_ga=18,
        semillas_compartidas_por_generacion=3,
        duracion_evaluacion_fitness=120.0,
        prob_mutacion_ga=0.12,
        sigma_mutacion_ga=0.08,
        peso_cola_fase=PESO_COLA_FASE,
        peso_espera_fase=PESO_ESPERA_FASE,
        umbral_empate_fase=UMBRAL_EMPATE_FASE,
        archivo_mejor_cromosoma=RAIZ_PROYECTO / "cromosoma_final.json",
        archivo_grafica_evolucion=CARPETA_GRAFICAS / "evolucion_fitness_final.png",
        archivo_grafica_estrategias_promedio=CARPETA_GRAFICAS / "comparacion_estrategias_promedio_final.png",
        archivo_grafica_por_escenario=CARPETA_GRAFICAS / "comparacion_por_escenario_final.png",
        archivo_grafica_comparacion_costes=CARPETA_GRAFICAS / "comparacion_costes_final.png",
    ),
}
PERFILES_ENTRENAMIENTO_UI = tuple(p.etiqueta_ui for p in PERFILES_ENTRENAMIENTO.values())


def obtener_perfil_entrenamiento(perfil: str | None = None) -> PerfilEntrenamiento:
    clave = (perfil or PERFIL_ENTRENAMIENTO_POR_DEFECTO).strip().lower()
    if clave not in PERFILES_ENTRENAMIENTO:
        validos = ", ".join(sorted(PERFILES_ENTRENAMIENTO))
        raise ValueError(f"Perfil de entrenamiento no válido: {perfil}. Use: {validos}")
    return PERFILES_ENTRENAMIENTO[clave]


def obtener_parametros_politica_fase(perfil: str | None = None) -> dict[str, float]:
    perfil_cfg = obtener_perfil_entrenamiento(perfil)
    return {
        "peso_cola": float(perfil_cfg.peso_cola_fase),
        "peso_espera": float(perfil_cfg.peso_espera_fase),
        "umbral_empate": float(perfil_cfg.umbral_empate_fase),
    }


ANCHO_VENTANA = 900
ALTO_VENTANA = 650
MITAD_ANCHO_VIA = 55.0
SEPARACION_CARRILES_MISMO_SENTIDO = 18.0
OFFSET_CENTRO_GRUPO_CARRIL = 28.0
FPS = 60
TITULO_VENTANA = "Proyecto Semáforo IA — Simulación"

SPRITE_VEHICULO_MULT_RADIO = 4.35
SPRITE_VEHICULO_LADO_MIN = 34
SPRITE_VEHICULO_ESCALADO_SUAVE = False

HUD_METRICAS_COLOR = (12, 12, 12)
HUD_METRICAS_CONTORNO = (255, 255, 255)
HUD_METRICAS_CONTORNO_GROSOR = 1
HUD_METRICAS_FUENTE_PX = 14
HUD_PANEL_PADDING = 6
HUD_PANEL_LINE_GAP = 2
HUD_PANEL_RELLENO = (255, 252, 245)
HUD_PANEL_ALPHA = 242
HUD_PANEL_BORDE_PX = 2
HUD_PANEL_BORDE_COLOR = (0, 0, 0)
HUD_METRICAS_NOMBRES_FUENTE = (
    "Press Start 2P",
    "VT323",
    "Pixeloid Mono",
    "Silkscreen",
    "Fixedsys",
    "Consolas",
    "Courier New",
)

COLOR_FONDO = (32, 36, 48)
COLOR_CALLE = (48, 52, 62)
COLOR_CENTRO = (40, 44, 54)
COLOR_MARCA_VIAL = (248, 248, 252)
COLOR_MARCA_VIAL_PARALELA = (198, 200, 210)
MARCAS_VIALES_DASH_PX = 10
MARCAS_VIALES_GAP_PX = 7
CRUCE_MARCO_GROSOR_PX = 3
COLOR_CARRO_NS = (220, 90, 90)
COLOR_CARRO_EW = (90, 140, 220)
COLOR_TEXTO = (230, 230, 235)
COLOR_SEMAFORO_ROJO = (200, 50, 50)
COLOR_SEMAFORO_AMARILLO = (220, 200, 60)
COLOR_SEMAFORO_VERDE = (80, 200, 100)
COLOR_SEMAFORO_BORDE = (0, 0, 0)
SEMAFORO_RADIO_PX = 7
SEMAFORO_BORDE_PX = 2

CAPACIDAD_REFERENCIA_VEHICULOS = 24
MAX_VEHICULOS_EN_MAPA = 30
INTERVALO_SPAWN_BASE = 1.8
VELOCIDAD_BASE = 85.0
GAP_VISUAL_ENTRE_VEHICULOS = 3.0
SEPARACION_BASE_CENTROS_PX = 5.0
TOLERANCIA_MISMO_CORREDOR_PX = 16.0
SEPARACION_COLA_SUAVIDAD = 0.58
SEPARACION_REFUERZO_LONG_MAX_PX = 5.5
DISTANCIA_SALIDA_CRUCE = 52.0
DISTANCIA_PARADA_ANTE_SEMAFORO = float(DISTANCIA_SALIDA_CRUCE) + 16.0
MARGEN_BORDE_VEHICULO = 120.0
MARGEN_SPAWN_VENTANA = 18.0
MARGEN_RETIRO_VENTANA = 28.0

VEHICULOS_SOLO_RECTO = True
USA_FASE_ADAPTATIVA = True
UMBRAL_INICIO_GIRO_CRUCE = 44.0
PROB_MANIOBRA_RECTO = 0.58
PROB_MANIOBRA_IZQUIERDA = 0.21
PROB_MANIOBRA_DERECHA = 0.21
PESOS_SPAWN_TIPO_VEHICULO = (0.18, 0.52, 0.15, 0.15)
ESCENARIOS_ENTRENAMIENTO_GA = ("bajo", "pico", "desbalanceado", "mixto")
PESOS_ENTRENAMIENTO_MULTI_ESCENARIO = (0.25, 0.25, 0.25, 0.25)
USA_ENTRENAMIENTO_MULTI_ESCENARIO = True
RADIO_ZONA_CRUCE_INTERIOR = 58.0

DURACION_AMARILLO = 3.0
VERDE_MIN = 8
VERDE_MAX = 55
VERDE_FIJO_NS = 22
VERDE_FIJO_EW = 22

ESPERA_MAX_UNIVERSO = 90.0 
COLA_MAX_UNIVERSO = 20.0 

POBLACION_GA = 24
GENERACIONES_GA = 18
PROB_CRUCE = 0.75
PROB_MUTACION = 0.12
ELITISMO = 2
SEMILLA_ALEATORIA = 42

DURACION_EVALUACION_FITNESS = 120.0
DT_SIMULACION_RAPIDA = 0.25

PESO_TIEMPO_ESPERA = 0.42
PESO_LONGITUD_COLA = 0.26
PESO_VEHICULOS_ATENDIDOS = 0.28
PESO_TIEMPO_ESPERA_MAXIMA = 0.16
PESO_COLA_MAXIMA = 0.10
PESO_DEMORA_PROMEDIO_POR_VEHICULO = 0.10
PESO_DESEQUILIBRIO_ESPERA_EJES = 0.14
PESO_DESEQUILIBRIO_COLA_EJES = 0.08

ARCHIVO_MEJOR_CROMOSOMA = obtener_perfil_entrenamiento("final").archivo_mejor_cromosoma

ESCENARIO_POR_DEFECTO = "bajo"
DURACION_REFERENCIA_MIXTO = 120.0
DURACION_PLAN_VISUAL_MIXTO = 900.0

SEED_COMPARACION = 7
DURACION_ESCENARIO_COMPARACION = 180.0
DURACION_COMPARAR_DIFUSO_GA = 120.0
SEEDS_COMPARACION_MULTISEMILLA = [1, 7, 15, 23, 42]
SEEDS_COMPARACION_COMPLETA = [1, 7, 15, 23, 42]
ESCENARIOS_COMPARACION_COMPLETA = ("bajo", "pico", "desbalanceado", "mixto")
ESCENARIO_ENTRENAMIENTO_GA = "bajo"

ARCHIVO_GRAFICA_EVOLUCION_FITNESS = obtener_perfil_entrenamiento("final").archivo_grafica_evolucion
ARCHIVO_GRAFICA_COMPARACION_COSTES = CARPETA_GRAFICAS / "comparacion_costes.png"
ARCHIVO_GRAFICA_COMPARAR_GA = CARPETA_GRAFICAS / "comparacion_sin_ga_vs_ga.png"
ARCHIVO_GRAFICA_ESTRATEGIAS_PROMEDIO = CARPETA_GRAFICAS / "comparacion_estrategias_promedio.png"
ARCHIVO_GRAFICA_POR_ESCENARIO = CARPETA_GRAFICAS / "comparacion_por_escenario.png"

ESCENARIO_COMPARAR_COMPLETO = "mixto"

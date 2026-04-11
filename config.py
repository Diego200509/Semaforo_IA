"""
Configuración global del proyecto: dimensiones, tiempos, límites y rutas.
Centralizar constantes aquí facilita experimentos y la defensa académica del sistema.
"""

from dataclasses import dataclass
from pathlib import Path

# --- Rutas del proyecto ---
RAIZ_PROYECTO = Path(__file__).resolve().parent
CARPETA_ASSETS = RAIZ_PROYECTO / "assets"
CARPETA_CARROS = CARPETA_ASSETS / "carros"
CARPETA_SEMAFOROS = CARPETA_ASSETS / "semaforos"
CARPETA_FONDOS = CARPETA_ASSETS / "fondos"
# Vehículos (Pygame): en carros/ pon moto.png, auto.png, bus.png, camion.png (o un solo coche.png).
# Fondo de la ventana: en fondos/ cualquier .png/.jpg (se usa el primero por nombre y se escala a la ventana).
# Salida de gráficas Matplotlib (evolución GA, comparaciones, etc.).
CARPETA_GRAFICAS = RAIZ_PROYECTO / "graficas"


def asegurar_carpeta_graficas() -> None:
    """Crea la carpeta de gráficas si no existe."""
    CARPETA_GRAFICAS.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class PerfilEntrenamiento:
    """
    Dos perfiles simples para separar pruebas rápidas de corridas finales.
    """

    clave: str
    etiqueta_ui: str
    poblacion_ga: int
    generaciones_ga: int
    semillas_compartidas_por_generacion: int
    duracion_evaluacion_fitness: float
    archivo_mejor_cromosoma: Path
    archivo_banco_cromosomas: Path
    archivo_grafica_evolucion: Path
    archivo_grafica_estrategias_promedio: Path
    archivo_grafica_por_escenario: Path
    archivo_grafica_comparacion_costes: Path


PERFIL_ENTRENAMIENTO_POR_DEFECTO = "final"
PERFILES_ENTRENAMIENTO = {
    "prueba": PerfilEntrenamiento(
        clave="prueba",
        etiqueta_ui="PRUEBA",
        poblacion_ga=10,
        generaciones_ga=6,
        semillas_compartidas_por_generacion=2,
        duracion_evaluacion_fitness=45.0,
        archivo_mejor_cromosoma=RAIZ_PROYECTO / "cromosoma_prueba.json",
        archivo_banco_cromosomas=RAIZ_PROYECTO / "banco_prueba.json",
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
        archivo_mejor_cromosoma=RAIZ_PROYECTO / "cromosoma_final.json",
        archivo_banco_cromosomas=RAIZ_PROYECTO / "banco_final.json",
        archivo_grafica_evolucion=CARPETA_GRAFICAS / "evolucion_fitness_final.png",
        archivo_grafica_estrategias_promedio=CARPETA_GRAFICAS / "comparacion_estrategias_promedio_final.png",
        archivo_grafica_por_escenario=CARPETA_GRAFICAS / "comparacion_por_escenario_final.png",
        archivo_grafica_comparacion_costes=CARPETA_GRAFICAS / "comparacion_costes_final.png",
    ),
}
PERFILES_ENTRENAMIENTO_UI = tuple(p.etiqueta_ui for p in PERFILES_ENTRENAMIENTO.values())


def obtener_perfil_entrenamiento(perfil: str | None = None) -> PerfilEntrenamiento:
    """
    Normaliza el nombre del perfil y devuelve su configuración completa.
    """
    clave = (perfil or PERFIL_ENTRENAMIENTO_POR_DEFECTO).strip().lower()
    if clave not in PERFILES_ENTRENAMIENTO:
        validos = ", ".join(sorted(PERFILES_ENTRENAMIENTO))
        raise ValueError(f"Perfil de entrenamiento no válido: {perfil}. Use: {validos}")
    return PERFILES_ENTRENAMIENTO[clave]


# --- Ventana Pygame (simulación visual) ---
ANCHO_VENTANA = 900
ALTO_VENTANA = 650
# Mitad del ancho de calle (px), debe coincidir con entorno.dibujar (ancho_calle / 2).
MITAD_ANCHO_VIA = 55.0
# Carril recto vs giro dentro del mismo sentido: separación entre sus ejes (px).
SEPARACION_CARRILES_MISMO_SENTIDO = 18.0
# Distancia desde el centro del cruce al punto medio entre esos dos carriles (px), dentro de la mitad de vía.
OFFSET_CENTRO_GRUPO_CARRIL = 28.0
FPS = 60
TITULO_VENTANA = "Proyecto Semáforo IA — Simulación"

# --- Pygame: sprites de vehículos (tamaño en pantalla respecto al radio lógico) ---
SPRITE_VEHICULO_MULT_RADIO = 4.35
SPRITE_VEHICULO_LADO_MIN = 34
# True = suavizado (fotos); False = vecino más cercano (mejor para pixel art).
SPRITE_VEHICULO_ESCALADO_SUAVE = False

# --- Pygame: panel de métricas (esquina superior izquierda) ---
HUD_METRICAS_COLOR = (12, 12, 12)
HUD_METRICAS_CONTORNO = (255, 255, 255)
HUD_METRICAS_CONTORNO_GROSOR = 1
HUD_METRICAS_FUENTE_PX = 17
HUD_PANEL_PADDING = 10
HUD_PANEL_RELLENO = (255, 252, 245)
HUD_PANEL_ALPHA = 242
HUD_PANEL_BORDE_PX = 2
HUD_PANEL_BORDE_COLOR = (0, 0, 0)
# Orden de búsqueda (tipos pixel / monoespaciados típicos en Windows).
HUD_METRICAS_NOMBRES_FUENTE = (
    "Press Start 2P",
    "VT323",
    "Pixeloid Mono",
    "Silkscreen",
    "Fixedsys",
    "Consolas",
    "Courier New",
)

# --- Colores RGB (útiles para Pygame y gráficas) ---
COLOR_FONDO = (32, 36, 48)
COLOR_CALLE = (48, 52, 62)
COLOR_CENTRO = (40, 44, 54)
# Marcas viales dibujadas en Pygame (alineadas a OFFSET_CENTRO_GRUPO_CARRIL / MITAD_ANCHO_VIA).
COLOR_MARCA_VIAL = (248, 248, 252)
# Líneas al hilo (paralelas al sentido), algo más suaves que el eje central.
COLOR_MARCA_VIAL_PARALELA = (198, 200, 210)
MARCAS_VIALES_DASH_PX = 10
MARCAS_VIALES_GAP_PX = 7
# Contorno continuo del cuadro del cruce (Pygame); grosor del rectángulo blanco.
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

# --- Intersección y tráfico ---
# Capacidad de referencia para normalizar "densidad" (vehículos presentes / este valor).
CAPACIDAD_REFERENCIA_VEHICULOS = 24
# Máximo de vehículos que pueden existir a la vez en la simulación simple.
MAX_VEHICULOS_EN_MAPA = 30
# Intervalo aproximado entre apariciones de vehículos (segundos), se usa jitter aleatorio.
INTERVALO_SPAWN_BASE = 1.8
# Velocidad base de movimiento (píxeles por segundo) en calle libre.
VELOCIDAD_BASE = 85.0
# Hueco extra entre centros de vehículos en cola (además de radios); más bajo = cola más junta.
GAP_VISUAL_ENTRE_VEHICULOS = 3.0
# Suma mínima en px además de los radios (separación entre centros); bajar acerca más los coches en cola.
SEPARACION_BASE_CENTROS_PX = 5.0
# Misma fila lógica aunque el guiado lateral aún no los haya alineado del todo (< separación recto/giro ~18 px).
TOLERANCIA_MISMO_CORREDOR_PX = 16.0
# 0–1: corrección de separación en cola por fotograma (más alto = cierra huecos antes).
SEPARACION_COLA_SUAVIDAD = 0.58
# Paso máx. (px) del refuerzo longitudinal tras la cola (evita solapes sin empuje 2D del cruce).
SEPARACION_REFUERZO_LONG_MAX_PX = 5.5
# Referencia ~ mitad del ancho del cruce dibujado; sirve para colocar la línea de parada (no es el punto de desaparición).
DISTANCIA_SALIDA_CRUCE = 52.0
# Distancia desde el centro hasta la línea de parada (píxeles en el eje de marcha). Debe ser mayor que la mitad
# del cuadro central en la vista (entorno.dibujar usa ancho_calle=110 → mitad 55); si es menor, el coche frena
# dentro del recuadro oscuro del cruce.
DISTANCIA_PARADA_ANTE_SEMAFORO = float(DISTANCIA_SALIDA_CRUCE) + 16.0
# Reservado (p. ej. HUD); el spawn usa MARGEN_SPAWN_VENTANA.
MARGEN_BORDE_VEHICULO = 120.0
# Centro del vehículo a esta distancia del borde de la ventana al aparecer (inicio visual del carril).
MARGEN_SPAWN_VENTANA = 18.0
# Distancia del borde (desde el centro del vehículo) para retirarlo del mapa. Menor = casi al borde visible.
MARGEN_RETIRO_VENTANA = 28.0

# --- Fase 2: giros, tipos, carriles, fase adaptativa, GA multi-escenario ---
# True: solo trayectoria recta (sin giros ni carril de giro). False: usa PROB_MANIOBRA_* y UMBRAL_INICIO_GIRO_CRUCE.
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
ARCHIVO_BANCO_CROMOSOMAS = obtener_perfil_entrenamiento("final").archivo_banco_cromosomas
# Radio (px) alrededor del centro: dentro se aplica tope de velocidad por factor_despeje (cruce ocupado más tiempo).
RADIO_ZONA_CRUCE_INTERIOR = 58.0

# --- Semáforo (tiempos en segundos) ---
DURACION_AMARILLO = 3.0
VERDE_MIN = 8
VERDE_MAX = 55
# Ciclo de referencia para modo tiempo fijo (segundos de verde por fase).
VERDE_FIJO_NS = 22
VERDE_FIJO_EW = 22

# --- Universos difusos (rangos numéricos reales antes de normalizar) ---
ESPERA_MAX_UNIVERSO = 90.0  # segundos
COLA_MAX_UNIVERSO = 20.0  # vehículos en la aproximación más cargada

# --- Algoritmo genético ---
POBLACION_GA = 24
GENERACIONES_GA = 18
PROB_CRUCE = 0.75
PROB_MUTACION = 0.12
ELITISMO = 2
SEMILLA_ALEATORIA = 42

# Duración de cada evaluación de fitness (segundos de simulación acelerada).
DURACION_EVALUACION_FITNESS = 120.0
# En entrenamiento sin ventana, pasos de simulación más largos por tick interno.
DT_SIMULACION_RAPIDA = 0.25

# Pesos de la función fitness compuesta (minimizar espera y cola; maximizar atendidos).
PESO_TIEMPO_ESPERA = 0.5
PESO_LONGITUD_COLA = 0.3
PESO_VEHICULOS_ATENDIDOS = 0.2

# Archivo donde se guarda el mejor cromosoma tras entrenar.
ARCHIVO_MEJOR_CROMOSOMA = obtener_perfil_entrenamiento("final").archivo_mejor_cromosoma

# --- Escenarios de tráfico (solo generación; no afecta difuso/GA) ---
ESCENARIO_POR_DEFECTO = "bajo"
# Duración de referencia para escalar el escenario mixto (plantilla 0–120 s).
DURACION_REFERENCIA_MIXTO = 120.0
# En modo visual sin límite de tiempo, escala mixto con esta duración (segundos).
DURACION_PLAN_VISUAL_MIXTO = 900.0

# --- Comparación y gráficas ---
SEED_COMPARACION = 7
DURACION_ESCENARIO_COMPARACION = 180.0
# Duración por defecto para `comparar` (promedios multisemilla).
DURACION_COMPARAR_DIFUSO_GA = 120.0
# Semillas para `comparar` (promedio por estrategia).
SEEDS_COMPARACION_MULTISEMILLA = [1, 7, 15, 23, 42]
# Entrenamiento GA: perfil de tráfico fijo durante evaluación de fitness.
ESCENARIO_ENTRENAMIENTO_GA = "bajo"

# Salida de gráficas de evaluación (dentro de CARPETA_GRAFICAS).
ARCHIVO_GRAFICA_EVOLUCION_FITNESS = obtener_perfil_entrenamiento("final").archivo_grafica_evolucion
ARCHIVO_GRAFICA_COMPARACION_COSTES = CARPETA_GRAFICAS / "comparacion_costes.png"
ARCHIVO_GRAFICA_COMPARAR_GA = CARPETA_GRAFICAS / "comparacion_sin_ga_vs_ga.png"
ARCHIVO_GRAFICA_ESTRATEGIAS_PROMEDIO = CARPETA_GRAFICAS / "comparacion_estrategias_promedio.png"
ARCHIVO_GRAFICA_POR_ESCENARIO = CARPETA_GRAFICAS / "comparacion_por_escenario.png"

# Escenario usado en `comparar_completo` (una semilla, coste compuesto; retrocompatibilidad).
ESCENARIO_COMPARAR_COMPLETO = "bajo"

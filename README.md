# Proyecto Semáforo IA

Sistema inteligente **híbrido** para regular de forma dinámica los tiempos de luz verde en una intersección urbana simplificada. Combina:

- **Lógica difusa (Mamdani)** para traducir variables de tráfico en un tiempo de verde.
- **Algoritmo genético** para ajustar la forma de las funciones de membresía.
- **Simulación local** con interfaz abstracta pensada para sustituir el motor por **SUMO** en el futuro sin reescribir el núcleo de IA.

## Arquitectura en una frase

El **controlador principal** (`main.py`) solo habla con un **motor de simulación** que cumple `obtener_estado_trafico`, `aplicar_tiempo_verde`, `actualizar`, `reiniciar` y `obtener_metricas`. La lógica difusa y el GA **no conocen** Pygame ni SUMO.

## Requisitos

- Python **3.10–3.12** recomendado (en versiones muy nuevas pueden fallar extensiones binarias por políticas del SO).
- Dependencias declaradas en `requirements.txt`:
  - **numpy** (1.26.4 en el archivo): cómputo numérico en difuso, GA y simulación.
  - **scikit-fuzzy** (`skfuzzy`): triángulos de membresía, interpolación y defuzzificación por centroide (`difuso/variables.py`, `difuso/controlador.py`).
  - **scipy**: incluida en `requirements.txt`; **scikit-fuzzy** la usa internamente (el código del proyecto no importa `scipy` directamente).
  - **deap**: bucle evolutivo del GA (selección, cruce `cxBlend`, mutación gaussiana, `eaSimple`) en `genetico/ga.py`.
  - **pygame**: solo para `--modo sim_visual` (importación perezosa en `simulacion/entorno.py`). En Python más reciente, **pygame-ce** es una alternativa compatible que el propio código sugiere si falla la instalación clásica.
  - **matplotlib**: gráficas en `--modo entrenar`, `--modo comparar`, `--modo comparar_completo` (importación al usar esas rutas).

## Instalación

Desde la carpeta del proyecto:

```bash
python -m pip install -r requirements.txt
```

Si `matplotlib` o `pygame` fallan por DLLs bloqueadas en Windows, puedes seguir usando simulación **sin ventana**:

```bash
python main.py --modo sim_prog --segundos 120
```

---

## Parámetros del difuso (automático y manual)

En **sim_visual** y **sim_prog**, cuando el control **no** está en `--tiempo-fijo`, el programa elige los parámetros del difuso así:

| Situación | Qué ocurre |
|-----------|------------|
| Existe `mejor_cromosoma.json` en la raíz del proyecto | Se cargan esos valores optimizados por el GA. En consola: **«Usando parámetros optimizados del GA»**. |
| No existe el archivo | Se usan los parámetros por defecto del código. En consola: **«Usando parámetros por defecto»**. |

Puedes **forzar** el comportamiento (solo una de estas a la vez):

| Opción | Efecto |
|--------|--------|
| `--usar-default` | Siempre parámetros por defecto, **aunque** exista el JSON. |
| `--usar-ga` | Siempre cargar el JSON; si **no** existe, el programa **termina con error** (te indica que entrenes antes). |
| `--mejor-cromosoma` | Igual que `--usar-ga` (nombre antiguo, por compatibilidad). |

Con `--tiempo-fijo` no hay difuso: no se muestran esos mensajes y el semáforo usa duraciones fijas de `config.py`.

---

## Guía de comandos (`main.py`)

La forma general es:

```bash
python main.py [--modo MODO] [opciones]
```

Si omites `--modo`, el valor por defecto es **`sim_visual`**.

### `--segundos` (duración)

- En **`sim_prog`**: si **no** lo pones, la simulación dura **90** segundos.
- En **`comparar`**: si **no** lo pones, la duración es la de `config.py` (**120** s por defecto, constante `DURACION_COMPARAR_DIFUSO_GA`).
- En **`comparar_completo`**: la duración **no** usa `--segundos`; sigue la constante `DURACION_ESCENARIO_COMPARACION` en `config.py` (p. ej. 180 s).

Ejemplo: misma duración en consola y en comparación:

```bash
python main.py --modo sim_prog --segundos 60
python main.py --modo comparar --segundos 60
```

---

### Modo `sim_visual` — ventana gráfica (Pygame)

**Qué hace:** abre una ventana con el cruce, vehículos, semáforos y un pequeño panel de texto (densidad, espera, cola, etc.).

```bash
python main.py --modo sim_visual
```

Equivalente (porque `sim_visual` es el modo por defecto):

```bash
python main.py
```

**Variantes útiles:**

```bash
# Semáforo con tiempos fijos (sin difuso)
python main.py --modo sim_visual --tiempo-fijo

# Forzar parámetros por defecto del difuso aunque tengas mejor_cromosoma.json
python main.py --modo sim_visual --usar-default

# Forzar uso del JSON optimizado (falla si no existe)
python main.py --modo sim_visual --usar-ga
```

Cierra la ventana o pulsa **ESC** para salir.

---

### Modo `sim_prog` — simulación rápida por consola

**Qué hace:** ejecuta la misma lógica que la visual pero **sin ventana**; al final imprime una línea con métricas (espera promedio, cola, atendidos, tiempo simulado).

```bash
python main.py --modo sim_prog
```

Por defecto corre **90** segundos de simulación. Para otra duración:

```bash
python main.py --modo sim_prog --segundos 120
```

Combina con `--tiempo-fijo`, `--usar-default` o `--usar-ga` igual que en `sim_visual`.

---

### Modo `entrenar` — algoritmo genético (offline)

**Qué hace:** evoluciona la población, evalúa individuos con la simulación programática y guarda el mejor cromosoma en la raíz del proyecto.

```bash
python main.py --modo entrenar
```

**Salida:** `mejor_cromosoma.json` y `graficas/evolucion_fitness.png`. Puede tardar varios minutos.

A partir de ahí, en `sim_visual` / `sim_prog` el sistema **cargará solo** ese archivo si existe (salvo que uses `--usar-default`).

---

### Modo `comparar` — difuso base vs difuso entrenado (GA)

**Qué hace:**

1. Ejecuta **dos** simulaciones con la **misma semilla** y la **misma duración**: primero difuso con parámetros por defecto, luego difuso con `mejor_cromosoma.json` **si** el archivo existe.
2. Imprime en consola un bloque **RESULTADOS** (espera promedio, cola promedio, vehículos atendidos) para **SIN GA** y **CON GA**.
3. Genera gráficas en la carpeta **`graficas/`** (p. ej. `comparacion_estrategias_promedio.png` y `comparacion_por_escenario.png`).

```bash
python main.py --modo comparar
```

Duración por defecto **120** s (configurable en `config.py` o por línea de comandos):

```bash
python main.py --modo comparar --segundos 180
```

Si **no** hay `mejor_cromosoma.json`, solo se ejecuta el caso «sin GA» y en consola se indica que falta entrenar; la gráfica muestra solo ese escenario.

---

### Modo `comparar_completo` — tres estrategias y coste compuesto

**Qué hace:** conserva la comparación **amplia** del proyecto: **tiempo fijo**, **difuso base** y **difuso + GA** (este último solo si existe el JSON), todas con la misma semilla y la duración de `DURACION_ESCENARIO_COMPARACION` en `config.py`. Imprime el **coste compuesto** de cada una y guarda `graficas/comparacion_costes.png` (una barra por estrategia).

```bash
python main.py --modo comparar_completo
```

**Nota:** este modo **no** usa `--segundos`; para cambiar la duración edita `config.py` o el código que llama a `ejecutar_comparacion`.

---

## Resumen rápido de modos

| Modo | Comando típico | Idea en una frase |
|------|----------------|-------------------|
| `sim_visual` | `python main.py` | Ver el cruce en una ventana. |
| `sim_prog` | `python main.py --modo sim_prog --segundos 90` | Métricas en texto, sin gráficos. |
| `entrenar` | `python main.py --modo entrenar` | Entrenar el GA y generar el JSON. |
| `comparar` | `python main.py --modo comparar` | Medir impacto del GA (2 corridas + gráfica de métricas). |
| `comparar_completo` | `python main.py --modo comparar_completo` | Comparar tres políticas por **coste** + gráfica de costes. |

---

## Archivos generados

Las gráficas PNG se guardan en la carpeta **`graficas/`** (se crea sola al generar la primera).

| Archivo | Cuándo aparece |
|---------|----------------|
| `mejor_cromosoma.json` | Tras `--modo entrenar`. |
| `graficas/evolucion_fitness.png` | Tras `--modo entrenar`. |
| `graficas/comparacion_estrategias_promedio.png` | Tras `--modo comparar`. |
| `graficas/comparacion_por_escenario.png` | Tras `--modo comparar`. |
| `graficas/comparacion_costes.png` | Tras `--modo comparar_completo`. |

---

## Variables difusas

**Entradas** (normalizadas internamente a \([0,1]\)):

1. Densidad vehicular (respecto a `CAPACIDAD_REFERENCIA_VEHICULOS`).
2. Tiempo de espera promedio (respecto a `ESPERA_MAX_UNIVERSO`).
3. Longitud de cola dominante (respecto a `COLA_MAX_UNIVERSO`).

**Salida**: tiempo de luz verde en segundos, acotado a `[VERDE_MIN, VERDE_MAX]`.

Las reglas están listadas en `difuso/reglas.py` (9 reglas, conjunto defendible y compacto).

## Algoritmo genético

- **Cromosoma**: 20 genes en \([0,1]\), agrupados y **ordenados** en cuatro bloques de 5 vértices que definen términos triangulares (véase `genetico/cromosoma.py`).
- **Motor evolutivo**: **DEAP** registra tipos `FitnessMax` / `Individual` y ejecuta `algorithms.eaSimple` con operadores configurados en `genetico/ga.py`.
- **Fitness**: se **maximiza** \(-\text{coste}\), con  
  \(\text{coste} = 0{,}5\,\hat{t}_{esp} + 0{,}3\,\hat{q} - 0{,}2\,\hat{n}_{at}\)  
  (espera y cola normalizadas penalizan; vehículos atendidos premian). Los pesos concretos están en `config.py` (`PESO_TIEMPO_ESPERA`, etc.).

## Migración futura a SUMO (resumen)

1. Crear `simulacion/motor_sumo.py` con una clase que implemente la misma interfaz que `MotorSimulacion`.
2. `obtener_estado_trafico()` leería datos de TraCI; `aplicar_tiempo_verde()` escribiría duraciones de fase; `actualizar()` avanzaría un paso de simulación SUMO.
3. **Sin cambios** esperados en `difuso/`, `genetico/` y `evaluacion/` salvo ajustes de escalas de normalización si las unidades difieren.

## Créditos académicos

Proyecto modular pensado para **exposición oral**: cada carpeta tiene una responsabilidad clara y comentarios donde la lógica no es obvia.

## Comandos para ejecutar

Desde la raíz del proyecto (entorno virtual activado). Ver todas las opciones: `python main.py --help`.

```bash
python main.py  # Simulación con ventana (modo por defecto).
python main.py --modo sim_visual  # Igual: Pygame + cruce.
python main.py --modo sim_visual --escenario mixto --verbose-escenario  # Escenario mixto con avisos en consola.
python main.py --modo sim_visual --usar-ga  # Carga mejor_cromosoma.json (falla si no existe).
python main.py --modo sim_visual --adaptacion-banco  # Elige cromosoma según contexto (banco_cromosomas.json).
python main.py --modo sim_visual --tiempo-fijo  # Semáforo a tiempos fijos (sin difuso).
python main.py --modo sim_prog --segundos 90  # Sin ventana: métricas en texto, 90 s.
python main.py --modo sim_prog --escenario pico --segundos 120  # Mismo modo con otro tráfico y duración.
python main.py --modo entrenar  # Entrena GA y guarda mejor_cromosoma.json + gráfica de fitness.
python main.py --modo entrenar_banco  # Entrena banco de cromosomas (un cromosoma por contexto).
python main.py --modo comparar  # Comparación multisemilla + gráficas en graficas/.
python main.py --modo comparar --segundos 180 --escenario bajo  # Comparar con duración y escenario explícitos.
python main.py --modo comparar_completo  # Tres estrategias (fijo / difuso / difuso+GA) y gráfica de costes.
python main.py --help  # Lista completa de argumentos.
```

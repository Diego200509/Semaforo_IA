"""
Modelo de intersección: varios carriles, tipos de vehículo, fase adaptativa (Fase 2).
Los giros se omiten si `config.VEHICULOS_SOLO_RECTO` es True.
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import config
from simulacion.carriles import (
    CARRIL_PRINCIPAL_RECTO,
    carril_para_maniobra,
    elegir_carril_aleatorio,
    offset_spawn_lateral,
)
from simulacion.politica_fase import siguiente_grupo_es_ns
from simulacion.semaforo import FaseSemaforo, Semaforo
from simulacion.tipos_trafico import TipoVehiculo, especificacion
from simulacion.vehiculo import (
    DireccionMovimiento,
    Maniobra,
    Vehiculo,
    direccion_salida_cruce,
)

if TYPE_CHECKING:
    from simulacion.escenarios import ControlGeneracionTrafico, PerfilGeneracion


def _vehiculos_solo_recto() -> bool:
    return bool(getattr(config, "VEHICULOS_SOLO_RECTO", True))


class Interseccion:
    def __init__(
        self,
        semilla: int | None = None,
        control_trafico: Optional["ControlGeneracionTrafico"] = None,
        verbose_escenario: bool = False,
        fase_adaptativa: bool | None = None,
    ) -> None:
        self.centro_x = config.ANCHO_VENTANA // 2
        self.centro_y = config.ALTO_VENTANA // 2
        self._fase_adaptativa_deseada: bool = (
            bool(config.USA_FASE_ADAPTATIVA) if fase_adaptativa is None else bool(fase_adaptativa)
        )
        self.semaforo = Semaforo()
        self._modo_tiempo_fijo_activo: bool = True
        self.semaforo.configurar_modo(self._modo_tiempo_fijo_activo)
        self.semaforo.configurar_fase_adaptativa(
            self._fase_adaptativa_deseada and not self._modo_tiempo_fijo_activo
        )
        self.vehiculos: List[Vehiculo] = []
        self._siguiente_id = 1
        self._acum_spawn = 0.0
        self._rng = random.Random(semilla)

        self._control_trafico = control_trafico
        self._verbose_escenario = verbose_escenario

        self.suma_tiempos_espera_muestras = 0.0
        self.muestras_espera = 0
        self.suma_longitud_cola_muestras = 0.0
        self.muestras_cola = 0
        self.vehiculos_atendidos = 0
        self.tiempo_simulado = 0.0

        self.max_tiempo_espera_observado = 0.0
        self.suma_vehiculos_detenidos_muestras = 0.0
        self.muestras_detenidos = 0

        self._intervalo_spawn = float(config.INTERVALO_SPAWN_BASE)
        self._mitad_via = float(getattr(config, "MITAD_ANCHO_VIA", 55.0))
        self._prob_intento_spawn = 0.92
        self._dirs_spawn: List[DireccionMovimiento] = list(DireccionMovimiento)
        self._pesos_spawn: List[float] = [0.25, 0.25, 0.25, 0.25]

        self._historial_segmentos: List[Dict[str, Any]] = []
        self._seg_etiqueta: str = ""
        self._seg_t0: float = 0.0
        self._seg_suma_espera = 0.0
        self._seg_muestras_espera = 0
        self._seg_suma_cola = 0.0
        self._seg_muestras_cola = 0
        self._seg_atendidos = 0
        # Snapshot usado por el difuso al arrancar un verde: conserva la cola previa al cambio.
        self._cola_snapshot_preverde_ns: float | None = None
        self._cola_snapshot_preverde_ew: float | None = None

    def reiniciar(self, semilla: int | None = None) -> None:
        if semilla is not None:
            self._rng = random.Random(semilla)
        self.vehiculos.clear()
        self._siguiente_id = 1
        self._acum_spawn = 0.0
        self.semaforo = Semaforo()
        self.semaforo.configurar_modo(self._modo_tiempo_fijo_activo)
        self.semaforo.configurar_fase_adaptativa(
            self._fase_adaptativa_deseada and not self._modo_tiempo_fijo_activo
        )
        self.suma_tiempos_espera_muestras = 0.0
        self.muestras_espera = 0
        self.suma_longitud_cola_muestras = 0.0
        self.muestras_cola = 0
        self.vehiculos_atendidos = 0
        self.tiempo_simulado = 0.0
        self.max_tiempo_espera_observado = 0.0
        self.suma_vehiculos_detenidos_muestras = 0.0
        self.muestras_detenidos = 0
        self._historial_segmentos = []
        self._seg_etiqueta = ""
        self._seg_t0 = 0.0
        self._seg_suma_espera = 0.0
        self._seg_muestras_espera = 0
        self._seg_suma_cola = 0.0
        self._seg_muestras_cola = 0
        self._seg_atendidos = 0
        self._cola_snapshot_preverde_ns = None
        self._cola_snapshot_preverde_ew = None
        if self._control_trafico is not None:
            self._control_trafico.reiniciar()

    def configurar_fase_adaptativa(self, activo: bool) -> None:
        self._fase_adaptativa_deseada = bool(activo)
        self.semaforo.configurar_fase_adaptativa(
            self._fase_adaptativa_deseada and not self._modo_tiempo_fijo_activo
        )

    def configurar_modo_tiempo_fijo(self, activo: bool) -> None:
        self._modo_tiempo_fijo_activo = bool(activo)
        self.semaforo.configurar_modo(self._modo_tiempo_fijo_activo)
        self.semaforo.configurar_fase_adaptativa(
            self._fase_adaptativa_deseada and not self._modo_tiempo_fijo_activo
        )

    def aplicar_perfil_generacion(self, perfil: "PerfilGeneracion") -> None:
        self._intervalo_spawn = perfil.intervalo_spawn_efectivo()
        self._prob_intento_spawn = float(perfil.prob_intento)
        dirs = list(DireccionMovimiento)
        raw = [max(0.0, float(perfil.pesos_direccion.get(d, 0.0))) for d in dirs]
        s = sum(raw) or 1.0
        self._dirs_spawn = dirs
        self._pesos_spawn = [w / s for w in raw]

    def _callback_cambio_trafico(self, anterior: str, nuevo: str, t: float) -> None:
        if self._verbose_escenario and self._control_trafico is not None:
            if self._control_trafico.nombre_escenario == "mixto":
                print(f"[t={t:.2f} s] Escenario de tráfico -> {nuevo}")
        if anterior:
            self._volcar_segmento(anterior, self._seg_t0, t)
        self._seg_etiqueta = nuevo
        self._seg_t0 = t
        self._seg_suma_espera = 0.0
        self._seg_muestras_espera = 0
        self._seg_suma_cola = 0.0
        self._seg_muestras_cola = 0
        self._seg_atendidos = 0

    def _volcar_segmento(self, nombre: str, t0: float, t1: float) -> None:
        esp = self._seg_suma_espera / self._seg_muestras_espera if self._seg_muestras_espera else 0.0
        col = self._seg_suma_cola / self._seg_muestras_cola if self._seg_muestras_cola else 0.0
        self._historial_segmentos.append(
            {
                "nombre": nombre,
                "t_inicio": t0,
                "t_fin": t1,
                "duracion": max(0.0, t1 - t0),
                "espera_promedio_muestras": esp,
                "cola_promedio_muestras": col,
                "vehiculos_atendidos": self._seg_atendidos,
            }
        )

    def _finalizar_ultimo_segmento_si_mixto(self) -> None:
        if self._control_trafico is None or self._control_trafico.nombre_escenario != "mixto":
            return
        if self._seg_etiqueta and self.tiempo_simulado > self._seg_t0:
            self._volcar_segmento(self._seg_etiqueta, self._seg_t0, self.tiempo_simulado)

    def _linea_parada(self, direccion: DireccionMovimiento) -> Tuple[float, float]:
        d = float(config.DISTANCIA_PARADA_ANTE_SEMAFORO)
        if direccion == DireccionMovimiento.HACIA_SUR:
            return float(self.centro_x), float(self.centro_y - d)
        if direccion == DireccionMovimiento.HACIA_NORTE:
            return float(self.centro_x), float(self.centro_y + d)
        if direccion == DireccionMovimiento.HACIA_ESTE:
            return float(self.centro_x - d), float(self.centro_y)
        return float(self.centro_x + d), float(self.centro_y)

    def _cruzo_linea_parada_hacia_centro(self, v: Vehiculo) -> bool:
        px, py = self._linea_parada(v.direccion)
        if v.direccion == DireccionMovimiento.HACIA_SUR:
            return v.y > py
        if v.direccion == DireccionMovimiento.HACIA_NORTE:
            return v.y < py
        if v.direccion == DireccionMovimiento.HACIA_ESTE:
            return v.x > px
        return v.x < px

    def _direccion_movimiento_efectiva(self, v: Vehiculo) -> DireccionMovimiento:
        if _vehiculos_solo_recto():
            return v.direccion
        if v.direccion_movimiento is not None:
            return v.direccion_movimiento
        return v.direccion

    def _umbral_distancia_inicio_giro(self, v: Vehiculo) -> float:
        """Mayor factor_despeje → comienza el giro antes (más radio de maniobra)."""
        return float(config.UMBRAL_INICIO_GIRO_CRUCE) * float(especificacion(v.tipo).factor_despeje)

    def _en_zona_cruce_interior(self, v: Vehiculo) -> bool:
        return self._distancia_al_centro(v) < float(config.RADIO_ZONA_CRUCE_INTERIOR)

    def _intentar_iniciar_giro(self, v: Vehiculo) -> None:
        if _vehiculos_solo_recto():
            return
        if v.maniobra == Maniobra.RECTO:
            return
        if not v.ingreso_cruce_autorizado or v.direccion_movimiento is not None:
            return
        if self._distancia_al_centro(v) >= self._umbral_distancia_inicio_giro(v):
            return
        v.direccion_movimiento = direccion_salida_cruce(v.direccion, v.maniobra)
        v.carril = CARRIL_PRINCIPAL_RECTO

    def _ha_completado_cruce(self, v: Vehiculo) -> bool:
        m = float(getattr(config, "MARGEN_RETIRO_VENTANA", config.MARGEN_BORDE_VEHICULO))
        d = self._direccion_movimiento_efectiva(v)
        if d == DireccionMovimiento.HACIA_SUR:
            return v.y >= float(config.ALTO_VENTANA) - m
        if d == DireccionMovimiento.HACIA_NORTE:
            return v.y <= m
        if d == DireccionMovimiento.HACIA_ESTE:
            return v.x >= float(config.ANCHO_VENTANA) - m
        return v.x <= m

    def _aplicar_tope_rojo(self, v: Vehiculo) -> None:
        if self._puede_pasar(v) or v.ingreso_cruce_autorizado:
            return
        px, py = self._linea_parada(v.direccion)
        if v.direccion == DireccionMovimiento.HACIA_SUR:
            if v.y > py:
                v.y = py
                v.velocidad = 0.0
        elif v.direccion == DireccionMovimiento.HACIA_NORTE:
            if v.y < py:
                v.y = py
                v.velocidad = 0.0
        elif v.direccion == DireccionMovimiento.HACIA_ESTE:
            if v.x > px:
                v.x = px
                v.velocidad = 0.0
        else:
            if v.x < px:
                v.x = px
                v.velocidad = 0.0

    def _elegir_tipo_spawn(self) -> TipoVehiculo:
        tipos = list(TipoVehiculo)
        w = tuple(config.PESOS_SPAWN_TIPO_VEHICULO)
        if len(w) != len(tipos):
            w = tuple(1.0 for _ in tipos)
        return self._rng.choices(tipos, weights=list(w), k=1)[0]

    def _elegir_maniobra_spawn(self) -> Maniobra:
        return self._rng.choices(
            [Maniobra.RECTO, Maniobra.IZQUIERDA, Maniobra.DERECHA],
            weights=[
                float(config.PROB_MANIOBRA_RECTO),
                float(config.PROB_MANIOBRA_IZQUIERDA),
                float(config.PROB_MANIOBRA_DERECHA),
            ],
            k=1,
        )[0]

    def _spawn_vehiculo(self) -> None:
        if len(self.vehiculos) >= config.MAX_VEHICULOS_EN_MAPA:
            return
        dire = self._rng.choices(self._dirs_spawn, weights=self._pesos_spawn, k=1)[0]
        margen = max(
            6,
            int(round(float(getattr(config, "MARGEN_SPAWN_VENTANA", 18.0)))),
        )
        if _vehiculos_solo_recto():
            maniobra = Maniobra.RECTO
            carril = elegir_carril_aleatorio(self._rng)
        else:
            maniobra = self._elegir_maniobra_spawn()
            carril = carril_para_maniobra(maniobra)
        lax, lay = offset_spawn_lateral(dire, carril)
        j = self._rng.uniform(-4.0, 4.0)
        if dire == DireccionMovimiento.HACIA_SUR:
            x, y = self.centro_x + lax, float(margen) + lay + j
        elif dire == DireccionMovimiento.HACIA_NORTE:
            x, y = self.centro_x + lax, float(config.ALTO_VENTANA - margen) + lay + j
        elif dire == DireccionMovimiento.HACIA_ESTE:
            x, y = float(margen) + lax + j, self.centro_y + lay
        else:
            x, y = float(config.ANCHO_VENTANA - margen) + lax + j, self.centro_y + lay

        v = Vehiculo(
            self._siguiente_id,
            x,
            y,
            dire,
            tipo=self._elegir_tipo_spawn(),
            maniobra=maniobra,
            carril=carril,
            direccion_movimiento=None,
        )
        self._siguiente_id += 1
        self.vehiculos.append(v)

    def _es_grupo_ns(self, direccion: DireccionMovimiento) -> bool:
        return direccion in (DireccionMovimiento.HACIA_SUR, DireccionMovimiento.HACIA_NORTE)

    def _puede_pasar(self, v: Vehiculo) -> bool:
        ns = self._es_grupo_ns(v.direccion)
        if ns:
            return self.semaforo.puede_avanzar_ns()
        return self.semaforo.puede_avanzar_ew()

    def _distancia_al_centro(self, v: Vehiculo) -> float:
        return math.hypot(v.x - self.centro_x, v.y - self.centro_y)

    def _progreso_en_linea(self, v: Vehiculo) -> float:
        """Proyección sobre el sentido de marcha; crece hacia el cruce."""
        fx, fy = self._vector_direccion(v)
        return (v.x - self.centro_x) * fx + (v.y - self.centro_y) * fy

    def _vector_direccion(self, v: Vehiculo) -> Tuple[float, float]:
        d = self._direccion_movimiento_efectiva(v)
        if d == DireccionMovimiento.HACIA_SUR:
            return 0.0, 1.0
        if d == DireccionMovimiento.HACIA_NORTE:
            return 0.0, -1.0
        if d == DireccionMovimiento.HACIA_ESTE:
            return 1.0, 0.0
        return -1.0, 0.0

    def direccion_movimiento_efectiva(self, v: Vehiculo) -> DireccionMovimiento:
        """Sentido de marcha efectivo (con giros solo si `VEHICULOS_SOLO_RECTO` es False)."""
        return self._direccion_movimiento_efectiva(v)

    def vector_movimiento_unitario(self, v: Vehiculo) -> Tuple[float, float]:
        """Vector unitario (dx, dy) del movimiento efectivo, mismo criterio que la simulación."""
        return self._vector_direccion(v)

    def _direccion_para_guiado(self, v: Vehiculo) -> DireccionMovimiento:
        return v.direccion_movimiento if v.direccion_movimiento is not None else v.direccion

    def _carril_para_guiado(self, v: Vehiculo) -> int:
        if v.direccion_movimiento is not None:
            return CARRIL_PRINCIPAL_RECTO
        return v.carril

    def _punto_en_cruz(self, x: float, y: float) -> bool:
        h = self._mitad_via
        cx, cy = self.centro_x, self.centro_y
        return abs(x - cx) <= h or abs(y - cy) <= h

    def _clamp_a_cruz(self, v: Vehiculo) -> None:
        m = 6.0
        if self._punto_en_cruz(v.x, v.y):
            return
        cx, cy, h = self.centro_x, self.centro_y, self._mitad_via
        candidates: List[Tuple[float, float]] = []
        if abs(v.x - cx) <= h:
            candidates.append((v.x, max(cy - h + m, min(cy + h - m, v.y))))
        if abs(v.y - cy) <= h:
            candidates.append((max(cx - h + m, min(cx + h - m, v.x)), v.y))
        if candidates:
            best = min(candidates, key=lambda p: (p[0] - v.x) ** 2 + (p[1] - v.y) ** 2)
            v.x, v.y = best
        else:
            v.x = max(cx - h + m, min(cx + h - m, v.x))
            v.y = max(cy - h + m, min(cy + h - m, v.y))

    def _alinear_carril(self, v: Vehiculo, dt: float) -> None:
        d = self._direccion_para_guiado(v)
        c = self._carril_para_guiado(v)
        ox, oy = offset_spawn_lateral(d, c)
        cx, cy = self.centro_x, self.centro_y
        k = min(1.0, 10.0 * dt)
        tx, ty = cx + ox, cy + oy
        if d in (DireccionMovimiento.HACIA_SUR, DireccionMovimiento.HACIA_NORTE):
            v.x += k * (tx - v.x)
        else:
            v.y += k * (ty - v.y)

    def _mismo_corredor_efectivo(self, a: Vehiculo, b: Vehiculo) -> bool:
        """Misma marcha efectiva (SUR/NORTE/ESTE/OESTE) y misma banda lateral.

        Eje lateral: X para flujos norte–sur, Y para flujos este–oeste (misma regla en los cuatro sentidos).
        """
        if self._direccion_movimiento_efectiva(a) != self._direccion_movimiento_efectiva(b):
            return False
        tol = float(getattr(config, "TOLERANCIA_MISMO_CORREDOR_PX", 12.0))
        d = self._direccion_movimiento_efectiva(a)
        if d in (DireccionMovimiento.HACIA_SUR, DireccionMovimiento.HACIA_NORTE):
            return abs(a.x - b.x) < tol
        return abs(a.y - b.y) < tol

    def _vehiculo_delante_misma_aproximacion(self, v: Vehiculo) -> Vehiculo | None:
        """Líder inmediato en el mismo corredor virtual (todos los sentidos y también en giro)."""
        pv = self._progreso_en_linea(v)
        candidatos: List[Vehiculo] = []
        for otro in self.vehiculos:
            if otro is v or otro.cruzo:
                continue
            if not self._mismo_corredor_efectivo(v, otro):
                continue
            po = self._progreso_en_linea(otro)
            if po > pv + 1e-3:
                candidatos.append(otro)
        if not candidatos:
            return None
        return min(candidatos, key=lambda o: self._progreso_en_linea(o))

    def _aplicar_separacion_colas(self) -> None:
        """Separa colas en todos los corredores (N-S y E-O): acerca al detrás hacia la distancia mínima."""
        beta = float(getattr(config, "SEPARACION_COLA_SUAVIDAD", 0.48))
        beta = max(0.15, min(1.0, beta))
        for _ in range(5):
            activos = [v for v in self.vehiculos if not v.cruzo]
            for v in sorted(activos, key=lambda x: self._progreso_en_linea(x)):
                delante = self._vehiculo_delante_misma_aproximacion(v)
                if delante is None:
                    continue
                sep = v.separacion_respecto(delante)
                dx = v.x - delante.x
                dy = v.y - delante.y
                dist = math.hypot(dx, dy)
                if dist >= sep:
                    continue
                if dist < 1e-6:
                    fx, fy = self._vector_direccion(v)
                    tx = delante.x - fx * sep
                    ty = delante.y - fy * sep
                else:
                    f = sep / dist
                    tx = delante.x + dx * f
                    ty = delante.y + dy * f
                v.x += beta * (tx - v.x)
                v.y += beta * (ty - v.y)
                self._clamp_a_cruz(v)

    def _refinar_separacion_longitudinal(self) -> None:
        """Corrige solapes residuales en cola en cualquier sentido (empuje solo al de atrás, hacia el líder)."""
        cap = float(getattr(config, "SEPARACION_REFUERZO_LONG_MAX_PX", 5.5))
        for _ in range(4):
            activos = [v for v in self.vehiculos if not v.cruzo]
            for v in sorted(activos, key=lambda x: self._progreso_en_linea(x)):
                delante = self._vehiculo_delante_misma_aproximacion(v)
                if delante is None:
                    continue
                sep = v.separacion_respecto(delante)
                dx = v.x - delante.x
                dy = v.y - delante.y
                dist = math.hypot(dx, dy)
                if dist >= sep - 0.35 or dist < 1e-9:
                    continue
                ux, uy = dx / dist, dy / dist
                falta = sep - dist
                step = min(falta + 0.25, cap)
                v.x += ux * step
                v.y += uy * step
                self._clamp_a_cruz(v)

    def _separar_solapes_en_cruce(self) -> None:
        """Zona del cruce: separa solo pares de corredores distintos (cualquier cruce de trayectorias)."""
        r = float(config.RADIO_ZONA_CRUCE_INTERIOR) * 1.4
        activos = [v for v in self.vehiculos if not v.cruzo and self._distancia_al_centro(v) < r]
        for _ in range(4):
            for i, a in enumerate(activos):
                for b in activos[i + 1 :]:
                    if self._mismo_corredor_efectivo(a, b):
                        continue
                    sep = 0.5 * (a.separacion_respecto(b) + b.separacion_respecto(a))
                    dx = b.x - a.x
                    dy = b.y - a.y
                    dist = math.hypot(dx, dy)
                    if dist >= sep or dist < 1e-9:
                        continue
                    push = 0.45 * (sep - dist) / 2.0
                    ux, uy = dx / dist, dy / dist
                    a.x -= ux * push
                    a.y -= uy * push
                    b.x += ux * push
                    b.y += uy * push
                    self._clamp_a_cruz(a)
                    self._clamp_a_cruz(b)

    def _vehiculo_aporta_a_cola(self, v: Vehiculo) -> bool:
        """La cola ya no depende del color: cuenta vehículos detenidos o casi detenidos."""
        return bool(v.detenido or v.velocidad < 15.0)

    def _proximo_verde_es_ns(self) -> bool | None:
        """
        Determina qué eje recibirá el siguiente verde usando el estado ya programado del semáforo.
        """
        if self.semaforo.fase == FaseSemaforo.AMARILLO_NS:
            if self.semaforo.fase_adaptativa_activa and self.semaforo._siguiente_verde_ns is not None:
                return bool(self.semaforo._siguiente_verde_ns)
            return False
        if self.semaforo.fase == FaseSemaforo.AMARILLO_EW:
            if self.semaforo.fase_adaptativa_activa and self.semaforo._siguiente_verde_ns is not None:
                return bool(self.semaforo._siguiente_verde_ns)
            return True
        return None

    def _capturar_snapshot_cola_preverde(self) -> None:
        """
        Guarda la cola del eje que va a recibir verde justo antes del cambio de fase.
        """
        proximo_ns = self._proximo_verde_es_ns()
        if proximo_ns is None:
            return
        activos = [v for v in self.vehiculos if not v.cruzo]
        cola_ns, cola_ew, _, _ = self._esperas_y_colas_por_eje(activos)
        if proximo_ns:
            self._cola_snapshot_preverde_ns = float(cola_ns)
        else:
            self._cola_snapshot_preverde_ew = float(cola_ew)

    def _esperas_y_colas_por_eje(self, activos: List[Vehiculo]) -> tuple[int, int, float, float]:
        cola_ns = sum(
            1
            for v in activos
            if self._es_grupo_ns(v.direccion) and self._vehiculo_aporta_a_cola(v)
        )
        cola_ew = sum(
            1
            for v in activos
            if not self._es_grupo_ns(v.direccion) and self._vehiculo_aporta_a_cola(v)
        )
        ns_t = [
            v.tiempo_espera
            for v in activos
            if self._es_grupo_ns(v.direccion) and self._vehiculo_aporta_a_cola(v)
        ]
        ew_t = [
            v.tiempo_espera
            for v in activos
            if not self._es_grupo_ns(v.direccion) and self._vehiculo_aporta_a_cola(v)
        ]
        ens = float(sum(ns_t) / len(ns_t)) if ns_t else 0.0
        eew = float(sum(ew_t) / len(ew_t)) if ew_t else 0.0
        return cola_ns, cola_ew, ens, eew

    def _estado_para_politica_fase(self) -> Dict[str, float | bool]:
        activos = [v for v in self.vehiculos if not v.cruzo]
        cns, cew, ens, eew = self._esperas_y_colas_por_eje(activos)
        return {
            "cola_ns": float(cns),
            "cola_ew": float(cew),
            "espera_promedio_ns": float(ens),
            "espera_promedio_ew": float(eew),
            "ultimo_verde_fue_ns": bool(self.semaforo.ultimo_verde_fue_ns),
        }

    def actualizar(self, dt: float) -> None:
        self.tiempo_simulado += dt

        if self._control_trafico is not None:
            perfil = self._control_trafico.sincronizar(self.tiempo_simulado, self._callback_cambio_trafico)
            self.aplicar_perfil_generacion(perfil)

        if self.semaforo.fase_adaptativa_activa and self.semaforo.fase in (
            FaseSemaforo.AMARILLO_NS,
            FaseSemaforo.AMARILLO_EW,
        ):
            self.semaforo.programar_siguiente_verde_ns(
                siguiente_grupo_es_ns(self._estado_para_politica_fase())
            )
        if self.semaforo.fase in (FaseSemaforo.AMARILLO_NS, FaseSemaforo.AMARILLO_EW):
            tiempo_restante = float(config.DURACION_AMARILLO) - float(self.semaforo.tiempo_en_fase)
            # El snapshot conserva la cola previa al verde para que el difuso vea la demanda real.
            if tiempo_restante <= dt + 1e-9:
                self._capturar_snapshot_cola_preverde()

        self.semaforo.actualizar(dt)

        self._acum_spawn += dt
        jitter = self._rng.uniform(0.75, 1.35) * self._intervalo_spawn
        if self._acum_spawn >= jitter:
            self._acum_spawn = 0.0
            if self._rng.random() < self._prob_intento_spawn:
                self._spawn_vehiculo()

        self.vehiculos.sort(key=self._distancia_al_centro)

        for v in self.vehiculos:
            if v.cruzo:
                continue

            if self._ha_completado_cruce(v):
                v.cruzo = True
                self.vehiculos_atendidos += 1
                self._seg_atendidos += 1
                continue

            delante = self._vehiculo_delante_misma_aproximacion(v)
            objetivo_vel = v.velocidad_libre_objetivo(config.VELOCIDAD_BASE)

            if delante is not None:
                separacion = v.separacion_respecto(delante)
                dist = math.hypot(v.x - delante.x, v.y - delante.y)
                if dist < separacion:
                    objetivo_vel = 0.0
                elif dist < separacion + 14.0:
                    objetivo_vel = min(objetivo_vel, max(0.0, (dist - separacion) * 5.2))
                elif dist < separacion * 1.72:
                    objetivo_vel = min(objetivo_vel, delante.velocidad)

            if self._puede_pasar(v) and self._cruzo_linea_parada_hacia_centro(v):
                v.ingreso_cruce_autorizado = True

            self._intentar_iniciar_giro(v)

            px, py = self._linea_parada(v.direccion)
            dist_a_parada = math.hypot(v.x - px, v.y - py)
            if not self._puede_pasar(v):
                if v.ingreso_cruce_autorizado:
                    objetivo_vel = config.VELOCIDAD_BASE
                elif not self._cruzo_linea_parada_hacia_centro(v):
                    if dist_a_parada > 8.0:
                        if dist_a_parada < 55.0:
                            objetivo_vel = min(objetivo_vel, max(0.0, dist_a_parada - 10.0) * 2.0)
                    else:
                        objetivo_vel = 0.0
                else:
                    objetivo_vel = 0.0

            # Tiempo de despeje: en el cruce, velocidad máxima acotada por tipo (bus/camión más lentos).
            if v.ingreso_cruce_autorizado and self._en_zona_cruce_interior(v):
                cap = v.velocidad_libre_objetivo(config.VELOCIDAD_BASE) / max(0.5, v.factor_despeje())
                objetivo_vel = min(objetivo_vel, cap)

            alpha = min(1.0, 5.0 * dt)
            v.velocidad += alpha * (objetivo_vel - v.velocidad)
            dx, dy = self._vector_direccion(v)
            v.x += dx * v.velocidad * dt
            v.y += dy * v.velocidad * dt
            self._aplicar_tope_rojo(v)
            self._alinear_carril(v, dt)
            self._clamp_a_cruz(v)
            v.detenido = v.velocidad < 1.0
            v.actualizar_espera(dt)

        # Cadena común para los cuatro brazos: cola suave → refuerzo longitudinal → cruces → refuerzo otra vez
        self._aplicar_separacion_colas()
        self._refinar_separacion_longitudinal()
        self._separar_solapes_en_cruce()
        self._refinar_separacion_longitudinal()

        self.vehiculos = [v for v in self.vehiculos if not v.cruzo]

        estado = self.obtener_estado_trafico()
        self.suma_tiempos_espera_muestras += estado["tiempo_espera_promedio"]
        self.muestras_espera += 1
        self.suma_longitud_cola_muestras += estado["longitud_cola"]
        self.muestras_cola += 1

        activos = [v for v in self.vehiculos if not v.cruzo]
        if activos:
            self.max_tiempo_espera_observado = max(
                self.max_tiempo_espera_observado,
                max(v.tiempo_espera for v in activos),
            )
        n_det = sum(1 for v in activos if v.detenido)
        self.suma_vehiculos_detenidos_muestras += float(n_det)
        self.muestras_detenidos += 1

        if self._control_trafico is not None and self._control_trafico.nombre_escenario == "mixto":
            self._seg_suma_espera += estado["tiempo_espera_promedio"]
            self._seg_muestras_espera += 1
            self._seg_suma_cola += estado["longitud_cola"]
            self._seg_muestras_cola += 1

    def obtener_estado_trafico(self) -> dict:
        activos = [v for v in self.vehiculos if not v.cruzo]
        n = len(activos)
        densidad = min(1.0, n / max(1e-6, float(config.CAPACIDAD_REFERENCIA_VEHICULOS)))
        suma_peso = sum(v.peso_congestion_efectivo() for v in activos)
        densidad_ponderada = min(
            1.0,
            suma_peso / max(1e-6, float(config.CAPACIDAD_REFERENCIA_VEHICULOS)),
        )

        cola_ns, cola_ew, espera_ns, espera_ew = self._esperas_y_colas_por_eje(activos)
        longitud_cola = float(max(cola_ns, cola_ew))

        esperas = [v.tiempo_espera for v in activos if v.detenido or v.velocidad < 15]
        tiempo_espera_promedio = float(sum(esperas) / len(esperas)) if esperas else 0.0

        return {
            "densidad_vehicular": float(densidad),
            "densidad_ponderada": float(densidad_ponderada),
            "tiempo_espera_promedio": tiempo_espera_promedio,
            "longitud_cola": longitud_cola,
            "cola_ns": float(cola_ns),
            "cola_ew": float(cola_ew),
            # Snapshot de demanda justo antes de entrar al verde; el callback difuso lo usa si existe.
            "cola_ns_preverde": (
                float(self._cola_snapshot_preverde_ns)
                if self._cola_snapshot_preverde_ns is not None
                else None
            ),
            "cola_ew_preverde": (
                float(self._cola_snapshot_preverde_ew)
                if self._cola_snapshot_preverde_ew is not None
                else None
            ),
            "espera_ns": float(espera_ns),
            "espera_ew": float(espera_ew),
            "fase": self.semaforo.fase,
            "vehiculos_en_mapa": n,
            "ultimo_verde_fue_ns": bool(self.semaforo.ultimo_verde_fue_ns),
        }

    def obtener_metricas(self) -> dict:
        self._finalizar_ultimo_segmento_si_mixto()
        prom_espera = (
            self.suma_tiempos_espera_muestras / self.muestras_espera if self.muestras_espera else 0.0
        )
        prom_cola = (
            self.suma_longitud_cola_muestras / self.muestras_cola if self.muestras_cola else 0.0
        )
        prom_det = (
            self.suma_vehiculos_detenidos_muestras / self.muestras_detenidos
            if self.muestras_detenidos
            else 0.0
        )
        t_sim = max(1e-9, self.tiempo_simulado)
        throughput = float(self.vehiculos_atendidos) / t_sim
        m = {
            "tiempo_espera_promedio_muestras": prom_espera,
            "longitud_cola_promedio_muestras": prom_cola,
            "vehiculos_atendidos": float(self.vehiculos_atendidos),
            "tiempo_simulado": self.tiempo_simulado,
            "tiempo_espera_maximo": float(self.max_tiempo_espera_observado),
            "vehiculos_detenidos_promedio_muestras": prom_det,
            "throughput": throughput,
        }
        if self._historial_segmentos:
            m["segmentos_mixto"] = list(self._historial_segmentos)
        return m

"""
Interfaz abstracta del motor de simulación y dos implementaciones:

- `MotorSimulacionProgramatico`: sin gráficos, ideal para entrenar el GA o pruebas rápidas.
- `MotorSimulacionPygame`: misma lógica con visualización 2D.

Pygame se importa de forma perezosa solo al usar `MotorSimulacionPygame`, de modo que el GA
y la simulación por consola funcionen aunque Pygame no esté instalado en el entorno.

Un futuro adaptador SUMO implementaría la misma interfaz sin tocar difuso/genético/evaluación.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

import config
from simulacion.escenarios import crear_control_generacion
from simulacion.interseccion import Interseccion
from simulacion.semaforo import FaseSemaforo
from simulacion.vehiculo import DireccionMovimiento


def _import_pygame():
    try:
        import pygame
    except ImportError as exc:
        raise ImportError(
            "Se requiere Pygame para el modo visual. "
            "Instálalo con: python -m pip install pygame-ce  (o pygame en Python <= 3.12)"
        ) from exc
    return pygame


class MotorSimulacion(ABC):
    """Contrato que debe cumplir cualquier motor (local, Pygame, SUMO, etc.)."""

    @abstractmethod
    def obtener_estado_trafico(self) -> dict:
        """Retorna entradas crudas para el sistema difuso y depuración."""

    @abstractmethod
    def aplicar_tiempo_verde(self, segundos: float) -> None:
        """Fija la duración del verde del grupo que actualmente tiene luz verde (o el próximo)."""

    @abstractmethod
    def actualizar(self, dt: float) -> None:
        """Avanza el mundo simulado `dt` segundos."""

    @abstractmethod
    def reiniciar(self, semilla: int | None = None) -> None:
        """Reinicia escenario y métricas acumuladas."""

    @abstractmethod
    def obtener_metricas(self) -> dict:
        """Métricas agregadas para fitness y comparación."""


class MotorSimulacionProgramatico(MotorSimulacion):
    """
    Simulación basada en `Interseccion` sin renderizado.
    Opcionalmente invoca un callback para fijar el verde con lógica difusa.
    """

    def __init__(
        self,
        semilla: int | None = None,
        modo_tiempo_fijo: bool = False,
        callback_tiempo_verde: Optional[Callable[[dict], float]] = None,
        escenario: str | None = None,
        duracion_planeada: float | None = None,
        verbose_escenario: bool = False,
        fase_adaptativa: bool | None = None,
    ) -> None:
        esc = (escenario or config.ESCENARIO_POR_DEFECTO).strip().lower()
        if duracion_planeada is not None:
            dur = float(duracion_planeada)
        elif esc == "mixto":
            dur = float(config.DURACION_PLAN_VISUAL_MIXTO)
        else:
            dur = float(config.DURACION_REFERENCIA_MIXTO)
        control = crear_control_generacion(esc, dur)
        self.interseccion = Interseccion(
            semilla=semilla,
            control_trafico=control,
            verbose_escenario=verbose_escenario,
            fase_adaptativa=fase_adaptativa,
        )
        self.interseccion.configurar_modo_tiempo_fijo(modo_tiempo_fijo)
        self._callback = callback_tiempo_verde
        # Evita recalcular el verde varias veces dentro de la misma fase verde.
        self._fase_en_que_se_fijo_verde: FaseSemaforo | None = None

    def reiniciar(self, semilla: int | None = None) -> None:
        """Reinicia el escenario; `semilla` controla la aleatoriedad del tráfico."""
        self.interseccion.reiniciar(semilla=semilla)
        self._fase_en_que_se_fijo_verde = None

    def obtener_estado_trafico(self) -> dict:
        return self.interseccion.obtener_estado_trafico()

    def aplicar_tiempo_verde(self, segundos: float) -> None:
        self.interseccion.semaforo.aplicar_tiempo_verde(segundos)

    def obtener_metricas(self) -> dict:
        return self.interseccion.obtener_metricas()

    def actualizar(self, dt: float) -> None:
        """Avanza la intersección y ajusta el verde una sola vez al entrar en cada fase verde."""
        self.interseccion.actualizar(dt)
        sem = self.interseccion.semaforo
        if self._callback is None or sem.modo_tiempo_fijo:
            return
        if sem.fase not in (FaseSemaforo.VERDE_NS, FaseSemaforo.VERDE_EW):
            self._fase_en_que_se_fijo_verde = None
            return
        if self._fase_en_que_se_fijo_verde == sem.fase:
            return
        estado = self.obtener_estado_trafico()
        try:
            t = float(self._callback(estado))
        except Exception:
            t = float(config.VERDE_FIJO_NS)
        self.aplicar_tiempo_verde(t)
        self._fase_en_que_se_fijo_verde = sem.fase


class MotorSimulacionPygame(MotorSimulacionProgramatico):
    """Motor con ventana Pygame; reutiliza la lógica del motor programático."""

    def __init__(
        self,
        semilla: int | None = None,
        modo_tiempo_fijo: bool = False,
        callback_tiempo_verde: Optional[Callable[[dict], float]] = None,
        escenario: str | None = None,
        duracion_planeada: float | None = None,
        verbose_escenario: bool = False,
        fase_adaptativa: bool | None = None,
    ) -> None:
        super().__init__(
            semilla=semilla,
            modo_tiempo_fijo=modo_tiempo_fijo,
            callback_tiempo_verde=callback_tiempo_verde,
            escenario=escenario,
            duracion_planeada=duracion_planeada,
            verbose_escenario=verbose_escenario,
            fase_adaptativa=fase_adaptativa,
        )
        self._pg = _import_pygame()
        self._pg.init()
        self._pg.display.set_caption(config.TITULO_VENTANA)
        self._pantalla = self._pg.display.set_mode((config.ANCHO_VENTANA, config.ALTO_VENTANA))
        self._reloj = self._pg.time.Clock()
        self._fuente = self._pg.font.SysFont("segoeui", 18)
        self._fondo_cache: Any = self._cargar_fondo_opcional()

    def _cargar_fondo_opcional(self) -> Any:
        """Si existe una imagen en assets/fondos, úsala; si no, fondo plano."""
        if not config.CARPETA_FONDOS.is_dir():
            return None
        candidatos = sorted(config.CARPETA_FONDOS.glob("*.png")) + sorted(
            config.CARPETA_FONDOS.glob("*.jpg")
        )
        if not candidatos:
            return None
        try:
            img = self._pg.image.load(str(candidatos[0])).convert()
            return self._pg.transform.scale(img, (config.ANCHO_VENTANA, config.ALTO_VENTANA))
        except self._pg.error:
            return None

    def _cargar_sprite_coche_opcional(self) -> Any:
        if not config.CARPETA_CARROS.is_dir():
            return None
        imgs = sorted(config.CARPETA_CARROS.glob("*.png"))
        if not imgs:
            return None
        try:
            return self._pg.image.load(str(imgs[0])).convert_alpha()
        except self._pg.error:
            return None

    def cerrar(self) -> None:
        self._pg.quit()

    def dibujar(self) -> None:
        """Dibuja calles, semáforos y vehículos."""
        pg = self._pg
        if self._fondo_cache:
            self._pantalla.blit(self._fondo_cache, (0, 0))
        else:
            self._pantalla.fill(config.COLOR_FONDO)

        cx, cy = self.interseccion.centro_x, self.interseccion.centro_y
        ancho_calle = 110
        largo = max(config.ANCHO_VENTANA, config.ALTO_VENTANA)

        pg.draw.rect(
            self._pantalla,
            config.COLOR_CALLE,
            (cx - ancho_calle // 2, 0, ancho_calle, largo),
        )
        pg.draw.rect(
            self._pantalla,
            config.COLOR_CALLE,
            (0, cy - ancho_calle // 2, largo, ancho_calle),
        )
        pg.draw.rect(
            self._pantalla,
            config.COLOR_CENTRO,
            (cx - ancho_calle // 2, cy - ancho_calle // 2, ancho_calle, ancho_calle),
        )

        self._dibujar_semaforos(cx, cy)
        sprite = self._cargar_sprite_coche_opcional()

        for v in self.interseccion.vehiculos:
            color = (
                config.COLOR_CARRO_NS
                if v.direccion
                in (DireccionMovimiento.HACIA_SUR, DireccionMovimiento.HACIA_NORTE)
                else config.COLOR_CARRO_EW
            )
            if sprite:
                r = sprite.get_rect(center=(int(v.x), int(v.y)))
                self._pantalla.blit(sprite, r)
            else:
                pg.draw.circle(self._pantalla, color, (int(v.x), int(v.y)), max(4, v.radio_dibujo()))

        estado = self.obtener_estado_trafico()
        m = self.obtener_metricas()
        lineas = [
            f"Densidad: {estado['densidad_vehicular']:.2f}",
            f"Espera prom.: {estado['tiempo_espera_promedio']:.1f} s",
            f"Cola max.: {estado['longitud_cola']:.0f}",
            f"Atendidos: {int(m['vehiculos_atendidos'])}",
            f"Fase NS: {self.interseccion.semaforo.fase_para_grupo_ns()} | EW: {self.interseccion.semaforo.fase_para_grupo_ew()}",
        ]
        y0 = 8
        for i, texto in enumerate(lineas):
            surf = self._fuente.render(texto, True, config.COLOR_TEXTO)
            self._pantalla.blit(surf, (10, y0 + i * 22))

        pg.display.flip()

    def _dibujar_semaforos(self, cx: int, cy: int) -> None:
        """Indicadores simples en cada esquina."""
        pg = self._pg
        sem = self.interseccion.semaforo

        def color_para(grupo_ns: bool) -> tuple:
            if grupo_ns:
                if sem.verde_ns():
                    return config.COLOR_SEMAFORO_VERDE
                if sem.fase == FaseSemaforo.AMARILLO_NS:
                    return config.COLOR_SEMAFORO_AMARILLO
            else:
                if sem.verde_ew():
                    return config.COLOR_SEMAFORO_VERDE
                if sem.fase == FaseSemaforo.AMARILLO_EW:
                    return config.COLOR_SEMAFORO_AMARILLO
            return config.COLOR_SEMAFORO_ROJO

        radio = 7
        offset = 78
        pos_ns = [(cx - offset, cy - offset), (cx + offset, cy + offset)]
        pos_ew = [(cx + offset, cy - offset), (cx - offset, cy + offset)]
        for px, py in pos_ns:
            pg.draw.circle(self._pantalla, color_para(True), (px, py), radio)
        for px, py in pos_ew:
            pg.draw.circle(self._pantalla, color_para(False), (px, py), radio)

    def ejecutar_bucle_visual(
        self,
        max_segundos: Optional[float] = None,
    ) -> None:
        """Bucle estándar Pygame hasta cerrar ventana o alcanzar límite de tiempo."""
        pg = self._pg
        ejecutando = True
        tiempo_total = 0.0
        while ejecutando:
            dt_ms = self._reloj.tick(config.FPS)
            dt = dt_ms / 1000.0
            tiempo_total += dt
            if max_segundos is not None and tiempo_total >= max_segundos:
                ejecutando = False

            for evento in pg.event.get():
                if evento.type == pg.QUIT:
                    ejecutando = False
                elif evento.type == pg.KEYDOWN and evento.key == pg.K_ESCAPE:
                    ejecutando = False

            self.actualizar(dt)
            self.dibujar()

        self.cerrar()

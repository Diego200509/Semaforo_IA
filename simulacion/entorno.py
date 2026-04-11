"""
Interfaz abstracta del motor de simulación y dos implementaciones:

- `MotorSimulacionProgramatico`: sin gráficos, ideal para entrenar el GA o pruebas rápidas.
- `MotorSimulacionPygame`: misma lógica con visualización 2D.

Pygame se importa de forma perezosa solo al usar `MotorSimulacionPygame`, de modo que el GA
y la simulación por consola funcionen aunque Pygame no esté instalado en el entorno.

Un futuro adaptador SUMO implementaría la misma interfaz sin tocar difuso/genético/evaluación.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple

import config
from simulacion.escenarios import crear_control_generacion
from simulacion.interseccion import Interseccion
from simulacion.semaforo import FaseSemaforo
from simulacion.tipos_trafico import TipoVehiculo, especificacion
from simulacion.vehiculo import DireccionMovimiento, Vehiculo


_NOMBRE_ARCHIVO_POR_TIPO: Dict[TipoVehiculo, str] = {
    TipoVehiculo.MOTO: "moto",
    TipoVehiculo.AUTO: "auto",
    TipoVehiculo.BUS: "bus",
    TipoVehiculo.CAMION: "camion",
}


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
        estado = dict(self.obtener_estado_trafico())
        estado["inferir_para_grupo_ns"] = sem.fase == FaseSemaforo.VERDE_NS
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
        self._fuente_metricas = self._crear_fuente_metricas()
        self._fondo_cache: Any = self._cargar_fondo_opcional()
        # Bases escaladas por tipo y variantes ya rotadas (clave: tipo, dirección efectiva).
        self._sprites_base_por_tipo: Dict[TipoVehiculo, Any] | None = None
        self._sprites_rotados_cache: Dict[Tuple[TipoVehiculo, DireccionMovimiento], Any] = {}

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

    def _crear_fuente_metricas(self) -> Any:
        """Fuente tipo pixel / monoespaciada y negrita para el HUD; legible sobre fondos claros."""
        pg = self._pg
        px = int(getattr(config, "HUD_METRICAS_FUENTE_PX", 17))
        nombres = getattr(
            config,
            "HUD_METRICAS_NOMBRES_FUENTE",
            ("Press Start 2P", "VT323", "Consolas", "Courier New"),
        )
        for nombre in nombres:
            ruta = pg.font.match_font(nombre, bold=True)
            if ruta:
                return pg.font.Font(ruta, px)
        return pg.font.SysFont(["Courier New", "Courier", "Consolas"], px, bold=True)

    def _tamano_caja_sprite_px(self, radio: int) -> int:
        """Encaja el arte en un cuadrado ~ proporcional al radio lógico del vehículo."""
        mult = float(getattr(config, "SPRITE_VEHICULO_MULT_RADIO", 4.35))
        lado_min = int(getattr(config, "SPRITE_VEHICULO_LADO_MIN", 34))
        return max(lado_min, int(round(mult * float(radio))))

    def _escalar_a_caja(self, surf: Any, lado: int) -> Any:
        w, h = surf.get_size()
        if w <= 0 or h <= 0:
            return surf
        escala = min(float(lado) / float(w), float(lado) / float(h))
        nw = max(1, int(round(w * escala)))
        nh = max(1, int(round(h * escala)))
        suave = bool(getattr(config, "SPRITE_VEHICULO_ESCALADO_SUAVE", False))
        if suave:
            return self._pg.transform.smoothscale(surf, (nw, nh))
        return self._pg.transform.scale(surf, (nw, nh))

    def _cargar_superficie_archivo(self, ruta: Any) -> Any | None:
        pg = self._pg
        try:
            if str(ruta).lower().endswith(".png"):
                return pg.image.load(str(ruta)).convert_alpha()
            return pg.image.load(str(ruta)).convert()
        except pg.error:
            return None

    def _asegurar_sprites_base_por_tipo(self) -> None:
        """Carga una vez `assets/carros/<tipo>.png` (o .jpg); si no hay por tipo, usa un único PNG genérico."""
        if self._sprites_base_por_tipo is not None:
            return
        self._sprites_base_por_tipo = {}
        self._sprites_rotados_cache.clear()
        carpeta = config.CARPETA_CARROS
        if not carpeta.is_dir():
            return
        bases: Dict[TipoVehiculo, Any] = {}
        for tipo, nombre in _NOMBRE_ARCHIVO_POR_TIPO.items():
            surf = None
            for ext in (".png", ".jpg", ".jpeg"):
                p = carpeta / f"{nombre}{ext}"
                if p.is_file():
                    surf = self._cargar_superficie_archivo(p)
                    if surf is not None:
                        break
            if surf is not None:
                lado = self._tamano_caja_sprite_px(especificacion(tipo).radio_px)
                bases[tipo] = self._escalar_a_caja(surf, lado)
        if bases:
            self._sprites_base_por_tipo = bases
            return
        gen = carpeta / "coche.png"
        if not gen.is_file():
            todas = sorted(carpeta.glob("*.png")) + sorted(carpeta.glob("*.jpg"))
            if not todas:
                return
            gen = todas[0]
        surf_gen = self._cargar_superficie_archivo(gen)
        if surf_gen is None:
            return
        for tipo in TipoVehiculo:
            lado = self._tamano_caja_sprite_px(especificacion(tipo).radio_px)
            self._sprites_base_por_tipo[tipo] = self._escalar_a_caja(surf_gen, lado)

    def _render_texto_metrica(self, texto: str, color: tuple, contorno: tuple, grosor: int) -> Any:
        """Texto con contorno claro (8 vecinos) para leerlo sobre cualquier fondo."""
        pg = self._pg
        g = max(1, int(grosor))
        fg = self._fuente_metricas.render(texto, False, color)
        w, h = fg.get_size()
        out = pg.Surface((w + 2 * g, h + 2 * g), pg.SRCALPHA)
        offsets = (
            (-g, 0),
            (g, 0),
            (0, -g),
            (0, g),
            (-g, -g),
            (g, -g),
            (-g, g),
            (g, g),
        )
        capa = self._fuente_metricas.render(texto, False, contorno)
        for dx, dy in offsets:
            out.blit(capa, (g + dx, g + dy))
        out.blit(fg, (g, g))
        return out

    def _dibujar_hud_metricas(self, lineas: list[str]) -> None:
        """Panel semitransparente + texto negro con contorno blanco."""
        pg = self._pg
        color_fg = tuple(getattr(config, "HUD_METRICAS_COLOR", (12, 12, 12)))
        contorno = tuple(getattr(config, "HUD_METRICAS_CONTORNO", (255, 255, 255)))
        grosor = int(getattr(config, "HUD_METRICAS_CONTORNO_GROSOR", 1))
        pad = int(getattr(config, "HUD_PANEL_PADDING", 10))
        line_gap = 4
        x0, y0 = 6, 6

        surfs = [self._render_texto_metrica(t, color_fg, contorno, grosor) for t in lineas]
        w = max((s.get_width() for s in surfs), default=0) + 2 * pad
        h = (
            2 * pad
            + sum(s.get_height() for s in surfs)
            + line_gap * max(0, len(surfs) - 1)
        )

        panel = pg.Surface((max(1, w), max(1, h)), pg.SRCALPHA)
        r, g, b = tuple(getattr(config, "HUD_PANEL_RELLENO", (255, 252, 245)))
        alpha = int(getattr(config, "HUD_PANEL_ALPHA", 242))
        alpha = max(0, min(255, alpha))
        panel.fill((r, g, b, alpha))
        borde = int(getattr(config, "HUD_PANEL_BORDE_PX", 2))
        color_borde = tuple(getattr(config, "HUD_PANEL_BORDE_COLOR", (0, 0, 0)))
        pg.draw.rect(panel, color_borde, panel.get_rect(), width=max(1, borde))

        yy = pad
        for s in surfs:
            panel.blit(s, (pad, yy))
            yy += s.get_height() + line_gap

        self._pantalla.blit(panel, (x0, y0))

    def _angulo_sprite_grados(self, dx: float, dy: float) -> float:
        """Asume el PNG con el morro hacia arriba (eje -Y pantalla); alinea con (dx, dy)."""
        return math.degrees(math.atan2(-dx, -dy))

    def _sprite_rotado(self, v: Vehiculo) -> Any | None:
        self._asegurar_sprites_base_por_tipo()
        if not self._sprites_base_por_tipo:
            return None
        base = self._sprites_base_por_tipo.get(v.tipo)
        if base is None:
            return None
        inter = self.interseccion
        d_eff = inter.direccion_movimiento_efectiva(v)
        clave = (v.tipo, d_eff)
        if clave in self._sprites_rotados_cache:
            return self._sprites_rotados_cache[clave]
        dx, dy = inter.vector_movimiento_unitario(v)
        ang = self._angulo_sprite_grados(dx, dy)
        rot = self._pg.transform.rotate(base, ang)
        self._sprites_rotados_cache[clave] = rot
        return rot

    def _linea_vertical_discontinua(
        self,
        x: int,
        y0: int,
        y1: int,
        color: tuple,
        grosor: int = 1,
        dash_px: int | None = None,
        gap_px: int | None = None,
    ) -> None:
        pg = self._pg
        surf = self._pantalla
        dash = max(
            3,
            int(
                dash_px
                if dash_px is not None
                else getattr(config, "MARCAS_VIALES_DASH_PX", 10)
            ),
        )
        gap = max(
            2,
            int(
                gap_px
                if gap_px is not None
                else getattr(config, "MARCAS_VIALES_GAP_PX", 7)
            ),
        )
        ya, yb = (y0, y1) if y0 <= y1 else (y1, y0)
        y = float(ya)
        while y <= yb:
            y_end = min(y + float(dash), float(yb))
            if y_end > y:
                pg.draw.line(surf, color, (int(x), int(y)), (int(x), int(y_end)), grosor)
            y = y_end + float(gap)

    def _linea_horizontal_discontinua(
        self,
        y: int,
        x0: int,
        x1: int,
        color: tuple,
        grosor: int = 1,
        dash_px: int | None = None,
        gap_px: int | None = None,
    ) -> None:
        pg = self._pg
        surf = self._pantalla
        dash = max(
            3,
            int(
                dash_px
                if dash_px is not None
                else getattr(config, "MARCAS_VIALES_DASH_PX", 10)
            ),
        )
        gap = max(
            2,
            int(
                gap_px
                if gap_px is not None
                else getattr(config, "MARCAS_VIALES_GAP_PX", 7)
            ),
        )
        xa, xb = (x0, x1) if x0 <= x1 else (x1, x0)
        x = float(xa)
        while x <= xb:
            x_end = min(x + float(dash), float(xb))
            if x_end > x:
                pg.draw.line(surf, color, (int(x), int(y)), (int(x_end), int(y)), grosor)
            x = x_end + float(gap)

    def _dibujar_marcas_viales(self, cx: int, cy: int, ancho_calle: int) -> None:
        """Paralelas (suaves) y eje fuera del cruce + marco blanco del cuadrado central."""
        pg = self._pg
        surf = self._pantalla
        color_eje = tuple(getattr(config, "COLOR_MARCA_VIAL", (248, 248, 252)))
        color_par = tuple(getattr(config, "COLOR_MARCA_VIAL_PARALELA", (198, 200, 210)))
        largo = max(config.ANCHO_VENTANA, config.ALTO_VENTANA)
        mid = int(round(float(getattr(config, "OFFSET_CENTRO_GRUPO_CARRIL", 28.0))))
        h = ancho_calle // 2
        y_lo = cy - h
        y_hi = cy + h
        x_lo = cx - h
        x_hi = cx + h

        def v_doble(xv: int, g: int, col: tuple) -> None:
            if y_lo > 0:
                self._linea_vertical_discontinua(xv, 0, y_lo, col, g)
            if y_hi < largo:
                self._linea_vertical_discontinua(xv, y_hi, largo - 1, col, g)

        def h_doble(yv: int, g: int, col: tuple) -> None:
            if x_lo > 0:
                self._linea_horizontal_discontinua(yv, 0, x_lo, col, g)
            if x_hi < largo:
                self._linea_horizontal_discontinua(yv, x_hi, largo - 1, col, g)

        # Ejes (sentido opuesto) y carriles paralelos: tramos fuera del cuadro del cruce.
        v_doble(cx, 2, color_eje)
        v_doble(cx - mid, 1, color_par)
        v_doble(cx + mid, 1, color_par)
        h_doble(cy, 2, color_eje)
        h_doble(cy - mid, 1, color_par)
        h_doble(cy + mid, 1, color_par)

        marco = max(1, int(getattr(config, "CRUCE_MARCO_GROSOR_PX", 3)))
        pg.draw.rect(surf, color_eje, (x_lo, y_lo, ancho_calle, ancho_calle), width=marco)

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
        ancho_calle = int(round(2.0 * float(getattr(config, "MITAD_ANCHO_VIA", 55.0))))
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

        self._dibujar_marcas_viales(cx, cy, ancho_calle)

        self._dibujar_semaforos(cx, cy)
        self._asegurar_sprites_base_por_tipo()

        for v in self.interseccion.vehiculos:
            color = (
                config.COLOR_CARRO_NS
                if v.direccion
                in (DireccionMovimiento.HACIA_SUR, DireccionMovimiento.HACIA_NORTE)
                else config.COLOR_CARRO_EW
            )
            sprite = self._sprite_rotado(v)
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
        self._dibujar_hud_metricas(lineas)

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

        radio = int(getattr(config, "SEMAFORO_RADIO_PX", 7))
        borde = int(getattr(config, "SEMAFORO_BORDE_PX", 2))
        color_borde = tuple(getattr(config, "COLOR_SEMAFORO_BORDE", (0, 0, 0)))
        offset = 78
        pos_ns = [(cx - offset, cy - offset), (cx + offset, cy + offset)]
        pos_ew = [(cx + offset, cy - offset), (cx - offset, cy + offset)]
        for px, py in pos_ns:
            pg.draw.circle(self._pantalla, color_borde, (px, py), radio + borde)
            pg.draw.circle(self._pantalla, color_para(True), (px, py), radio)
        for px, py in pos_ew:
            pg.draw.circle(self._pantalla, color_borde, (px, py), radio + borde)
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

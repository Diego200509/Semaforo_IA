"""
Menú gráfico para lanzar simulación, entrenamiento y reportes sin escribir la CLI.

Ejecutar desde la raíz del proyecto: python launcher.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError as e:  # pragma: no cover
    print("Tkinter no está disponible en este Python. Instala python3-tk o use la CLI: python main.py --help")
    raise SystemExit(1) from e

import config as cfg

RAIZ = Path(__file__).resolve().parent
MAIN_PY = RAIZ / "main.py"
SCRIPT_GRAFICAR_MEMBRESIAS = RAIZ / "scripts" / "graficar_membresias.py"
CARPETA_GRAFICAS = RAIZ / "graficas"
VENV_PYTHON = RAIZ / "venv" / "Scripts" / "python.exe"
PYTHON_312_PATHS = (
    Path(r"C:\Users\diego\AppData\Local\Programs\Python\Python312\python.exe"),
    Path(r"C:\Python312\python.exe"),
)

ESCENARIOS = ("bajo", "pico", "desbalanceado", "mixto")
PERFILES_ENTRENAMIENTO_UI = tuple(cfg.PERFILES_ENTRENAMIENTO_UI)
PERFIL_UI_A_CLAVE = {perfil.etiqueta_ui: perfil.clave for perfil in cfg.PERFILES_ENTRENAMIENTO.values()}


def _probar_comando_python(cmd: list[str]) -> bool:
    try:
        proc = subprocess.run(
            [*cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    salida = f"{proc.stdout} {proc.stderr}".strip()
    return proc.returncode == 0 and "Python 3.12" in salida


def _resolver_python_proyecto() -> list[str] | None:
    """
    El proyecto prioriza Python 3.12 porque el entorno virtual y dependencias fueron
    preparados para esa versión.
    """
    if VENV_PYTHON.is_file() and _probar_comando_python([str(VENV_PYTHON)]):
        return [str(VENV_PYTHON)]
    if _probar_comando_python(["py", "-3.12"]):
        return ["py", "-3.12"]
    for ruta in PYTHON_312_PATHS:
        if ruta.is_file() and _probar_comando_python([str(ruta)]):
            return [str(ruta)]
    if sys.version_info[:2] == (3, 12):
        return [sys.executable]
    return None


def _mensaje_python_312_no_disponible() -> str:
    return (
        "Este proyecto debe ejecutarse con Python 3.12.\n\n"
        "No encontré un intérprete 3.12 usable en esta máquina ni un venv válido.\n"
        "Instala Python 3.12 o recrea el entorno virtual del proyecto con esa versión."
    )


def _popen_main(args: list[str]) -> None:
    python_cmd = _resolver_python_proyecto()
    if python_cmd is None:
        messagebox.showerror("Python 3.12 requerido", _mensaje_python_312_no_disponible())
        return
    cmd = [*python_cmd, str(MAIN_PY), *args]
    kw: dict = {"cwd": str(RAIZ)}
    if sys.platform == "win32":
        kw["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    else:
        kw["start_new_session"] = True
    subprocess.Popen(cmd, **kw)


def _validar_opciones_sim(
    *,
    usar_default: bool,
    usar_ga: bool,
    adaptacion_banco: bool,
    tiempo_fijo: bool,
) -> str | None:
    # Red de seguridad (el menú suele impedir estas mezclas al marcar).
    if tiempo_fijo and (usar_default or usar_ga or adaptacion_banco):
        return "Con “semáforo clásico” no aplica el difuso: quita las otras tres opciones de reglas."
    n = int(usar_default) + int(usar_ga) + int(adaptacion_banco)
    if n > 1:
        return "Solo puedes elegir una fuente de reglas: estándar, entrenamiento GA o banco (o ninguna = automático)."
    return None


def _args_sim_base(
    escenario: str,
    *,
    perfil_entrenamiento: str,
    usar_default: bool,
    usar_ga: bool,
    adaptacion_banco: bool,
    tiempo_fijo: bool,
    verbose_escenario: bool,
    no_fase_adaptativa: bool,
) -> list[str]:
    args: list[str] = ["--escenario", escenario, "--perfil-entrenamiento", perfil_entrenamiento]
    if usar_default:
        args.append("--usar-default")
    if usar_ga:
        args.append("--usar-ga")
    if adaptacion_banco:
        args.append("--adaptacion-banco")
    if tiempo_fijo:
        args.append("--tiempo-fijo")
    if verbose_escenario:
        args.append("--verbose-escenario")
    if no_fase_adaptativa:
        args.append("--no-fase-adaptativa")
    return args


class LauncherApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Semáforo inteligente — Menú principal")
        self.minsize(520, 620)
        self.geometry("760x760")

        self._duracion_comparar_default = float(cfg.DURACION_COMPARAR_DIFUSO_GA)
        self._imagenes_graficas: list[Path] = []
        self._grafica_seleccionada: Path | None = None
        self._proceso_graficas_activo = False

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._tab_sim = ttk.Frame(nb, padding=8)
        self._tab_reportes = ttk.Frame(nb, padding=8)
        self._tab_graficas = ttk.Frame(nb, padding=8)
        nb.add(self._tab_sim, text="  Ver el cruce (simulación)  ")
        nb.add(self._tab_reportes, text="  Entrenar y comparar  ")
        nb.add(self._tab_graficas, text="  Graficas  ")

        self._build_tab_sim()
        self._build_tab_reportes()
        self._build_tab_graficas()

        pie = ttk.Frame(self, padding=(8, 0, 8, 8))
        pie.pack(fill=tk.X)
        ttk.Button(pie, text="Cerrar menú", command=self.destroy).pack(side=tk.RIGHT)

    def _enlazar_exclusiones_control_semaforo(self) -> None:
        """Alineado con main.py: una sola fuente difusa (o ninguna) y semáforo fijo excluye el difuso."""
        self._mutuo_control = False

        def on_default(*_: object) -> None:
            if self._mutuo_control or not self.var_default.get():
                return
            self._mutuo_control = True
            try:
                self.var_ga.set(False)
                self.var_banco.set(False)
                self.var_tiempo_fijo.set(False)
            finally:
                self._mutuo_control = False

        def on_ga(*_: object) -> None:
            if self._mutuo_control or not self.var_ga.get():
                return
            self._mutuo_control = True
            try:
                self.var_default.set(False)
                self.var_banco.set(False)
                self.var_tiempo_fijo.set(False)
            finally:
                self._mutuo_control = False

        def on_banco(*_: object) -> None:
            if self._mutuo_control or not self.var_banco.get():
                return
            self._mutuo_control = True
            try:
                self.var_default.set(False)
                self.var_ga.set(False)
                self.var_tiempo_fijo.set(False)
            finally:
                self._mutuo_control = False

        def on_tiempo_fijo(*_: object) -> None:
            if self._mutuo_control or not self.var_tiempo_fijo.get():
                return
            self._mutuo_control = True
            try:
                self.var_default.set(False)
                self.var_ga.set(False)
                self.var_banco.set(False)
            finally:
                self._mutuo_control = False

        self.var_default.trace_add("write", on_default)
        self.var_ga.trace_add("write", on_ga)
        self.var_banco.trace_add("write", on_banco)
        self.var_tiempo_fijo.trace_add("write", on_tiempo_fijo)

    def _refrescar_nota_opciones(self) -> None:
        """Una o dos frases cortas según lo marcado; evita el bloque de texto fijo largo."""
        if not hasattr(self, "lbl_nota_opciones"):
            return
        perfil = cfg.obtener_perfil_entrenamiento(self._perfil_sim_clave())
        partes: list[str] = []
        if self.var_tiempo_fijo.get():
            partes.append("Semáforo fijo: sin difuso. Las otras tres opciones de reglas quedan desmarcadas.")
        elif self.var_banco.get():
            partes.append(
                f"Banco activo [{perfil.etiqueta_ui}]: el difuso usa {perfil.archivo_banco_cromosomas.name}."
            )
        elif self.var_ga.get():
            partes.append(
                f"GA activo [{perfil.etiqueta_ui}]: se cargará {perfil.archivo_mejor_cromosoma.name}."
            )
        elif self.var_default.get():
            partes.append("Reglas difusas estándar: no se usan archivos de entrenamiento.")
        else:
            partes.append(
                f"Automático [{perfil.etiqueta_ui}]: si existe {perfil.archivo_mejor_cromosoma.name} se usa; si no, reglas estándar."
            )
        extra: list[str] = []
        if self.var_verbose.get():
            extra.append("Consola: ver cambios de tráfico (útil con escenario «mixto»).")
        if self.var_no_adapt.get():
            extra.append("Ciclo entre ejes sin prioridad por colas largas.")
        texto = " ".join(partes)
        if extra:
            texto = f"{texto} {' '.join(extra)}"
        self.lbl_nota_opciones.configure(text=texto)

    def _build_tab_sim(self) -> None:
        f = self._tab_sim

        lf_esc = ttk.LabelFrame(f, text="Cuánto tráfico hay en la simulación", padding=8)
        lf_esc.pack(fill=tk.X, pady=(0, 8))
        self.var_escenario = tk.StringVar(value=ESCENARIOS[0])
        ttk.Combobox(
            lf_esc,
            textvariable=self.var_escenario,
            values=ESCENARIOS,
            state="readonly",
            width=24,
        ).pack(anchor=tk.W)
        ttk.Label(
            lf_esc,
            text="bajo = pocos coches · pico = muchos · desbalanceado = más en un sentido · mixto = cambia con el tiempo",
            wraplength=520,
        ).pack(anchor=tk.W, pady=(6, 0))

        lf_opt = ttk.LabelFrame(f, text="Cómo controla el semáforo (marca lo que necesites)", padding=8)
        lf_opt.pack(fill=tk.X, pady=(0, 8))
        self.var_default = tk.BooleanVar(value=False)
        self.var_ga = tk.BooleanVar(value=False)
        self.var_banco = tk.BooleanVar(value=False)
        self.var_tiempo_fijo = tk.BooleanVar(value=False)
        self.var_verbose = tk.BooleanVar(value=False)
        self.var_no_adapt = tk.BooleanVar(value=False)
        self.var_perfil_sim = tk.StringVar(value=cfg.obtener_perfil_entrenamiento().etiqueta_ui)
        fila_perfil = ttk.Frame(lf_opt)
        fila_perfil.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(fila_perfil, text="Perfil de entrenamiento:").pack(side=tk.LEFT)
        ttk.Combobox(
            fila_perfil,
            textvariable=self.var_perfil_sim,
            values=PERFILES_ENTRENAMIENTO_UI,
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT, padx=8)
        ttk.Checkbutton(
            lf_opt,
            text="Usar reglas por defecto (ignorar archivos de entrenamiento)",
            variable=self.var_default,
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            lf_opt,
            text="Usar solo el último entrenamiento (requiere archivo guardado del algoritmo genético)",
            variable=self.var_ga,
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            lf_opt,
            text="Elegir reglas distintas según cómo esté el tráfico (archivo “banco” de configuraciones)",
            variable=self.var_banco,
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            lf_opt,
            text="Semáforo clásico: duraciones fijas, sin lógica difusa",
            variable=self.var_tiempo_fijo,
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            lf_opt,
            text="Mostrar en consola cada cambio de tráfico (útil con escenario “mixto”)",
            variable=self.var_verbose,
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            lf_opt,
            text="Ciclo Norte-Sur / Este-Oeste siempre igual (no alargar verde por colas largas)",
            variable=self.var_no_adapt,
        ).pack(anchor=tk.W)
        self._enlazar_exclusiones_control_semaforo()
        self.lbl_nota_opciones = ttk.Label(lf_opt, text="", wraplength=500)
        self.lbl_nota_opciones.pack(anchor=tk.W, pady=(10, 0))
        for _v in (
            self.var_perfil_sim,
            self.var_default,
            self.var_ga,
            self.var_banco,
            self.var_tiempo_fijo,
            self.var_verbose,
            self.var_no_adapt,
        ):
            _v.trace_add("write", lambda *_a, s=self: s._refrescar_nota_opciones())
        self._refrescar_nota_opciones()

        lf_run = ttk.LabelFrame(f, text="Poner en marcha", padding=8)
        lf_run.pack(fill=tk.BOTH, expand=True)
        ttk.Button(
            lf_run,
            text="▶ Abrir ventana del cruce (simulación animada)",
            command=self._sim_visual,
        ).pack(fill=tk.X, pady=4)
        ttk.Label(
            lf_run,
            text="Sin ventana: solo números y métricas en una consola negra.",
            wraplength=520,
        ).pack(anchor=tk.W, pady=(4, 0))
        row = ttk.Frame(lf_run)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Duración en segundos:").pack(side=tk.LEFT)
        self.var_seg_prog = tk.StringVar(value="90")
        ttk.Entry(row, textvariable=self.var_seg_prog, width=8).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="Ejecutar simulación en consola", command=self._sim_prog).pack(side=tk.LEFT)

    def _build_tab_reportes(self) -> None:
        f = self._tab_reportes

        lf_ga = ttk.LabelFrame(f, text="Entrenar el sistema (suele tardar bastante)", padding=8)
        lf_ga.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(
            lf_ga,
            text="Busca mejores tiempos de verde; guarda un archivo y una curva en la carpeta graficas/.",
            wraplength=520,
        ).pack(anchor=tk.W, pady=(0, 6))
        fila_perfil = ttk.Frame(lf_ga)
        fila_perfil.pack(fill=tk.X, pady=(0, 6))
        self.var_perfil_train = tk.StringVar(value=cfg.obtener_perfil_entrenamiento().etiqueta_ui)
        ttk.Label(fila_perfil, text="Perfil de entrenamiento:").pack(side=tk.LEFT)
        ttk.Combobox(
            fila_perfil,
            textvariable=self.var_perfil_train,
            values=PERFILES_ENTRENAMIENTO_UI,
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT, padx=8)
        self.lbl_nota_perfil_train = ttk.Label(lf_ga, text="", wraplength=520)
        self.lbl_nota_perfil_train.pack(anchor=tk.W, pady=(0, 6))
        self.var_perfil_train.trace_add("write", lambda *_: self._refrescar_nota_perfil_train())
        self._refrescar_nota_perfil_train()
        ttk.Button(
            lf_ga,
            text="Entrenar una sola configuración óptima (recomendado para empezar)",
            command=self._entrenar,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            lf_ga,
            text="Entrenar varias configuraciones (una por tipo de tráfico)",
            command=self._entrenar_banco,
        ).pack(fill=tk.X, pady=2)

        lf_cmp = ttk.LabelFrame(f, text="Comparar estrategias con varias pruebas", padding=8)
        lf_cmp.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(
            lf_cmp,
            text="Repite la simulación con distintas semillas y genera gráficas en graficas/.",
            wraplength=520,
        ).pack(anchor=tk.W, pady=(0, 6))
        r1 = ttk.Frame(lf_cmp)
        r1.pack(fill=tk.X, pady=4)
        ttk.Label(r1, text="Segundos por prueba:").pack(side=tk.LEFT)
        self.var_seg_comparar = tk.StringVar(value=str(int(self._duracion_comparar_default)))
        ttk.Entry(r1, textvariable=self.var_seg_comparar, width=8).pack(side=tk.LEFT, padx=6)
        ttk.Label(r1, text="Tráfico:").pack(side=tk.LEFT, padx=(12, 0))
        self.var_escenario_cmp = tk.StringVar(value=ESCENARIOS[0])
        ttk.Combobox(
            r1,
            textvariable=self.var_escenario_cmp,
            values=ESCENARIOS,
            state="readonly",
            width=14,
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(lf_cmp, text="Ejecutar comparación y generar gráficas", command=self._comparar).pack(fill=tk.X, pady=4)

        lf_full = ttk.LabelFrame(f, text="Comparar las tres formas de control", padding=8)
        lf_full.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(
            lf_full,
            text="Tiempos fijos vs lógica difusa vs difusa mejorada por entrenamiento.",
            wraplength=520,
        ).pack(anchor=tk.W, pady=(0, 6))
        ttk.Button(
            lf_full,
            text="Ejecutar y guardar gráfico de costes en graficas/",
            command=self._comparar_completo,
        ).pack(fill=tk.X, pady=2)

        ttk.Label(
            f,
            text="Cada acción abre una consola: ahí ves el progreso. Las imágenes quedan en la carpeta graficas/.",
            wraplength=520,
        ).pack(fill=tk.X, pady=(8, 0))

    def _build_tab_graficas(self) -> None:
        f = self._tab_graficas

        lf_acciones = ttk.LabelFrame(f, text="Generar y actualizar", padding=8)
        lf_acciones.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(
            lf_acciones,
            text=(
                "Estas acciones reutilizan los comandos oficiales del proyecto "
                "y refrescan la carpeta graficas/ al terminar."
            ),
            wraplength=680,
        ).pack(anchor=tk.W, pady=(0, 8))
        ttk.Button(
            lf_acciones,
            text="Generar graficas de membresia",
            command=self._graficas_generar_membresias,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            lf_acciones,
            text="Entrenar GA final y actualizar fitness",
            command=self._graficas_entrenar_final,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            lf_acciones,
            text="Comparar estrategias y actualizar comparativas",
            command=self._graficas_comparar_final,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            lf_acciones,
            text="Comparacion completa y actualizar costes",
            command=self._graficas_comparar_completo_final,
        ).pack(fill=tk.X, pady=2)

        self.var_estado_graficas = tk.StringVar(
            value="Listo. Usa esta pestaña para generar, abrir y revisar las imagenes."
        )
        ttk.Label(
            lf_acciones,
            textvariable=self.var_estado_graficas,
            wraplength=680,
            foreground="#1f4f82",
        ).pack(anchor=tk.W, pady=(10, 0))

        lf_lista = ttk.LabelFrame(f, text="Imagenes disponibles en graficas", padding=8)
        lf_lista.pack(fill=tk.BOTH, expand=True)

        fila_top = ttk.Frame(lf_lista)
        fila_top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(fila_top, text="Refrescar lista", command=self._refrescar_lista_graficas).pack(side=tk.LEFT)
        ttk.Button(fila_top, text="Abrir carpeta graficas", command=self._abrir_carpeta_graficas).pack(
            side=tk.LEFT, padx=6
        )

        cuerpo = ttk.Frame(lf_lista)
        cuerpo.pack(fill=tk.BOTH, expand=True)
        self.listbox_graficas = tk.Listbox(cuerpo, height=12, exportselection=False)
        self.listbox_graficas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(cuerpo, orient=tk.VERTICAL, command=self.listbox_graficas.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_graficas.configure(yscrollcommand=scroll.set)
        self.listbox_graficas.bind("<<ListboxSelect>>", self._on_select_grafica)
        self.listbox_graficas.bind("<Double-Button-1>", lambda *_: self._abrir_grafica_seleccionada())

        fila_acciones = ttk.Frame(lf_lista)
        fila_acciones.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(
            fila_acciones,
            text="Ver en ventana",
            command=self._visualizar_grafica_seleccionada,
        ).pack(side=tk.LEFT)
        ttk.Button(
            fila_acciones,
            text="Abrir con visor del sistema",
            command=self._abrir_grafica_seleccionada,
        ).pack(side=tk.LEFT, padx=6)

        self.var_grafica_actual = tk.StringVar(value="No hay imagen seleccionada.")
        ttk.Label(
            lf_lista,
            textvariable=self.var_grafica_actual,
            wraplength=680,
        ).pack(anchor=tk.W, pady=(10, 0))

        self._refrescar_lista_graficas()

    def _perfil_sim_clave(self) -> str:
        return PERFIL_UI_A_CLAVE.get(self.var_perfil_sim.get(), cfg.PERFIL_ENTRENAMIENTO_POR_DEFECTO)

    def _perfil_train_clave(self) -> str:
        return PERFIL_UI_A_CLAVE.get(self.var_perfil_train.get(), cfg.PERFIL_ENTRENAMIENTO_POR_DEFECTO)

    def _refrescar_nota_perfil_train(self) -> None:
        if not hasattr(self, "lbl_nota_perfil_train"):
            return
        perfil = cfg.obtener_perfil_entrenamiento(self._perfil_train_clave())
        self.lbl_nota_perfil_train.configure(
            text=(
                f"{perfil.etiqueta_ui}: población {perfil.poblacion_ga}, generaciones {perfil.generaciones_ga}, "
                f"salida {perfil.archivo_mejor_cromosoma.name} / {perfil.archivo_banco_cromosomas.name}"
            )
        )

    def _flags_sim(self) -> tuple[str, dict[str, bool | str]] | None:
        esc = self.var_escenario.get().strip().lower()
        if esc not in ESCENARIOS:
            messagebox.showerror("Escenario", f"Escenario no válido: {esc}")
            return None
        d = {
            "perfil_entrenamiento": self._perfil_sim_clave(),
            "usar_default": self.var_default.get(),
            "usar_ga": self.var_ga.get(),
            "adaptacion_banco": self.var_banco.get(),
            "tiempo_fijo": self.var_tiempo_fijo.get(),
            "verbose_escenario": self.var_verbose.get(),
            "no_fase_adaptativa": self.var_no_adapt.get(),
        }
        err = _validar_opciones_sim(
            usar_default=d["usar_default"],
            usar_ga=d["usar_ga"],
            adaptacion_banco=d["adaptacion_banco"],
            tiempo_fijo=d["tiempo_fijo"],
        )
        if err:
            messagebox.showerror("Opciones que no van juntas", err)
            return None
        return esc, d

    def _sim_visual(self) -> None:
        got = self._flags_sim()
        if not got:
            return
        esc, d = got
        args = ["--modo", "sim_visual", *_args_sim_base(esc, **d)]
        _popen_main(args)

    def _sim_prog(self) -> None:
        got = self._flags_sim()
        if not got:
            return
        esc, d = got
        try:
            seg = float(self.var_seg_prog.get().replace(",", "."))
            if seg <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Duración", "Indica un número de segundos válido (> 0).")
            return
        args = ["--modo", "sim_prog", "--segundos", str(seg), *_args_sim_base(esc, **d)]
        _popen_main(args)

    def _entrenar(self) -> None:
        _popen_main(["--modo", "entrenar", "--perfil-entrenamiento", self._perfil_train_clave()])

    def _entrenar_banco(self) -> None:
        _popen_main(["--modo", "entrenar_banco", "--perfil-entrenamiento", self._perfil_train_clave()])

    def _comparar(self) -> None:
        try:
            seg = float(self.var_seg_comparar.get().replace(",", "."))
            if seg <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Duración", "Indica segundos válidos para comparar.")
            return
        esc = self.var_escenario_cmp.get().strip().lower()
        if esc not in ESCENARIOS:
            messagebox.showerror("Escenario", f"Escenario no válido: {esc}")
            return
        _popen_main(
            [
                "--modo",
                "comparar",
                "--segundos",
                str(seg),
                "--escenario",
                esc,
                "--perfil-entrenamiento",
                self._perfil_train_clave(),
            ]
        )

    def _comparar_completo(self) -> None:
        _popen_main(["--modo", "comparar_completo", "--perfil-entrenamiento", self._perfil_train_clave()])

    def _python_cmd_proyecto(self) -> list[str] | None:
        python_cmd = _resolver_python_proyecto()
        if python_cmd is None:
            messagebox.showerror("Python 3.12 requerido", _mensaje_python_312_no_disponible())
            return None
        return python_cmd

    def _iniciar_proceso_graficas(self, titulo: str, cmd: list[str]) -> None:
        if self._proceso_graficas_activo:
            messagebox.showinfo(
                "Proceso en curso",
                "Ya hay una accion de graficas ejecutandose. Espera a que termine para iniciar otra.",
            )
            return

        self._proceso_graficas_activo = True
        self.var_estado_graficas.set(f"Ejecutando: {titulo}...")
        kw: dict = {"cwd": str(RAIZ)}
        if sys.platform == "win32":
            kw["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        else:
            kw["start_new_session"] = True

        try:
            proc = subprocess.Popen(cmd, **kw)
        except OSError as exc:
            self._proceso_graficas_activo = False
            self.var_estado_graficas.set("No se pudo iniciar el proceso.")
            messagebox.showerror("Error al ejecutar", str(exc))
            return

        def _esperar() -> None:
            rc = proc.wait()
            self.after(0, lambda: self._finalizar_proceso_graficas(titulo, rc))

        threading.Thread(target=_esperar, daemon=True).start()

    def _finalizar_proceso_graficas(self, titulo: str, returncode: int) -> None:
        self._proceso_graficas_activo = False
        self._refrescar_lista_graficas()
        if returncode == 0:
            self.var_estado_graficas.set(f"Proceso terminado: {titulo}. Lista de imagenes actualizada.")
            return
        self.var_estado_graficas.set(f"El proceso finalizo con errores: {titulo}.")
        messagebox.showwarning(
            "Proceso finalizado con errores",
            (
                f"La accion '{titulo}' termino con codigo {returncode}.\n"
                "Revisa la consola que se abrio para ver el detalle."
            ),
        )

    def _graficas_generar_membresias(self) -> None:
        python_cmd = self._python_cmd_proyecto()
        if python_cmd is None:
            return
        if not SCRIPT_GRAFICAR_MEMBRESIAS.is_file():
            messagebox.showerror(
                "Script no disponible",
                f"No se encontro el script esperado:\n{SCRIPT_GRAFICAR_MEMBRESIAS}",
            )
            return
        self._iniciar_proceso_graficas(
            "Graficas de membresia",
            [*python_cmd, str(SCRIPT_GRAFICAR_MEMBRESIAS)],
        )

    def _graficas_entrenar_final(self) -> None:
        python_cmd = self._python_cmd_proyecto()
        if python_cmd is None:
            return
        self._iniciar_proceso_graficas(
            "Entrenamiento final",
            [*python_cmd, str(MAIN_PY), "--modo", "entrenar", "--perfil-entrenamiento", "final"],
        )

    def _graficas_comparar_final(self) -> None:
        python_cmd = self._python_cmd_proyecto()
        if python_cmd is None:
            return
        self._iniciar_proceso_graficas(
            "Comparacion final",
            [*python_cmd, str(MAIN_PY), "--modo", "comparar", "--perfil-entrenamiento", "final"],
        )

    def _graficas_comparar_completo_final(self) -> None:
        python_cmd = self._python_cmd_proyecto()
        if python_cmd is None:
            return
        self._iniciar_proceso_graficas(
            "Comparacion completa final",
            [*python_cmd, str(MAIN_PY), "--modo", "comparar_completo", "--perfil-entrenamiento", "final"],
        )

    def _archivos_graficas_disponibles(self) -> list[Path]:
        if not CARPETA_GRAFICAS.is_dir():
            return []
        exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
        return [
            p for p in sorted(CARPETA_GRAFICAS.iterdir(), key=lambda x: x.name.lower())
            if p.is_file() and p.suffix.lower() in exts
        ]

    def _refrescar_lista_graficas(self) -> None:
        self._imagenes_graficas = self._archivos_graficas_disponibles()
        self.listbox_graficas.delete(0, tk.END)
        self._grafica_seleccionada = None
        if not self._imagenes_graficas:
            self.var_grafica_actual.set(
                f"No hay imagenes en {CARPETA_GRAFICAS}. Genera una grafica desde esta pestaña."
            )
            return
        for ruta in self._imagenes_graficas:
            self.listbox_graficas.insert(tk.END, ruta.name)
        self.listbox_graficas.selection_set(0)
        self.listbox_graficas.activate(0)
        self._actualizar_grafica_seleccionada_desde_lista()

    def _on_select_grafica(self, _event: object | None = None) -> None:
        self._actualizar_grafica_seleccionada_desde_lista()

    def _actualizar_grafica_seleccionada_desde_lista(self) -> None:
        seleccion = self.listbox_graficas.curselection()
        if not seleccion:
            if self._imagenes_graficas:
                self.var_grafica_actual.set("Selecciona una imagen para abrirla o verla.")
            return
        idx = int(seleccion[0])
        if idx < 0 or idx >= len(self._imagenes_graficas):
            self.var_grafica_actual.set("Selecciona una imagen valida.")
            return
        self._grafica_seleccionada = self._imagenes_graficas[idx]
        self.var_grafica_actual.set(f"Seleccionada: {self._grafica_seleccionada}")

    def _ruta_grafica_seleccionada(self) -> Path | None:
        self._actualizar_grafica_seleccionada_desde_lista()
        if self._grafica_seleccionada is None or not self._grafica_seleccionada.is_file():
            messagebox.showinfo(
                "Grafica no disponible",
                "La imagen seleccionada no existe. Refresca la lista o genera las graficas primero.",
            )
            return None
        return self._grafica_seleccionada

    def _abrir_carpeta_graficas(self) -> None:
        CARPETA_GRAFICAS.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(CARPETA_GRAFICAS))
        except AttributeError:
            subprocess.Popen(["xdg-open", str(CARPETA_GRAFICAS)], cwd=str(RAIZ))
        except OSError as exc:
            messagebox.showerror("No se pudo abrir la carpeta", str(exc))

    def _abrir_grafica_seleccionada(self) -> None:
        ruta = self._ruta_grafica_seleccionada()
        if ruta is None:
            return
        try:
            os.startfile(str(ruta))
        except AttributeError:
            subprocess.Popen(["xdg-open", str(ruta)], cwd=str(RAIZ))
        except OSError as exc:
            messagebox.showerror("No se pudo abrir la imagen", str(exc))

    def _visualizar_grafica_seleccionada(self) -> None:
        ruta = self._ruta_grafica_seleccionada()
        if ruta is None:
            return
        try:
            img = tk.PhotoImage(file=str(ruta))
        except tk.TclError:
            messagebox.showinfo(
                "Vista rapida no disponible",
                "No pude mostrar la imagen dentro del launcher. Usa el visor del sistema.",
            )
            return

        w_max, h_max = 880, 620
        factor_w = max(1, (img.width() + w_max - 1) // w_max)
        factor_h = max(1, (img.height() + h_max - 1) // h_max)
        factor = max(factor_w, factor_h)
        if factor > 1:
            img = img.subsample(factor, factor)

        top = tk.Toplevel(self)
        top.title(f"Vista rapida - {ruta.name}")
        top.transient(self)
        top.img_ref = img
        top.geometry(
            f"{min(w_max + 40, max(420, img.width() + 24))}x"
            f"{min(h_max + 90, max(320, img.height() + 70))}"
        )

        ttk.Label(top, text=ruta.name).pack(anchor=tk.W, padx=10, pady=(10, 4))
        ttk.Label(top, image=img).pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        ttk.Label(top, text=str(ruta), wraplength=w_max).pack(anchor=tk.W, padx=10, pady=(0, 10))


def main() -> int:
    if not MAIN_PY.is_file():
        print(f"No se encontró main.py en {MAIN_PY.parent}")
        return 1
    app = LauncherApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

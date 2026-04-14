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
        self.title("Semáforo inteligente — Panel principal")
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
        nb.add(self._tab_sim, text="  Simulación  ")
        nb.add(self._tab_reportes, text="  Entrenamiento  ")
        nb.add(self._tab_graficas, text="  Gráficas  ")

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
        lf_cfg = ttk.LabelFrame(f, text="Configuración", padding=8)
        lf_cfg.pack(fill=tk.X, pady=(0, 8))

        fila_esc = ttk.Frame(lf_cfg)
        fila_esc.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(fila_esc, text="Tráfico:").pack(side=tk.LEFT)
        self.var_escenario = tk.StringVar(value=ESCENARIOS[0])
        ttk.Combobox(
            fila_esc,
            textvariable=self.var_escenario,
            values=ESCENARIOS,
            state="readonly",
            width=18,
        ).pack(side=tk.LEFT, padx=8)

        lf_control = ttk.LabelFrame(lf_cfg, text="Modo de control", padding=8)
        lf_control.pack(fill=tk.X)
        self.var_modo_control = tk.StringVar(value="ga")
        ttk.Radiobutton(
            lf_control,
            text="Semáforo fijo",
            value="fijo",
            variable=self.var_modo_control,
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            lf_control,
            text="Lógica difusa (base)",
            value="difuso_base",
            variable=self.var_modo_control,
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            lf_control,
            text="Lógica difusa optimizada (GA)",
            value="ga",
            variable=self.var_modo_control,
        ).pack(anchor=tk.W)

        lf_run = ttk.LabelFrame(f, text="Ejecución", padding=8)
        lf_run.pack(fill=tk.BOTH, expand=True)
        fila_duracion = ttk.Frame(lf_run)
        fila_duracion.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(fila_duracion, text="Duración (opcional):").pack(side=tk.LEFT)
        self.var_seg_sim = tk.StringVar(value="")
        ttk.Entry(fila_duracion, textvariable=self.var_seg_sim, width=10).pack(side=tk.LEFT, padx=8)
        ttk.Label(
            lf_run,
            text="Si dejas la duración vacía, se abre la simulación animada. Si indicas segundos, se ejecuta una corrida rápida en consola.",
            wraplength=620,
        ).pack(anchor=tk.W, pady=(0, 10))
        ttk.Button(
            lf_run,
            text="▶ Ejecutar simulación",
            command=self._ejecutar_simulacion,
        ).pack(fill=tk.X)

    def _build_tab_reportes(self) -> None:
        f = self._tab_reportes
        lf_cfg = ttk.LabelFrame(f, text="Configuración", padding=8)
        lf_cfg.pack(fill=tk.X, pady=(0, 8))
        fila_perfil = ttk.Frame(lf_cfg)
        fila_perfil.pack(fill=tk.X)
        self.var_perfil_train = tk.StringVar(value=cfg.obtener_perfil_entrenamiento().etiqueta_ui)
        ttk.Label(fila_perfil, text="Perfil de entrenamiento:").pack(side=tk.LEFT)
        ttk.Combobox(
            fila_perfil,
            textvariable=self.var_perfil_train,
            values=PERFILES_ENTRENAMIENTO_UI,
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT, padx=8)

        lf_run = ttk.LabelFrame(f, text="Ejecución", padding=8)
        lf_run.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(
            lf_run,
            text="Entrenar modelo",
            command=self._entrenar,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            lf_run,
            text="Entrenar múltiples configuraciones",
            command=self._entrenar_banco,
        ).pack(fill=tk.X, pady=2)

        lf_out = ttk.LabelFrame(f, text="Resultados", padding=8)
        lf_out.pack(fill=tk.BOTH, expand=True)
        self.lbl_nota_perfil_train = ttk.Label(lf_out, text="", wraplength=620, justify=tk.LEFT)
        self.lbl_nota_perfil_train.pack(anchor=tk.W)
        self.var_perfil_train.trace_add("write", lambda *_: self._refrescar_nota_perfil_train())
        self._refrescar_nota_perfil_train()

    def _build_tab_graficas(self) -> None:
        f = self._tab_graficas

        lf_acciones = ttk.LabelFrame(f, text="Acciones", padding=8)
        lf_acciones.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(
            lf_acciones,
            text="Generar gráficas de membresía",
            command=self._graficas_generar_membresias,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            lf_acciones,
            text="Entrenar GA y actualizar fitness",
            command=self._graficas_entrenar_final,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            lf_acciones,
            text="Comparar estrategias",
            command=self._graficas_comparar_final,
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            lf_acciones,
            text="Comparación completa",
            command=self._graficas_comparar_completo_final,
        ).pack(fill=tk.X, pady=2)

        self.var_estado_graficas = tk.StringVar(
            value="Listo para generar y revisar resultados."
        )
        ttk.Label(
            lf_acciones,
            textvariable=self.var_estado_graficas,
            wraplength=680,
            foreground="#1f4f82",
        ).pack(anchor=tk.W, pady=(10, 0))

        lf_lista = ttk.LabelFrame(f, text="Resultados", padding=8)
        lf_lista.pack(fill=tk.BOTH, expand=True)

        fila_top = ttk.Frame(lf_lista)
        fila_top.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(fila_top, text="Refrescar lista", command=self._refrescar_lista_graficas).pack(side=tk.LEFT)
        ttk.Button(fila_top, text="Abrir carpeta", command=self._abrir_carpeta_graficas).pack(
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

        self.var_grafica_actual = tk.StringVar(value="No hay imágenes disponibles.")
        ttk.Label(
            lf_lista,
            textvariable=self.var_grafica_actual,
            wraplength=680,
        ).pack(anchor=tk.W, pady=(10, 0))

        self._refrescar_lista_graficas()

    def _perfil_sim_clave(self) -> str:
        return cfg.PERFIL_ENTRENAMIENTO_POR_DEFECTO

    def _perfil_train_clave(self) -> str:
        return PERFIL_UI_A_CLAVE.get(self.var_perfil_train.get(), cfg.PERFIL_ENTRENAMIENTO_POR_DEFECTO)

    def _refrescar_nota_perfil_train(self) -> None:
        if not hasattr(self, "lbl_nota_perfil_train"):
            return
        perfil = cfg.obtener_perfil_entrenamiento(self._perfil_train_clave())
        self.lbl_nota_perfil_train.configure(
            text=(
                f"Cromosoma: {perfil.archivo_mejor_cromosoma.name}\n"
                f"Banco: {perfil.archivo_banco_cromosomas.name}\n"
                f"Gráfica esperada: {cfg.CARPETA_GRAFICAS.name}/evolucion_fitness_{perfil.clave}.png"
            )
        )

    def _args_modo_control(self) -> list[str]:
        modo = self.var_modo_control.get().strip().lower()
        if modo == "fijo":
            return ["--tiempo-fijo"]
        if modo == "difuso_base":
            return ["--usar-default"]
        return ["--usar-ga"]

    def _ejecutar_simulacion(self) -> None:
        esc = self.var_escenario.get().strip().lower()
        if esc not in ESCENARIOS:
            messagebox.showerror("Escenario", f"Escenario no válido: {esc}")
            return

        args = [
            "--escenario",
            esc,
            "--perfil-entrenamiento",
            self._perfil_sim_clave(),
            *self._args_modo_control(),
        ]

        seg_txt = self.var_seg_sim.get().strip().replace(",", ".")
        if not seg_txt:
            _popen_main(["--modo", "sim_visual", *args])
            return

        try:
            seg = float(seg_txt)
            if seg <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Duración", "Indica un número de segundos válido (> 0) o deja el campo vacío.")
            return

        _popen_main(["--modo", "sim_prog", "--segundos", str(seg), *args])

    def _flags_sim(self) -> tuple[str, dict[str, bool | str]] | None:
        esc = self.var_escenario.get().strip().lower()
        if esc not in ESCENARIOS:
            messagebox.showerror("Escenario", f"Escenario no válido: {esc}")
            return None
        modo = self.var_modo_control.get().strip().lower()
        d = {
            "perfil_entrenamiento": self._perfil_sim_clave(),
            "usar_default": modo == "difuso_base",
            "usar_ga": modo == "ga",
            "adaptacion_banco": False,
            "tiempo_fijo": modo == "fijo",
            "verbose_escenario": False,
            "no_fase_adaptativa": False,
        }
        return esc, d

    def _sim_visual(self) -> None:
        actual = self.var_seg_sim.get()
        self.var_seg_sim.set("")
        try:
            self._ejecutar_simulacion()
        finally:
            self.var_seg_sim.set(actual)

    def _sim_prog(self) -> None:
        self._ejecutar_simulacion()

    def _entrenar(self) -> None:
        _popen_main(["--modo", "entrenar", "--perfil-entrenamiento", self._perfil_train_clave()])

    def _entrenar_banco(self) -> None:
        _popen_main(["--modo", "entrenar_banco", "--perfil-entrenamiento", self._perfil_train_clave()])

    def _comparar(self) -> None:
        self._graficas_comparar_final()

    def _comparar_completo(self) -> None:
        self._graficas_comparar_completo_final()

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
            self.var_estado_graficas.set(f"Proceso terminado: {titulo}. Lista de imágenes actualizada.")
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
                f"No hay imágenes en {CARPETA_GRAFICAS}. Genera una gráfica desde esta pestaña."
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

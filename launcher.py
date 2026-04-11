"""
Menú gráfico para lanzar simulación, entrenamiento y reportes sin escribir la CLI.

Ejecutar desde la raíz del proyecto: python launcher.py
"""

from __future__ import annotations

import subprocess
import sys
import webbrowser
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
VENV_PYTHON = RAIZ / "venv" / "Scripts" / "python.exe"
PYTHON_312_PATHS = (
    Path(r"C:\Users\diego\AppData\Local\Programs\Python\Python312\python.exe"),
    Path(r"C:\Python312\python.exe"),
)

ESCENARIOS = ("bajo", "pico", "desbalanceado", "mixto")


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
    usar_default: bool,
    usar_ga: bool,
    adaptacion_banco: bool,
    tiempo_fijo: bool,
    verbose_escenario: bool,
    no_fase_adaptativa: bool,
) -> list[str]:
    args: list[str] = ["--escenario", escenario]
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
        self.minsize(480, 560)
        self.geometry("580x620")

        self._duracion_comparar_default = float(cfg.DURACION_COMPARAR_DIFUSO_GA)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._tab_sim = ttk.Frame(nb, padding=8)
        self._tab_reportes = ttk.Frame(nb, padding=8)
        nb.add(self._tab_sim, text="  Ver el cruce (simulación)  ")
        nb.add(self._tab_reportes, text="  Entrenar y comparar  ")

        self._build_tab_sim()
        self._build_tab_reportes()

        pie = ttk.Frame(self, padding=(8, 0, 8, 8))
        pie.pack(fill=tk.X)
        ttk.Button(pie, text="Abrir documentación (README)", command=self._abrir_readme).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(pie, text="Ver comandos de consola", command=self._ayuda_cli).pack(side=tk.LEFT, padx=(0, 6))
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
        partes: list[str] = []
        if self.var_tiempo_fijo.get():
            partes.append("Semáforo fijo: sin difuso. Las otras tres opciones de reglas quedan desmarcadas.")
        elif self.var_banco.get():
            partes.append("Banco activo: el difuso cambia de configuración según el tráfico.")
        elif self.var_ga.get():
            partes.append("Solo entrenamiento GA: hace falta el archivo guardado del último entrenamiento.")
        elif self.var_default.get():
            partes.append("Reglas difusas estándar: no se usan archivos de entrenamiento.")
        else:
            partes.append("Automático: si existe archivo de entrenamiento se usa; si no, reglas estándar.")
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

    def _flags_sim(self) -> tuple[str, dict[str, bool]] | None:
        esc = self.var_escenario.get().strip().lower()
        if esc not in ESCENARIOS:
            messagebox.showerror("Escenario", f"Escenario no válido: {esc}")
            return None
        d = {
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
        _popen_main(["--modo", "entrenar"])

    def _entrenar_banco(self) -> None:
        _popen_main(["--modo", "entrenar_banco"])

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
        _popen_main(["--modo", "comparar", "--segundos", str(seg), "--escenario", esc])

    def _comparar_completo(self) -> None:
        _popen_main(["--modo", "comparar_completo"])

    def _abrir_readme(self) -> None:
        readme = RAIZ / "README.md"
        if readme.is_file():
            webbrowser.open(readme.as_uri())
        else:
            messagebox.showwarning("README", f"No se encontró {readme}")

    def _ayuda_cli(self) -> None:
        _popen_main(["--help"])


def main() -> int:
    if not MAIN_PY.is_file():
        print(f"No se encontró main.py en {MAIN_PY.parent}")
        return 1
    app = LauncherApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Paquete de simulación: entorno desacoplado del control inteligente.

Expone la interfaz abstracta del motor para permitir en el futuro un adaptador SUMO
sin modificar difuso, genético ni evaluación.
"""

from simulacion.entorno import MotorSimulacion, MotorSimulacionProgramatico, MotorSimulacionPygame

__all__ = [
    "MotorSimulacion",
    "MotorSimulacionProgramatico",
    "MotorSimulacionPygame",
]

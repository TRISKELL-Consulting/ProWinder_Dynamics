import math

class InertiaTracker:
    """
    Gère le calcul dynamique de l'inertie totale du système en fonction du rayon.
    Essential pour le Feedforward Control (80% de la consigne).
    J_tot = J_motor + J_roller + J_coil
    J_coil = 0.5 * PI * rho * L * (R^4 - R_core^4)
    """
    def __init__(self, j_motor: float, j_roller: float, r_core: float, width: float, density: float):
        self.J_fixed = j_motor + j_roller
        self.R_core = r_core
        self.L = width
        self.rho = density
        self.current_inertia = self._compute_inertia(r_core)

    def _compute_inertia(self, radius: float) -> float:
        if radius < self.R_core:
            radius = self.R_core
        j_coil = 0.5 * math.pi * self.rho * self.L * (pow(radius, 4) - pow(self.R_core, 4))
        return self.J_fixed + j_coil

    def update(self, current_radius: float) -> float:
        self.current_inertia = self._compute_inertia(current_radius)
        return self.current_inertia

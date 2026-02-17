import numpy as np

class FrictionModel:
    """
    Modèle de friction complèt incluant le frottement de Coulomb, visqueux et l'effet Stribeck.
    Critique pour la compensation au démarrage (Stiction).
    """
    def __init__(self, coulomb_coeff: float, viscous_coeff: float, stiction_coeff: float, stribeck_velocity: float):
        self.Tc = coulomb_coeff
        self.Kv = viscous_coeff
        self.Ts = stiction_coeff
        self.vs = stribeck_velocity

    def compute_torque(self, velocity: float) -> float:
        """
        Calcule le couple de frottement pour une vitesse donnée.
        T_friction = (Tc + (Ts - Tc) * exp(-(v/vs)^2)) * sign(v) + Kv * v
        """
        if self.vs == 0:
            stribeck_effect = 0
        else:
            stribeck_effect = (self.Ts - self.Tc) * np.exp(-(velocity / self.vs) ** 2)
            
        friction_torque = (self.Tc + stribeck_effect) * np.sign(velocity) + self.Kv * velocity
        return friction_torque

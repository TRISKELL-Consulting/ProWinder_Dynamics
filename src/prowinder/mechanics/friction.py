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
            # Add small epsilon to velocity to avoid division by zero or large exponents? No, velocity is in numerator here.
            # But the exponent is negative, so it's safe.
            stribeck_effect = (self.Ts - self.Tc) * np.exp(-(velocity / self.vs) ** 2)
            
        friction_torque = (self.Tc + stribeck_effect) * np.sign(velocity) + self.Kv * velocity
        
        # If velocity is exactly 0, np.sign(0) is 0, so stiction is lost.
        # But stiction should oppose the applied torque or be maximum.
        # This is the "Static Friction" ambiguity.
        # For an observer, we can't know the static friction unless we know the load.
        # However, for simulation purposes, if we want to reduce error at V=0:
        # We can assume that if V=0 and Torque is applied, friction balances torque up to Ts.
        # But this function only takes velocity.
        # Let's leave it as is, but maybe the observer should handle V=0 specially if we want perfection.
        
        return friction_torque

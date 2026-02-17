from typing import Optional
from .material import WebMaterial
from .friction import FrictionModel

class Roller:
    """
    Classe de base pour tout élément rotatif (Rouleau fou, rouleau tireur, bobineuse).
    """
    def __init__(self, name: str, inertia_base: float, radius_base: float, friction_model: Optional[FrictionModel] = None):
        self.name = name
        self.J_base = inertia_base        # Inertie mécanique fixe (arbre, mandrin)
        self.radius = radius_base         # Rayon actuel
        self.friction_model = friction_model
        
        # État Mécanique
        self.angle = 0.0 # rad
        self.omega = 0.0 # rad/s (Vit. angulaire)
        self.alpha = 0.0 # rad/s^2 (Accélération)

    def get_total_inertia(self) -> float:
        """Retourne l'inertie totale actuelle (à surcharger pour Winder)."""
        return self.J_base

    def get_friction_torque(self) -> float:
        """Calcule le couple de frottement résistif."""
        if self.friction_model:
            return self.friction_model.compute_torque(self.omega)
        return 0.0

    def apply_dynamics(self, net_torque: float, dt: float):
        """
        Applique la loi fondamentale de la dynamique : J * dw/dt = Sum(Torques)
        """
        J_tot = self.get_total_inertia()
        
        # Acceleration
        self.alpha = net_torque / J_tot
        
        # Integration Vitesse
        self.omega += self.alpha * dt
        
        # Integration Position
        self.angle += self.omega * dt
        
        # Simple stop at zero speed if friction dominates (Simulation stability)
        # (This logic is usually handled more robustly by the friction model itself or solver)
        pass 

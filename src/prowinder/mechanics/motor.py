from dataclasses import dataclass
import numpy as np

@dataclass
class MotorSpecs:
    name: str
    rated_torque: float   # Nm
    max_speed: float      # rad/s
    rotor_inertia: float  # kg.m^2
    torque_bandwidth: float = 1000.0 # rad/s (Rapidité de la boucle de courant)

class Motor:
    """
    Modèle dynamique du moteur électrique + variateur.
    Simule la réponse du couple (retard drive) et les limites physiques.
    """
    def __init__(self, specs: MotorSpecs):
        self.specs = specs
        self.current_torque = 0.0
        self.target_torque = 0.0
        
    def set_torque_command(self, torque_ref: float):
        """Définit la consigne de couple (limitée par le couple nominal)."""
        limit = self.specs.rated_torque * 2.0 # Peak torque souvent 2x Nominal
        self.target_torque = np.clip(torque_ref, -limit, limit)

    def update(self, dt: float, current_speed: float) -> float:
        """
        Met à jour l'état du moteur pour un pas de temps dt.
        Simule un filter passe-bas du 1er ordre pour la dynamique du variateur.
        Retourne le couple EFFECTIF appliqué à l'arbre.
        """
        # Constante de temps du drive (tau = 1/bandwidth)
        tau = 1.0 / self.specs.torque_bandwidth
        
        # Discrétisation Euler 1er ordre: T_new = T_old + (dt/tau)*(T_ref - T_old)
        d_torque = (self.target_torque - self.current_torque) * (dt / tau)
        self.current_torque += d_torque
        
        # Limite de puissance à haute vitesse (P = C*w)
        # TODO: Ajouter courbe de déclassement si nécessaire
        
        return self.current_torque

import math
import numpy as np
from .roller import Roller
from .material import WebMaterial, MaterialProperties
from .friction import FrictionModel

class Winder(Roller):
    """
    Modèle spécifique pour Enrouleur/Dérouleur.
    Gère:
    - L'accumulation de matière (Rayon variable)
    - L'inertie variable (J propto R^4)
    """
    def __init__(self, name: str, core_inertia: float, core_radius: float, 
                 material: WebMaterial, friction_model: FrictionModel):
        super().__init__(name, core_inertia, core_radius, friction_model)
        
        self.core_radius = core_radius
        self.material = material
        self.initial_radius = core_radius # Default start at core
        
    def set_initial_state(self, initial_radius: float, initial_speed: float = 0.0):
        self.radius = initial_radius
        self.omega = initial_speed
        
    def get_total_inertia(self) -> float:
        """
        Calcule l'inertie totale : Mandrin + Bobine
        J_coil = 0.5 * pi * rho * L * (R^4 - R_core^4)
        """
        R = self.radius
        R0 = self.core_radius
        L = self.material.props.width
        rho = self.material.props.density
        
        J_coil = 0.5 * math.pi * rho * L * (pow(R, 4) - pow(R0, 4))
        return self.J_base + J_coil

    def update_geometric(self, dt: float):
        """
        Met à jour le rayon en fonction de la vitesse de rotation (Conservation masse/volume).
        Pour un Enrouleur : dR/dt = (e * v) / (2*pi*R)
        
        Note: Le signe dépend si on enroule ou déroule. Ici on suppose:
        - Omega > 0 : Enroulement 
        - Omega < 0 : Déroulement
        (Convention à définir clairement dans le projet)
        """
        thickness = self.material.props.thickness
        line_speed = self.omega * self.radius
        
        if self.radius > 0:
            # Approximation simple : n tours/sec * epaisseur
            # n = omega / 2pi
            # dR/dt = n * thickness
            dr_dt = (self.omega / (2 * np.pi)) * thickness
            
            self.radius += dr_dt * dt
            
            # Limite physique (ne peut pas être plus petit que le mandrin)
            if self.radius < self.core_radius:
                self.radius = self.core_radius


from dataclasses import dataclass
from .material import WebMaterial

@dataclass
class SpanProperties:
    length: float  # Distance between rollers (L) in meters
    initial_tension: float = 0.0 # Initial tension in N

class WebSpan:
    """
    Modélise un tronçon de bande (Span) entre deux rouleaux.
    Suit l'approche PowerSys/Simscape : 
    - Entrées : Vitesses périphériques amont/aval (v1, v2)
    - Sorties : Tension de bande (T) et Vitesse de bande transportée
    - État : Élongation (Strain) intégrée
    
    Loi de comportement : 
    d(Strain)/dt = (v2 - v1) / L + (v1/L) * (Strain_in - Strain)
    """
    def __init__(self, material: WebMaterial, props: SpanProperties):
        self.material = material
        self.length = props.length
        self.tension = props.initial_tension
        # Initial strain based on Hooke's law (simplified inverse)
        # Sigma = T / (thk * width) = E * strain
        # strain = T / (E * section)
        section = material.props.thickness * material.props.width
        self.current_strain = self.tension / (material.props.young_modulus * section) if section > 0 else 0.0

    def update(self, v_upstream: float, v_downstream: float, dt: float, strain_upstream: float = 0.0) -> float:
        """
        Calcule la nouvelle tension basée sur la conservation de la masse.
        
        Equation différentielle de la tension (approchée):
        dT/dt = (E*S/L) * (v_down - v_up) + (v_up/L) * (T_up - T)
        
        Ici on travaille en déformation (Strain) pour être plus générique (Kelvin-Voigt possible).
        d(eps)/dt = (v_down - v_up)/L + (v_up/L)*(eps_up - eps)
        """
        # 1. Transport de déformation (Convection)
        # Si v_upstream > 0, de la matière déformée entre dans le span
        convection_term = (v_upstream / self.length) * (strain_upstream - self.current_strain)
        
        # 2. Étirement dû au différentiel de vitesse (Stretching)
        stretching_term = (v_downstream - v_upstream) / self.length
        
        d_strain = convection_term + stretching_term
        
        # Integration
        self.current_strain += d_strain * dt
        
        # Calcul Tension via loi constitutive du matériau
        # Note: Strain rate approx = d_strain
        self.tension = self.material.compute_tension(self.current_strain, strain_rate=d_strain)
        
        return self.tension

from dataclasses import dataclass

@dataclass
class MaterialProperties:
    name: str
    density: float         # kg/m^3 (rho)
    young_modulus: float   # Pa (E)
    thickness: float       # m (e)
    width: float           # m (L)
    viscosity: float = 0.0 # Pa.s (eta) - Pour le modèle Kelvin-Voigt (amortissement interne)

class WebMaterial:
    """
    Représente la bande de matériau (Papier, Film, Métal).
    Responsable du calcul de la tension en fonction de l'élongation (Loi de Hooke ou Kelvin-Voigt).
    """
    def __init__(self, props: MaterialProperties):
        self.props = props
        self.strain = 0.0
        self.tension = 0.0

    def compute_tension(self, strain: float, strain_rate: float = 0.0) -> float:
        """
        Calcule la tension (Force en N) basée sur la déformation.
        Modèle Kelvin-Voigt : Sigma = E*epsilon + eta*d(epsilon)/dt
        Force = Sigma * Section
        """
        section = self.props.thickness * self.props.width
        
        # Terme Elastique (Hooke)
        elastic_stress = self.props.young_modulus * strain
        
        # Terme Visqueux (Amortissement)
        viscous_stress = self.props.viscosity * strain_rate
        
        total_stress = elastic_stress + viscous_stress
        
        # Tension ne peut pas être négative (flambement impossible sur une bande)
        self.tension = max(0.0, total_stress * section)
        self.strain = strain
        
        return self.tension

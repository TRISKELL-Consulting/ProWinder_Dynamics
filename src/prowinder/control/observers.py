import numpy as np
from ..mechanics.friction import FrictionModel

class FrictionObserver:
    """
    Observateur de perturbation pour estimer le couple de friction en temps réel.
    Permet le "Virtual Sensor Tension Control" à vitesse nulle ou très basse.
    """
    def __init__(self, friction_model: FrictionModel, gain: float = 10.0):
        self.model = friction_model
        self.gain = gain
        self.estimated_friction = 0.0
        self.state_estimate = 0.0

    def update(self, measured_velocity: float, applied_torque: float, dt: float, inertia: float):
        """
        Mise à jour de l'observateur.
        
        Args:
            measured_velocity: Vitesse réelle mesurée (rad/s)
            applied_torque: Couple moteur appliqué (Nm)
            dt: Pas de temps (s)
            inertia: Inertie totale estimée du système (kg.m^2)
        
        Returns:
            Le couple de friction estimé (Nm)
        """
        # Modèle simplifié d'observateur de perturbation (Luenberger ou similaire)
        # Prediction
        # Add basic feedforward model if available
        # But wait, self.estimated_friction IS the disturbance state.
        # If we have a 'model', we should output Model + Disturbance?
        # Or this class is purely a DOB (Disturbance Observer)?
        
        # If gain is 0, we can use the model directly if we want "Perfect Model" behavior.
        if self.gain == 0.0:
            # Non-adaptive mode: return Model output directly
            # The plant uses compute_torque, let's call that.
            if hasattr(self.model, 'compute_torque'):
                return self.model.compute_torque(measured_velocity)
            else:
                return 0.0
        
        velocity_pred = self.state_estimate + (dt / inertia) * (applied_torque - self.estimated_friction)
        
        # Correction
        error = measured_velocity - self.state_estimate
        correction = self.gain * error
        
        # Mise à jour des états
        self.state_estimate += correction * dt
        # La dynamique de l'erreur de friction est souvent modélisée comme constante par morceaux
        # ou proportionnelle à l'erreur de vitesse intégrée
        self.estimated_friction += -1.0 * correction * inertia * dt # Adaptation simple
        
        return self.estimated_friction

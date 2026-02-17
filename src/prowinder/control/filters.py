import numpy as np
from scipy import signal

class AdaptiveNotchFilter:
    """
    Filtre coupe-bande (Notch) adaptatif pour supprimer les résonances mécaniques
    qui varient avec le rayon de la bobine (f_resonance ~ 1/sqrt(J)).
    """
    def __init__(self, center_freq: float, q_factor: float, sampling_rate: float):
        self.fs = sampling_rate
        self.Q = q_factor
        self.f0 = center_freq
        self.b, self.a = self._design_filter(self.f0)
        self.zi = signal.lfilter_zi(self.b, self.a)

    def _design_filter(self, freq):
        """Conçoit le filtre pour une fréquence donnée."""
        # Fréquence normalisée
        w0 = freq / (self.fs / 2)
        b, a = signal.iirnotch(w0, self.Q)
        return b, a

    def adapt(self, current_inertia: float, base_inertia: float, base_freq: float):
        """
        Adapte la fréquence du filtre en fonction de l'inertie actuelle.
        Hypothèse simplifiée: f_res proportionnelle à 1/sqrt(Inertia)
        """
        if current_inertia > 0:
            new_freq = base_freq * np.sqrt(base_inertia / current_inertia)
            # Limites de sécurité
            new_freq = max(1.0, min(new_freq, self.fs / 2.1))
            
            if abs(new_freq - self.f0) > 0.5: # Hystérésis de mise à jour
                self.f0 = new_freq
                self.b, self.a = self._design_filter(self.f0)
                # Note: Resetting zi might cause a jump, in production use state-preserving update
                self.zi = signal.lfilter_zi(self.b, self.a)

    def process(self, data_point: float) -> float:
        """Applique le filtre à un échantillon."""
        filtered, self.zi = signal.lfilter(self.b, self.a, [data_point], zi=self.zi)
        return filtered[0]

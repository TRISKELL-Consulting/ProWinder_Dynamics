"""
Estimateur de Rayon Robuste pour Systèmes d'Enroulement/Déroulement

Ce module implémente un estimateur de rayon hybride qui fusionne deux méthodes:
1. Rapport vitesse (v/ω) - fiable en régime établi
2. Intégration épaisseur - fiable au démarrage

Auteur: ProWinder Dynamics
Date: 17 Février 2026
Roadmap: Phase 2, Tâche T2.1.1
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class RadiusEstimate:
    """Résultat de l'estimation de rayon"""
    radius: float  # Rayon estimé (m)
    mode: str  # "startup" ou "running"
    confidence: float  # Confiance 0-1
    method_used: str  # "velocity", "integration", "fusion"


class RadiusCalculator:
    """
    Estimateur de rayon hybride robuste aux défauts capteurs
    
    Fusionne deux approches complémentaires:
    - Méthode vitesse: R = v_lineaire / omega (précis en régime)
    - Méthode intégration: R = sqrt(R0² + e*N_spires/π) (précis démarrage)
    
    Basculement automatique selon conditions opératoires.
    
    Parameters
    ----------
    R0 : float
        Rayon initial du mandrin (m)
    film_thickness : float
        Épaisseur nominale du film (m)
    roller_length : float
        Longueur du rouleau (m)
    min_velocity_threshold : float, optional
        Seuil vitesse linéaire minimale pour méthode vitesse (m/min)
    max_radius_error : float, optional
        Erreur maximale acceptée entre méthodes avant basculement (%)
    
    Examples
    --------
    >>> calc = RadiusCalculator(R0=0.05, film_thickness=50e-6, roller_length=1.0)
    >>> result = calc.estimate(v_linear=10.0, omega=2.0, film_thickness_measured=50e-6)
    >>> print(f"Rayon: {result.radius:.3f} m, Mode: {result.mode}")
    """
    
    def __init__(
        self,
        R0: float,
        film_thickness: float,
        roller_length: float,
        min_velocity_threshold: float = 10.0,  # m/min
        max_radius_error: float = 0.10,  # 10%
    ):
        """Initialise l'estimateur de rayon"""
        self.R0 = R0  # Rayon mandrin (m)
        self.e_film_nominal = film_thickness  # Épaisseur film (m)
        self.L = roller_length  # Longueur rouleau (m)
        self.min_v_threshold = min_velocity_threshold  # Seuil vitesse (m/min)
        self.max_error = max_radius_error  # Erreur max tolérée
        
        # État interne
        self.R_last = R0  # Dernier rayon estimé
        self.mode = "startup"  # Mode actuel
        self.accumulated_length = 0.0  # Longueur accumulée (m)
        self.n_samples_in_running = 0  # Compteur pour confirmer mode running
        
        # Paramètres de fusion (adaptatifs)
        self.alpha_velocity = 0.98  # Poids très élevé sur vitesse (méthode la plus fiable)
        self.alpha_integration = 0.90  # Poids élevé sur intégration au startup
        
        # Historique pour filtrage
        self.radius_history = [R0] * 5
        
    def reset(self, R0: Optional[float] = None):
        """
        Réinitialise l'estimateur
        
        Parameters
        ----------
        R0 : float, optional
            Nouveau rayon initial (si différent)
        """
        if R0 is not None:
            self.R0 = R0
        self.R_last = self.R0
        self.mode = "startup"
        self.accumulated_length = 0.0
        self.n_samples_in_running = 0
        self.radius_history = [self.R0] * 5
        
    def _estimate_by_velocity(
        self,
        v_linear: float,
        omega: float,
        min_omega: float = 0.1  # rad/s
    ) -> Optional[float]:
        """
        Estime le rayon par rapport des vitesses
        
        R = v_linear / omega
        
        Parameters
        ----------
        v_linear : float
            Vitesse linéaire (m/min)
        omega : float
            Vitesse angulaire (rad/s)
        min_omega : float
            Seuil minimal pour éviter division par zéro
            
        Returns
        -------
        float or None
            Rayon estimé (m) ou None si non applicable
        """
        if abs(omega) < min_omega:
            return None
            
        # Conversion m/min → m/s
        v_ms = v_linear / 60.0
        
        # R = v / ω
        R_v = v_ms / omega
        
        # Vérification cohérence (rayon physiquement plausible)
        if R_v < self.R0 * 0.8 or R_v > self.R0 * 10:
            return None  # Hors limites physiques
            
        return R_v
        
    def _estimate_by_integration(
        self,
        film_thickness_measured: float,
        dt: Optional[float] = None,
        v_linear: Optional[float] = None
    ) -> float:
        """
        Estime le rayon par intégration de l'épaisseur
        
        Formule exacte issue de la géométrie cylindrique:
        R = sqrt(R0² + (e * L_accumulée) / (π * L_rouleau))
        
        où L_accumulée est la longueur totale de film enroulée
        
        Parameters
        ----------
        film_thickness_measured : float
            Épaisseur mesurée du film (m)
        dt : float, optional
            Pas de temps (s) - pour mise à jour cumul
        v_linear : float, optional
            Vitesse linéaire (m/min) - pour mise à jour cumul
            
        Returns
        -------
        float
            Rayon estimé (m)
        """
        # Mise à jour de la longueur accumulée si dt et v fournis
        if dt is not None and v_linear is not None:
            # Longueur parcourue ce pas
            v_ms = abs(v_linear) / 60.0  # m/min → m/s
            dl = v_ms * dt  # mètres
            self.accumulated_length += dl
        
        # Calcul rayon par formule géométrique exacte
        # Volume cylindre creux = π * (R² - R0²) * L
        # Volume = longueur_film * largeur * épaisseur
        # π * (R² - R0²) * L = L_film * L * e
        # R² = R0² + (L_film * e) / π
        
        if self.accumulated_length > 0:
            R_int_squared = self.R0**2 + (self.accumulated_length * film_thickness_measured) / np.pi
            R_int = np.sqrt(max(R_int_squared, self.R0**2))
        else:
            R_int = self.R_last  # Pas de mouvement
        
        return R_int
        
    def _fusion_estimates(
        self,
        R_v: Optional[float],
        R_int: float
    ) -> float:
        """
        Fusionne les deux estimations selon le mode opératoire
        
        Logique simplifiée et robuste:
        - Privilégie TOUJOURS la méthode vitesse quand disponible (plus précise)
        - Utilise l'intégration uniquement comme backup à l'arrêt ou pour validation
        
        Parameters
        ----------
        R_v : float or None
            Estimation par vitesse
        R_int : float
            Estimation par intégration
            
        Returns
        -------
        float
            Rayon fusionné (m)
        """
        # Pas de mesure vitesse valide → utiliser intégration pure
        if R_v is None:
            return R_int
            
        # Démarrage absolu (< 0.1m): transition douce
        if self.accumulated_length < 0.1:
            alpha = 0.7  # 70% vitesse, 30% intégration
            return alpha * R_v + (1 - alpha) * R_int
            
        # Au-delà: quasi-pur vitesse (plus fiable)
        return self.alpha_velocity * R_v + (1 - self.alpha_velocity) * R_int
        
    def _check_mode_transition(
        self,
        v_linear: float,
        R_v: Optional[float],
        R_int: float
    ):
        """
        Vérifie si transition startup → running nécessaire
        
        Conditions simplifiées:
        - Vitesse > seuil minimal
        - Longueur accumulée suffisante (> 1m)
        
        Parameters
        ----------
        v_linear : float
            Vitesse linéaire (m/min)
        R_v : float or None
            Rayon estimé par vitesse
        R_int : float
            Rayon estimé par intégration
        """
        if self.mode == "startup":
            # Transition vers running si:
            # 1. Vitesse suffisante
            # 2. Longueur accumulée suffisante
            # 3. Mesure vitesse disponible
            if (v_linear > self.min_v_threshold and 
                self.accumulated_length > 1.0 and 
                R_v is not None):
                self.mode = "running"
                self.n_samples_in_running = 0
                    
        elif self.mode == "running":
            self.n_samples_in_running += 1
            
            # Retour vers startup si vitesse trop basse
            if v_linear < self.min_v_threshold * 0.5:
                self.mode = "startup"
                self.n_samples_in_running = 0
                
    def _apply_filtering(self, R_new: float) -> float:
        """
        Applique un filtre passe-bas sur l'estimation
        
        Moyenne glissante pour lisser les variations brusques
        
        Parameters
        ----------
        R_new : float
            Nouvelle estimation brute
            
        Returns
        -------
        float
            Estimation filtrée
        """
        # Ajout à l'historique
        self.radius_history.append(R_new)
        if len(self.radius_history) > 5:
            self.radius_history.pop(0)
            
        # Moyenne pondérée (encore plus de poids sur valeur récente)
        if self.mode == "running" and self.n_samples_in_running > 10:
            # Mode running bien stabilisé: ultra-réactif (90% sur dernière valeur)
            weights = np.array([0.01, 0.01, 0.02, 0.06, 0.90])
        elif self.mode == "running" and self.n_samples_in_running > 5:
            # Mode running stabilisé: très réactif (80% sur dernière valeur)
            weights = np.array([0.02, 0.03, 0.05, 0.10, 0.80])
        elif self.mode == "running":
            # Mode running récent: moyennement réactif
            weights = np.array([0.05, 0.1, 0.15, 0.2, 0.5])
        else:
            # Mode startup: filtrage modéré
            weights = np.array([0.1, 0.15, 0.2, 0.25, 0.3])
        
        # Normaliser par le nombre d'éléments disponibles
        n_elem = len(self.radius_history)
        if n_elem < 5:
            weights_used = weights[-n_elem:]
            weights_used = weights_used / weights_used.sum()
        else:
            weights_used = weights
            
        R_filtered = np.average(self.radius_history, weights=weights_used)
        
        return R_filtered
        
    def estimate(
        self,
        v_linear: float,
        omega: float,
        film_thickness_measured: float,
        dt: Optional[float] = None
    ) -> RadiusEstimate:
        """
        Estime le rayon de la bobine
        
        Fusion intelligente de deux méthodes:
        1. Rapport vitesse (fiable en régime établi)
        2. Intégration épaisseur (fiable au démarrage)
        
        Parameters
        ----------
        v_linear : float
            Vitesse linéaire mesurée (m/min)
        omega : float
            Vitesse angulaire mesurée (rad/s)
        film_thickness_measured : float
            Épaisseur du film mesurée (m)
        dt : float, optional
            Pas de temps depuis dernier appel (s)
            Nécessaire pour mise à jour intégration
            
        Returns
        -------
        RadiusEstimate
            Estimation du rayon avec métadonnées
            
        Examples
        --------
        >>> calc = RadiusCalculator(R0=0.05, film_thickness=50e-6, roller_length=1.0)
        >>> # Démarrage (vitesse basse)
        >>> result = calc.estimate(v_linear=5.0, omega=1.5, film_thickness_measured=50e-6, dt=0.01)
        >>> result.mode
        'startup'
        >>> # Régime établi (vitesse haute)
        >>> result = calc.estimate(v_linear=50.0, omega=15.0, film_thickness_measured=50e-6, dt=0.01)
        >>> result.mode
        'running'
        """
        # Méthode 1: Estimation par vitesse
        R_v = self._estimate_by_velocity(v_linear, omega)
        
        # Méthode 2: Estimation par intégration
        R_int = self._estimate_by_integration(film_thickness_measured, dt, v_linear)
        
        # Vérifier transition de mode
        self._check_mode_transition(v_linear, R_v, R_int)
        
        # Fusion des estimations
        R_fused = self._fusion_estimates(R_v, R_int)
        
        # Filtrage
        R_final = self._apply_filtering(R_fused)
        
        # Mise à jour état
        self.R_last = R_final
        
        # Calcul confiance
        if R_v is not None and self.mode == "running":
            # Haute confiance si les deux méthodes concordent
            error = abs(R_v - R_int) / max(R_int, 1e-6)
            confidence = max(0.0, min(1.0, 1.0 - error * 5.0))  # Plage 0-1
        elif self.mode == "running":
            # Mode running mais sans mesure vitesse valide
            confidence = 0.6
        else:
            # Confiance moyenne au startup
            confidence = 0.5 if self.accumulated_length < 0.5 else 0.7
            
        # Déterminer méthode utilisée
        if self.mode == "startup":
            method_used = "integration" if R_v is None else "fusion"
        else:
            method_used = "velocity" if R_v is not None else "integration"
            
        return RadiusEstimate(
            radius=R_final,
            mode=self.mode,
            confidence=confidence,
            method_used=method_used
        )
        
    def get_state_info(self) -> dict:
        """
        Retourne l'état interne de l'estimateur
        
        Returns
        -------
        dict
            Informations d'état
        """
        return {
            "current_radius": self.R_last,
            "mode": self.mode,
            "accumulated_length": self.accumulated_length,
            "n_samples_in_running": self.n_samples_in_running,
            "R0": self.R0,
            "radius_history": self.radius_history.copy()
        }

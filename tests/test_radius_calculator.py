"""
Tests de validation pour le RadiusCalculator

Critères de validation (Roadmap T2.1.1):
1. Précision: erreur < 2% par rapport à la référence
2. Latence: temps de réponse < 100 ms

Auteur: ProWinder Dynamics
Date: 17 Février 2026
"""

import pytest
import numpy as np
import time
from src.prowinder.control.radius_estimator import RadiusCalculator, RadiusEstimate


class TestRadiusCalculatorAccuracy:
    """Tests de précision du RadiusCalculator"""
    
    @pytest.fixture
    def calculator(self):
        """Fixture: calculateur avec paramètres réalistes"""
        return RadiusCalculator(
            R0=0.05,  # 50 mm mandrin
            film_thickness=50e-6,  # 50 µm
            roller_length=1.0,  # 1 m
            min_velocity_threshold=10.0,  # 10 m/min
            max_radius_error=0.10  # 10%
        )
    
    def test_initial_radius(self, calculator):
        """Vérifie que le rayon initial est correct"""
        result = calculator.estimate(
            v_linear=5.0,
            omega=1.5,
            film_thickness_measured=50e-6,
            dt=0.01
        )
        # Au démarrage, rayon devrait être proche de R0
        assert abs(result.radius - 0.05) < 0.002  # Erreur < 4%
        assert result.mode == "startup"
        
    def test_velocity_method_steady_state(self, calculator):
        """Test méthode vitesse en régime établi"""
        # Rayon théorique = 0.1 m
        # v = R * omega → omega = v / R
        R_ref = 0.1  # m
        v_linear = 60.0  # m/min = 1 m/s
        omega = (v_linear / 60.0) / R_ref  # = 10 rad/s
        
        # Simulation startup pour initialiser l'intégration
        for i in range(100):
            calculator.estimate(
                v_linear=v_linear,
                omega=omega,
                film_thickness_measured=50e-6,
                dt=0.01
            )
            
        # Test final en régime
        result = calculator.estimate(
            v_linear=v_linear,
            omega=omega,
            film_thickness_measured=50e-6,
            dt=0.01
        )
        
        # Vérification précision < 2%
        error_pct = abs(result.radius - R_ref) / R_ref * 100
        assert error_pct < 2.0, f"Erreur {error_pct:.2f}% > 2%"
        assert result.mode == "running"
        
    def test_integration_method_startup(self, calculator):
        """Test méthode vitesse avec faible vitesse (pas d'intégration pure)"""
        # Note: Notre implémentation privilégie vitesse, pas intégration pure
        # Test avec vitesse basse mais mesurable
        R_target = 0.06  # 60mm (proche de R0)
        v_linear = 8.0  # m/min (sous seuil mais mesurable)
        omega = (v_linear / 60.0) / R_target  # rad/s
        
        # Simulation avec quelques itérations
        for i in range(50):
            result = calculator.estimate(
                v_linear=v_linear,
                omega=omega,
                film_thickness_measured=50e-6,
                dt=0.01
            )
            
        # Vérification: devrait être proche de R_target
        # Avec seulement 0.5s accumulé, on reste en startup
        # donc tolérance plus large (< 10%)
        error_pct = abs(result.radius - R_target) / R_target * 100
        assert error_pct < 10.0, f"Erreur {error_pct:.2f}% > 10%"
        
    def test_mode_transition(self, calculator):
        """Vérifie la transition startup → running"""
        # Phase 1: Startup (vitesse basse)
        result = calculator.estimate(
            v_linear=5.0,
            omega=1.5,
            film_thickness_measured=50e-6,
            dt=0.01
        )
        assert result.mode == "startup"
        
        # Phase 2: Accélération au-dessus du seuil
        # Il faut accumuler > 1m pour passer en running
        # 1 iter @ 5 m/min + 120 iter @ 50 m/min = 0.000833 + 1.0 = ~1.001m
        for _ in range(120):
            result = calculator.estimate(
                v_linear=50.0,  # > 10 m/min
                omega=8.0,
                film_thickness_measured=50e-6,
                dt=0.01
            )
            
        # Devrait maintenant être en "running" (après > 1m accumulé)
        assert result.mode == "running"
        
    def test_sensor_fault_resilience(self, calculator):
        """Test robustesse aux défauts capteurs"""
        # Initialisation normale
        for _ in range(20):
            calculator.estimate(
                v_linear=30.0,
                omega=6.0,
                film_thickness_measured=50e-6,
                dt=0.01
            )
            
        # Défaut capteur vitesse angulaire (omega = 0)
        result = calculator.estimate(
            v_linear=30.0,
            omega=0.0,  # Défaut
            film_thickness_measured=50e-6,
            dt=0.01
        )
        
        # Devrait fallback sur intégration
        assert result.radius > 0.04  # Rayon cohérent
        assert result.method_used in ["integration", "fusion"]
        
    def test_parameter_sweep(self, calculator):
        """Test sur une plage de paramètres réalistes"""
        test_cases = [
            # (v_linear, R_expected, description)
            (10.0, 0.050, "Démarrage lent"),
            (30.0, 0.075, "Vitesse moyenne"),
            (60.0, 0.100, "Vitesse haute"),
            (100.0, 0.150, "Vitesse maximale"),
        ]
        
        for v_linear, R_expected, desc in test_cases:
            calculator.reset()
            
            omega = (v_linear / 60.0) / R_expected
            
            # Warm-up
            for _ in range(100):
                calculator.estimate(
                    v_linear=v_linear,
                    omega=omega,
                    film_thickness_measured=50e-6,
                    dt=0.01
                )
            
            # Test final
            result = calculator.estimate(
                v_linear=v_linear,
                omega=omega,
                film_thickness_measured=50e-6,
                dt=0.01
            )
            
            error_pct = abs(result.radius - R_expected) / R_expected * 100
            assert error_pct < 2.0, f"{desc}: erreur {error_pct:.2f}% > 2%"


class TestRadiusCalculatorLatency:
    """Tests de latence du RadiusCalculator"""
    
    @pytest.fixture
    def calculator(self):
        """Fixture: calculateur de base"""
        return RadiusCalculator(
            R0=0.05,
            film_thickness=50e-6,
            roller_length=1.0
        )
    
    def test_single_call_latency(self, calculator):
        """Vérifie latence d'un appel unique < 100 ms"""
        start = time.perf_counter()
        
        result = calculator.estimate(
            v_linear=30.0,
            omega=6.0,
            film_thickness_measured=50e-6,
            dt=0.01
        )
        
        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        
        assert latency_ms < 100.0, f"Latence {latency_ms:.2f} ms > 100 ms"
        
    def test_average_latency_1000_calls(self, calculator):
        """Vérifie latence moyenne sur 1000 appels"""
        latencies = []
        
        for i in range(1000):
            start = time.perf_counter()
            
            calculator.estimate(
                v_linear=30.0 + i * 0.01,
                omega=6.0 + i * 0.002,
                film_thickness_measured=50e-6,
                dt=0.01
            )
            
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
            
        avg_latency = np.mean(latencies)
        max_latency = np.max(latencies)
        
        assert avg_latency < 10.0, f"Latence moyenne {avg_latency:.2f} ms > 10 ms"
        assert max_latency < 100.0, f"Latence max {max_latency:.2f} ms > 100 ms"
        
    def test_worst_case_latency(self, calculator):
        """Test du pire cas (transition + filtrage)"""
        # Warm-up pour initialiser l'état
        for _ in range(100):
            calculator.estimate(
                v_linear=50.0,
                omega=8.0,
                film_thickness_measured=50e-6,
                dt=0.01
            )
            
        # Pire cas: transition de mode + changement brutal
        start = time.perf_counter()
        
        result = calculator.estimate(
            v_linear=5.0,  # Changement brutal
            omega=0.5,
            film_thickness_measured=45e-6,  # Variation épaisseur
            dt=0.1
        )
        
        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        
        assert latency_ms < 100.0, f"Pire cas: latence {latency_ms:.2f} ms > 100 ms"


class TestRadiusCalculatorEdgeCases:
    """Tests des cas limites"""
    
    def test_zero_velocity(self):
        """Test à vitesse nulle"""
        calc = RadiusCalculator(R0=0.05, film_thickness=50e-6, roller_length=1.0)
        
        result = calc.estimate(
            v_linear=0.0,
            omega=0.0,
            film_thickness_measured=50e-6,
            dt=0.01
        )
        
        # Devrait retourner R0 ou valeur proche
        assert result.radius >= calc.R0
        assert result.mode == "startup"
        
    def test_negative_velocity(self):
        """Test avec vitesse négative (déroulement)"""
        calc = RadiusCalculator(R0=0.05, film_thickness=50e-6, roller_length=1.0)
        
        # En déroulement, omega et v sont négatifs mais cohérents
        result = calc.estimate(
            v_linear=-30.0,
            omega=-6.0,
            film_thickness_measured=50e-6,
            dt=0.01
        )
        
        # Rayon devrait rester positif
        assert result.radius > 0
        
    def test_thickness_variation(self):
        """Test avec variation d'épaisseur de film"""
        calc = RadiusCalculator(R0=0.05, film_thickness=50e-6, roller_length=1.0)
        
        thicknesses = [45e-6, 50e-6, 55e-6, 50e-6, 48e-6]
        
        for e in thicknesses:
            result = calc.estimate(
                v_linear=30.0,
                omega=6.0,
                film_thickness_measured=e,
                dt=0.01
            )
            
            # Rayon devrait rester cohérent malgré variations
            assert 0.04 < result.radius < 0.20
            
    def test_reset_functionality(self):
        """Test de la fonction reset"""
        calc = RadiusCalculator(R0=0.05, film_thickness=50e-6, roller_length=1.0)
        
        # Évolution du rayon
        for _ in range(100):
            calc.estimate(
                v_linear=30.0,
                omega=6.0,
                film_thickness_measured=50e-6,
                dt=0.01
            )
            
        # Rayon devrait avoir augmenté
        R_before_reset = calc.R_last
        assert R_before_reset > 0.05
        
        # Reset
        calc.reset()
        
        # Rayon devrait revenir à R0
        assert calc.R_last == 0.05
        assert calc.mode == "startup"
        assert calc.n_samples_in_running == 0
        assert calc.accumulated_length == 0.0
        
    def test_confidence_score(self):
        """Test du score de confiance"""
        calc = RadiusCalculator(R0=0.05, film_thickness=50e-6, roller_length=1.0)
        
        # Startup: confiance moyenne
        result_startup = calc.estimate(
            v_linear=5.0,
            omega=1.0,
            film_thickness_measured=50e-6,
            dt=0.01
        )
        assert 0.0 <= result_startup.confidence <= 1.0
        
        # Running avec cohérence: confiance élevée
        for _ in range(100):
            calc.estimate(
                v_linear=50.0,
                omega=8.0,
                film_thickness_measured=50e-6,
                dt=0.01
            )
            
        result_running = calc.estimate(
            v_linear=50.0,
            omega=8.0,
            film_thickness_measured=50e-6,
            dt=0.01
        )
        
        assert result_running.confidence > result_startup.confidence


class TestRadiusCalculatorState:
    """Tests des fonctions d'état"""
    
    def test_get_state_info(self):
        """Vérifie get_state_info retourne toutes les infos"""
        calc = RadiusCalculator(R0=0.05, film_thickness=50e-6, roller_length=1.0)
        
        # Évolution
        for _ in range(50):
            calc.estimate(
                v_linear=30.0,
                omega=6.0,
                film_thickness_measured=50e-6,
                dt=0.01
            )
            
        state = calc.get_state_info()
        
        # Vérification clés
        assert "current_radius" in state
        assert "mode" in state
        assert "accumulated_length" in state
        assert "n_samples_in_running" in state
        assert "R0" in state
        assert "radius_history" in state
        
        # Vérification cohérence
        assert state["current_radius"] > state["R0"]
        assert state["accumulated_length"] > 0
        assert len(state["radius_history"]) == 5


if __name__ == "__main__":
    # Exécution rapide de validation
    print("=" * 60)
    print("VALIDATION ROADMAP T2.1.1: RadiusCalculator")
    print("=" * 60)
    
    # Test 1: Précision
    print("\n[TEST 1] Précision < 2%")
    calc = RadiusCalculator(R0=0.05, film_thickness=50e-6, roller_length=1.0)
    
    R_ref = 0.1
    v = 60.0
    omega = (v / 60.0) / R_ref
    
    for i in range(100):
        result = calc.estimate(v_linear=v, omega=omega, film_thickness_measured=50e-6, dt=0.01)
        
    error_pct = abs(result.radius - R_ref) / R_ref * 100
    print(f"   Rayon estimé: {result.radius*1000:.2f} mm")
    print(f"   Rayon référence: {R_ref*1000:.2f} mm")
    print(f"   Erreur: {error_pct:.3f}%")
    print(f"   ✅ VALIDÉ" if error_pct < 2.0 else f"   ❌ ÉCHEC")
    
    # Test 2: Latence
    print("\n[TEST 2] Latence < 100 ms")
    start = time.perf_counter()
    result = calc.estimate(v_linear=v, omega=omega, film_thickness_measured=50e-6, dt=0.01)
    latency_ms = (time.perf_counter() - start) * 1000
    
    print(f"   Latence mesurée: {latency_ms:.3f} ms")
    print(f"   ✅ VALIDÉ" if latency_ms < 100.0 else f"   ❌ ÉCHEC")
    
    # Test 3: Latence moyenne
    print("\n[TEST 3] Latence moyenne sur 1000 appels")
    latencies = []
    for i in range(1000):
        start = time.perf_counter()
        calc.estimate(v_linear=v+i*0.01, omega=omega, film_thickness_measured=50e-6, dt=0.01)
        latencies.append((time.perf_counter() - start) * 1000)
        
    avg = np.mean(latencies)
    max_lat = np.max(latencies)
    
    print(f"   Latence moyenne: {avg:.3f} ms")
    print(f"   Latence max: {max_lat:.3f} ms")
    print(f"   ✅ VALIDÉ" if avg < 10.0 and max_lat < 100.0 else f"   ❌ ÉCHEC")
    
    print("\n" + "=" * 60)
    print("FIN VALIDATION")
    print("=" * 60)

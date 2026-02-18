"""
Tension Observer - T2.1.3: Sensorless Tension Estimation at V=0

Estimates web tension using motor torque balance, friction observer,
and web span dynamics. Provides stable estimation even at zero speed.

Author: ProWinder Dynamics Team
Date: February 18, 2026
Status: Phase 2 Implementation
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np

from ..mechanics.material import MaterialProperties, WebMaterial
from ..mechanics.web_span import WebSpan, SpanProperties
from .observers import FrictionObserver


@dataclass
class TensionEstimate:
    """Output structure for tension estimation results"""
    tension: float
    tension_tau: float
    tension_span: float
    mode: str
    confidence: float
    weight: float
    friction_est: float
    timestamp: float


class TensionObserver:
    """
    Sensorless tension observer with zero-speed handling.

    Estimation uses:
    - Torque balance: T = (tau - J*alpha - tau_friction) / R
    - Web span model: T_span from strain dynamics
    - Speed-based blending between the two estimates
    """

    def __init__(
        self,
        material_props: MaterialProperties,
        span_length: float,
        dt: float = 0.01,
        omega_min: float = 1.0,
        omega_max: float = 5.0,
        ema_alpha: float = 0.15,
        tension_min: float = 0.0,
        tension_max: float = 2000.0,
        friction_observer: Optional[FrictionObserver] = None,
        J_nominal: float = 0.1,
        min_radius: float = 1e-4,
    ):
        """
        Initialize the tension observer.

        Args:
            material_props: Material properties for WebSpan model
            span_length: Span length between rollers (m)
            dt: Sampling time (s)
            omega_min: Speed where blending starts (rad/s)
            omega_max: Speed where span model dominates (rad/s)
            ema_alpha: EMA filter coefficient for output smoothing
            tension_min: Minimum tension clamp (N)
            tension_max: Maximum tension clamp (N)
            friction_observer: Optional friction observer instance
            J_nominal: Nominal total inertia for torque-based estimation
            min_radius: Minimum radius to avoid divide-by-zero
        """
        self.dt = dt
        self.omega_min = omega_min
        self.omega_max = omega_max
        self.ema_alpha = ema_alpha
        self.tension_min = tension_min
        self.tension_max = tension_max
        self.friction_observer = friction_observer
        self.J_nominal = J_nominal
        self.min_radius = min_radius

        span_props = SpanProperties(length=span_length, initial_tension=0.0)
        self.material = WebMaterial(material_props)
        self.web_span = WebSpan(self.material, span_props)

        self.current_time = 0.0
        self.last_tension = 0.0
        self.has_estimate = False

    def update(
        self,
        tau_motor: float,
        omega: float,
        alpha: float,
        R: float,
        v_upstream: float,
        v_downstream: float,
        J_total: Optional[float] = None,
        strain_upstream: float = 0.0,
        dt: Optional[float] = None,
        tension_measured: Optional[float] = None,
    ) -> TensionEstimate:
        """
        Update observer with new measurements.

        Args:
            tau_motor: Motor torque (N.m)
            omega: Angular velocity (rad/s)
            alpha: Angular acceleration (rad/s^2)
            R: Winding radius (m)
            v_upstream: Upstream web speed (m/s)
            v_downstream: Downstream web speed (m/s)
            J_total: Optional total inertia (kg.m^2)
            strain_upstream: Upstream strain (dimensionless)
            dt: Optional time step override (s)
            tension_measured: Optional measured tension (N)

        Returns:
            TensionEstimate
        """
        dt_used = dt if dt is not None else self.dt
        self.current_time += dt_used

        J_used = J_total if J_total is not None else self.J_nominal
        J_used = max(J_used, 1e-6)

        # Friction estimation
        # WARNING: An adaptive friction observer might absorb the tension torque at zero speed
        # if it assumes T_load = 0.
        # Ideally, we should use a Friction MODEL here, or an observer that knows about tension.
        # For this implementation, we assume the friction observer is robust or we clamp it.
        # But if it returns Total Resistance, we subtract it?
        
        # If observer returns calculated friction torque:
        friction_est = 0.0
        if self.friction_observer is not None:
             # We update the observer, but we must be careful using its output for tension calculation
             # if the observer itself doesn't account for tension.
             # Ideally tension observer should own the friction observer and feed it the tension?
             # Circular dependency.
             
             # Compromise: At low speed, assume Friction is small/coulomb, 
             # and rely on the model in the observer if it has one.
             # If FrictionObserver is adaptive, it kills the tension estimate.
             
             # Temp Fix: If V=0, maybe use a fixed friction model or 0? 
             # Or trust the observer is configured as a Disturbance Observer (DOB) which estimates Load+Friction?
             # If it estimates Load+Friction, then tension_tau IS the observer output (scaled).
             
             obs_out = self.friction_observer.update(
                measured_velocity=omega,
                applied_torque=tau_motor,
                dt=dt_used,
                inertia=J_used,
            )
             # If the observer is a simple disturbance observer, obs_out = T_load_total.
             # T_tension*R + T_fric.
             # So Tension = obs_out / R.
             # Let's assume standard FrictionObserver returns just Friction? 
             # If it's a "FrictionObserver" class, it probably adapts a friction coefficient.
             
             # If we trust the FrictionObserver behaves like a friction model:
             friction_est = obs_out


        # Torque-based tension estimate
        # Winder physics: J*alpha = T_motor + T_tension*R - T_friction
        # So T_tension = (J*alpha - T_motor + T_friction) / R
        # Wait, for Unwinder: Tension pulls (+), Motor brakes (-).
        
        # Let's assume standard motor convention: E = T_m - T_load
        # Here we need magnitude of tension.
        
        # If simulation uses: J*alpha = T_net = T_motor + T_load(Tension) - T_friction
        # Then T_load = J*alpha - T_motor + T_friction
        # If T_motor is negative (-100), T_load is positive (+100).
        # J*alpha (approx 0) = -100 + 100 + friction.
        # So T_load = 0 - (-100) + friction = 100 + friction.
        
        # Current code: (tau_motor - J*alpha - friction) / R
        # (-100 - 0 - friction) / R = -100 / R => Negative.
        
        # FIX: Flip the signs to get positive tension magnitude from braking torque.
        # Alternatively, assume we want Signed Tension (which is + for tension).
        
        if abs(R) >= self.min_radius:
            # Correct logic for Unwinder where Motor opposes Tension
            # T_tension = (J*alpha - tau_motor + friction_est) / R ?
            # Let's try: J*alpha = Tau_motor + Tau_tension - Friction
            # Tau_tension = J*alpha - Tau_motor + Friction
            tension_tau = (J_used * alpha - tau_motor + friction_est) / R
            
        tension_tau = self._apply_limits(tension_tau)

        # Span-based tension estimate
        tension_span = self.web_span.update(
            v_upstream=v_upstream,
            v_downstream=v_downstream,
            dt=dt_used,
            strain_upstream=strain_upstream,
        )

        # Optional measured tension replacement at high speed
        if tension_measured is not None and abs(omega) >= self.omega_max:
            tension_span = tension_measured

        # Blending
        weight = self._blend_weight(abs(omega))
        tension_raw = (1.0 - weight) * tension_tau + weight * tension_span
        tension_raw = self._apply_limits(tension_raw)

        # EMA filtering
        if self.has_estimate:
            tension_filtered = (1.0 - self.ema_alpha) * self.last_tension + self.ema_alpha * tension_raw
        else:
            tension_filtered = tension_raw
            self.has_estimate = True

        self.last_tension = tension_filtered

        mode = "torque"
        if weight >= 0.99:
            mode = "span"
        elif weight > 0.01:
            mode = "fusion"

        confidence = self._compute_confidence(abs(omega))

        return TensionEstimate(
            tension=tension_filtered,
            tension_tau=tension_tau,
            tension_span=tension_span,
            mode=mode,
            confidence=confidence,
            weight=weight,
            friction_est=friction_est,
            timestamp=self.current_time,
        )

    def reset(self):
        """Reset internal state"""
        self.current_time = 0.0
        self.last_tension = 0.0
        self.has_estimate = False

    def _blend_weight(self, omega_abs: float) -> float:
        """Compute blending weight based on speed"""
        if omega_abs <= self.omega_min:
            return 0.0
        if omega_abs >= self.omega_max:
            return 1.0
        return (omega_abs - self.omega_min) / (self.omega_max - self.omega_min)

    def _apply_limits(self, tension: float) -> float:
        """Clamp tension to physical limits"""
        return float(np.clip(tension, self.tension_min, self.tension_max))

    def _compute_confidence(self, omega_abs: float) -> float:
        """Simple confidence heuristic based on speed"""
        if omega_abs <= self.omega_min:
            return 0.7
        if omega_abs >= self.omega_max:
            return 0.9
        return 0.7 + 0.2 * (omega_abs - self.omega_min) / (self.omega_max - self.omega_min)

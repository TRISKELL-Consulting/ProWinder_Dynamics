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
        friction_est = 0.0
        if self.friction_observer is not None:
            friction_est = self.friction_observer.update(
                measured_velocity=omega,
                applied_torque=tau_motor,
                dt=dt_used,
                inertia=J_used,
            )

        # Torque-based tension estimate
        tension_tau = self.last_tension
        if abs(R) >= self.min_radius:
            tension_tau = (tau_motor - J_used * alpha - friction_est) / R
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

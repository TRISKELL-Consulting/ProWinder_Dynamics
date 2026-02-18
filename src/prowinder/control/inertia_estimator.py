"""
Inertia Estimator - T2.1.2: Auto-Identification of Total Inertia and Friction

This module implements real-time identification of winding system inertia J_total(R)
and friction coefficients using Recursive Least-Squares (RLS) estimation.

Author: ProWinder Dynamics Team
Date: February 18, 2026
Status: Phase 2 Implementation
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class IdentificationState(Enum):
    """State machine for inertia identification process"""
    IDLE = "idle"                    # Not started
    COLLECTING = "collecting"        # Collecting data for batch ID
    IDENTIFYING = "identifying"      # Running batch identification
    CONFIRMED = "confirmed"          # Identification converged
    TRACKING = "tracking"            # Online RLS tracking active
    FAILURE = "failure"              # Identification failed


@dataclass
class InertiaEstimate:
    """Output structure for inertia estimation results"""
    
    # Primary estimates
    J_total: float                   # Total inertia (kg·m²)
    J_web: float                     # Web contribution (kg·m²)
    f_coulomb: float                 # Coulomb friction (N·m)
    f_viscous: float                 # Viscous friction coefficient (N·m·s/rad)
    rho_estimated: float             # Material density (kg/m²)
    
    # Quality metrics
    uncertainty: float               # Estimate uncertainty (%)
    confidence: float                # Confidence score (0-1)
    residual_norm: float             # Residual norm from fit
    
    # State information
    state: str                       # Current identification state
    timestamp: float                 # Measurement time (s)
    num_samples: int = 0             # Number of samples used
    
    def __str__(self) -> str:
        return (f"InertiaEstimate(J={self.J_total:.4f} kg·m², "
                f"ρ={self.rho_estimated:.1f} kg/m², "
                f"uncertainty={self.uncertainty:.2f}%, "
                f"state={self.state})")


@dataclass
class MeasurementData:
    """Single timestep measurement for identification"""
    tau_motor: float                 # Motor torque command (N·m)
    omega: float                     # Angular velocity (rad/s)
    alpha: float                     # Angular acceleration (rad/s²)
    T_web: float                     # Web tension (N)
    R: float                         # Winding radius (m)
    timestamp: float                 # Time (s)


class InertiaEstimator:
    """
    Auto-identification of total inertia and friction parameters.
    
    Uses Recursive Least-Squares (RLS) to identify:
    - Total inertia J_total (including motor, roller, and web)
    - Coulomb friction f_coulomb
    - Viscous friction f_viscous
    
    The identification solves:
        τ_motor = J_total·α + f_coulomb·sign(ω) + f_viscous·ω + T_web·R
    
    for the unknown parameters [J_total, f_coulomb, f_viscous].
    """
    
    def __init__(
        self,
        J_motor: float,              # Motor inertia (kg·m²)
        J_roller: float,             # Roller inertia (kg·m²)
        R_core: float,               # Mandrel/core radius (m)
        L_roller: float,             # Roller width (m)
        dt: float = 0.01,            # Sampling time (s)
        lambda_rls: float = 0.995,   # RLS forgetting factor
        min_samples: int = 100,      # Min samples for batch ID
        max_samples: int = 500,      # Max buffer size
    ):
        """
        Initialize the inertia estimator.
        
        Args:
            J_motor: Motor moment of inertia (kg·m²) - from datasheet
            J_roller: Roller moment of inertia (kg·m²) - from CAD
            R_core: Core/mandrel radius (m)
            L_roller: Roller width (m)
            dt: Sampling time (s)
            lambda_rls: Forgetting factor for RLS (0.98-0.999)
            min_samples: Minimum samples before batch identification
            max_samples: Maximum buffer size (memory management)
        """
        # System parameters (known constants)
        self.J_motor = J_motor
        self.J_roller = J_roller
        self.R_core = R_core
        self.L_roller = L_roller
        self.dt = dt
        
        # RLS configuration
        self.lambda_rls = lambda_rls
        self.min_samples = min_samples
        self.max_samples = max_samples
        
        # State machine
        self.state = IdentificationState.IDLE
        self.time_in_state = 0.0
        
        # Parameter estimates [J_total, f_coulomb, f_viscous]
        self.theta = np.array([0.1, 1.0, 0.01])  # Initial guess
        self.theta_prev = self.theta.copy()
        
        # RLS covariance matrix
        self.P = np.eye(3) * 10.0  # Initial uncertainty
        
        # Data buffer for batch identification
        self.data_buffer: List[MeasurementData] = []
        
        # Convergence tracking
        self.convergence_threshold = 0.02  # 2% change threshold
        self.convergence_counter = 0
        self.convergence_required = 10  # Consecutive stable iterations
        
        # Statistics
        self.residual_history = []
        self.theta_history = []
        
        # Timing
        self.current_time = 0.0
        
        logger.info(f"InertiaEstimator initialized: J_motor={J_motor:.4f}, "
                   f"J_roller={J_roller:.4f}, R_core={R_core:.3f}m, L={L_roller:.3f}m")
    
    def update(
        self,
        tau_motor: float,
        omega: float,
        alpha: float,
        T_web: float,
        R: float
    ) -> InertiaEstimate:
        """
        Main update method called at control rate.
        
        Args:
            tau_motor: Motor torque command (N·m)
            omega: Angular velocity (rad/s)
            alpha: Angular acceleration (rad/s²)
            T_web: Web tension (N)
            R: Winding radius (m)
            
        Returns:
            InertiaEstimate with current parameters and state
        """
        self.current_time += self.dt
        self.time_in_state += self.dt
        
        # Create measurement
        measurement = MeasurementData(
            tau_motor=tau_motor,
            omega=omega,
            alpha=alpha,
            T_web=T_web,
            R=R,
            timestamp=self.current_time
        )
        
        # State machine logic
        if self.state == IdentificationState.IDLE:
            self._handle_idle_state(measurement)
            
        elif self.state == IdentificationState.COLLECTING:
            self._handle_collecting_state(measurement)
            
        elif self.state == IdentificationState.IDENTIFYING:
            self._handle_identifying_state()
            
        elif self.state == IdentificationState.CONFIRMED:
            self._handle_confirmed_state()
            
        elif self.state == IdentificationState.TRACKING:
            self._handle_tracking_state(measurement)
        
        # Generate output estimate
        return self._generate_estimate()
    
    def _handle_idle_state(self, measurement: MeasurementData):
        """Handle IDLE state - waiting for sufficient excitation"""
        # Check for sufficient excitation (non-zero acceleration)
        if abs(measurement.alpha) > 0.5:  # rad/s² threshold
            logger.info("Excitation detected, transitioning to COLLECTING")
            self.state = IdentificationState.COLLECTING
            self.time_in_state = 0.0
            self.data_buffer = [measurement]
        else:
            # Stay idle - use nominal model
            pass
    
    def _handle_collecting_state(self, measurement: MeasurementData):
        """Handle COLLECTING state - accumulating data"""
        # Add measurement to buffer
        self.data_buffer.append(measurement)
        
        # Enforce buffer size limit
        if len(self.data_buffer) > self.max_samples:
            self.data_buffer.pop(0)  # Remove oldest
        
        # Check if enough data collected
        if len(self.data_buffer) >= self.min_samples:
            logger.info(f"Collected {len(self.data_buffer)} samples, starting identification")
            self.state = IdentificationState.IDENTIFYING
            self.time_in_state = 0.0
        
        # Timeout protection (30s)
        if self.time_in_state > 30.0:
            logger.warning("Data collection timeout, reverting to IDLE")
            self.state = IdentificationState.FAILURE
            self.data_buffer = []
    
    def _handle_identifying_state(self):
        """Handle IDENTIFYING state - run batch identification"""
        try:
            # Run batch identification
            theta_identified, residual_norm = self._identify_batch()
            
            # Update estimate
            self.theta = theta_identified
            self.residual_history.append(residual_norm)
            
            # Check convergence
            if residual_norm < 0.15:  # Good fit threshold (relaxed for noise)
                logger.info(f"Identification converged: J={theta_identified[0]:.4f} kg·m²")
                self.state = IdentificationState.CONFIRMED
                self.time_in_state = 0.0
                
                # Initialize RLS for tracking
                self._initialize_rls()
            else:
                logger.warning(f"Identification poor fit (residual={residual_norm:.3f}), retrying")
                self.state = IdentificationState.COLLECTING
                
        except Exception as e:
            logger.error(f"Identification failed: {e}")
            self.state = IdentificationState.FAILURE
    
    def _handle_confirmed_state(self):
        """Handle CONFIRMED state - identification successful, prepare for tracking"""
        # Wait briefly to confirm stability
        if self.time_in_state > 2.0:
            logger.info("Transitioning to TRACKING mode")
            self.state = IdentificationState.TRACKING
            self.time_in_state = 0.0
    
    def _handle_tracking_state(self, measurement: MeasurementData):
        """Handle TRACKING state - online RLS updates"""
        # Update using RLS
        try:
            self._update_online_rls(measurement)
            
            # Check for drift (material change)
            if self._detect_drift():
                logger.warning("Parameter drift detected, re-identifying")
                self.state = IdentificationState.COLLECTING
                self.data_buffer = []
                self.convergence_counter = 0
                
        except Exception as e:
            logger.error(f"RLS update failed: {e}")
            # Stay in tracking, use previous estimate
    
    def _identify_batch(self) -> Tuple[np.ndarray, float]:
        """
        Batch identification using SEQUENTIAL parameter estimation.
        
        Phase 1: Identify f_viscous from constant-velocity data
        Phase 2: Identify f_coulomb from near-zero velocity data  
        Phase 3: Identify J from high-acceleration data
        
        Returns:
            theta: Parameter vector [J, f_coulomb, f_viscous]
            residual_norm: Normalized residual norm
        """
        n = len(self.data_buffer)
        
        # Initialize estimates
        f_viscous = 0.05  # Initial guess
        f_coulomb = 3.0   # Nominal value
        J_total = 0.1
        
        # ===== PHASE 1: Identify f_viscous from constant-velocity data =====
        # Select samples where α ≈ 0 and ω > 5 rad/s
        phase1_data = [(i, d) for i, d in enumerate(self.data_buffer) 
                       if abs(d.alpha) < 0.5 and abs(d.omega) > 5.0]
        
        if len(phase1_data) > 10:
            # Build regression: (τ - T·R - f_c_nominal·sign(ω)) = f_v·ω
            # Assume nominal f_c for now
            X1 = np.array([d.omega for _, d in phase1_data])
            y1 = np.array([d.tau_motor - d.T_web * d.R - 3.0 * np.sign(d.omega) 
                          for _, d in phase1_data])
            
            # Linear regression (1D)
            f_viscous = np.sum(X1 * y1) / (np.sum(X1 * X1) + 1e-6)
            f_viscous = np.clip(f_viscous, 0.0, 5.0)
            logger.debug(f"Phase 1: f_viscous={f_viscous:.4f} (from {len(phase1_data)} samples)")
        
        # ===== PHASE 2: Identify f_coulomb + J from varied acceleration data =====
        # Select samples where |α| > 0.5 rad/s² (transient)
        phase2_data = [(i, d) for i, d in enumerate(self.data_buffer) 
                       if abs(d.alpha) > 0.5]
        
        if len(phase2_data) > 10:
            # Build regression: (τ - T·R - f_v·ω) = f_c·sign(ω) + J·α
            # Use 2D regression [sign(ω), α]
            X2 = np.zeros((len(phase2_data), 2))
            y2 = np.zeros(len(phase2_data))
            
            for i, (_, d) in enumerate(phase2_data):
                X2[i, 0] = np.sign(d.omega) if d.omega != 0 else 0  # f_c term
                X2[i, 1] = d.alpha                                   # J term
                y2[i] = d.tau_motor - d.T_web * d.R - f_viscous * d.omega
            
            # Solve for [f_c, J]
            try:
                params = np.linalg.lstsq(X2, y2, rcond=None)[0]
                f_coulomb = np.clip(params[0], 0.0, 50.0)
                J_total = np.clip(params[1], 0.01, 10.0)
                logger.debug(f"Phase 2: f_coulomb={f_coulomb:.2f}, J={J_total:.4f} "
                            f"(from {len(phase2_data)} samples)")
            except np.linalg.LinAlgError:
                logger.warning("Phase 2 failed, using defaults")
        
        # ===== PHASE 3: Refine J from high-acceleration data =====
        # Select samples where |α| > 2 rad/s² (strong acceleration)
        phase3_data = [(i, d) for i, d in enumerate(self.data_buffer) 
                       if abs(d.alpha) > 2.0]
        
        if len(phase3_data) > 5:
            # Build regression: (τ - T·R - f_c·sign(ω) - f_v·ω) = J·α
            X3 = np.array([d.alpha for _, d in phase3_data])
            y3 = np.array([d.tau_motor - d.T_web * d.R - 
                          f_coulomb * np.sign(d.omega) - f_viscous * d.omega 
                          for _, d in phase3_data])
            
            # Linear regression (1D)
            J_refined = np.sum(X3 * y3) / (np.sum(X3 * X3) + 1e-6)
            if 0.01 < J_refined < 10.0:  # Sanity check
                J_total = J_refined
                logger.debug(f"Phase 3: J refined to {J_total:.4f} (from {len(phase3_data)} samples)")
        
        # ===== Calculate final residual =====
        theta = np.array([J_total, f_coulomb, f_viscous])
        
        # Calculate residual over ALL data
        X_all = np.zeros((n, 3))
        y_all = np.zeros(n)
        
        for i, data in enumerate(self.data_buffer):
            X_all[i, 0] = data.alpha
            X_all[i, 1] = np.sign(data.omega) if data.omega != 0 else 0
            X_all[i, 2] = data.omega
            y_all[i] = data.tau_motor - data.T_web * data.R
        
        y_pred = X_all @ theta
        residuals = y_all - y_pred
        residual_norm = np.linalg.norm(residuals) / (np.linalg.norm(y_all) + 1e-6)
        
        logger.info(f"Sequential ID complete: J={theta[0]:.4f}, f_c={theta[1]:.2f}, "
                   f"f_v={theta[2]:.4f}, residual={residual_norm:.4f}")
        
        return theta, residual_norm
    
    def _initialize_rls(self):
        """Initialize RLS for online tracking"""
        # Reset covariance with reduced uncertainty
        self.P = np.eye(3) * 1.0  # Lower initial uncertainty (confident from batch)
        
        logger.debug("RLS initialized for online tracking")
    
    def _update_online_rls(self, measurement: MeasurementData):
        """
        Recursive Least-Squares online update.
        
        Updates parameter estimates using new measurement.
        """
        # Form regressor vector φ
        phi = np.array([
            measurement.alpha,
            np.sign(measurement.omega) if measurement.omega != 0 else 0,
            measurement.omega
        ])
        
        # Target value
        y = measurement.tau_motor - measurement.T_web * measurement.R
        
        # Prediction error
        e = y - phi @ self.theta
        
        # RLS update equations
        # Gain: K = P·φ / (λ + φ^T·P·φ)
        denom = self.lambda_rls + phi @ self.P @ phi
        K = (self.P @ phi) / denom
        
        # Update parameters: θ = θ + K·e
        self.theta_prev = self.theta.copy()
        self.theta = self.theta + K * e
        
        # Update covariance: P = (1/λ)·(P - K·φ^T·P)
        self.P = (self.P - np.outer(K, phi @ self.P)) / self.lambda_rls
        
        # Bounds enforcement
        self.theta[0] = np.clip(self.theta[0], 0.01, 10.0)
        self.theta[1] = np.clip(self.theta[1], 0.0, 50.0)
        self.theta[2] = np.clip(self.theta[2], 0.0, 5.0)
        
        # Track convergence
        param_change = np.linalg.norm(self.theta - self.theta_prev) / np.linalg.norm(self.theta)
        if param_change < self.convergence_threshold:
            self.convergence_counter += 1
        else:
            self.convergence_counter = 0
        
        # Store history
        self.theta_history.append(self.theta.copy())
        if len(self.theta_history) > 1000:
            self.theta_history.pop(0)
    
    def _detect_drift(self) -> bool:
        """
        Detect parameter drift indicating material change.
        
        Returns:
            True if drift detected, False otherwise
        """
        if len(self.theta_history) < 20:  # Reduced from 50 for faster detection
            return False
        
        # Compare recent average to baseline
        recent = np.mean(self.theta_history[-5:], axis=0)
        baseline = np.mean(self.theta_history[-20:-10], axis=0) if len(self.theta_history) >= 20 else self.theta_history[0]
        
        # Check J drift (most sensitive to material change)
        J_drift = abs(recent[0] - baseline[0]) / (baseline[0] + 1e-6)
        
        if J_drift > 0.20:  # 20% drift threshold
            logger.warning(f"J drift detected: {J_drift*100:.1f}%")
            return True
        
        return False
    
    def calculate_analytical_J(self, R: float, rho: Optional[float] = None) -> float:
        """
        Calculate total inertia using analytical model.
        
        J_total = J_motor + J_roller + J_web(R)
        J_web = (ρ·π·L/2) · (R⁴ - R_core⁴)
        
        Args:
            R: Current winding radius (m)
            rho: Material density (kg/m²). If None, use identified value.
            
        Returns:
            J_total (kg·m²)
        """
        if rho is None:
            # Extract rho from identified J
            if self.state in [IdentificationState.CONFIRMED, IdentificationState.TRACKING]:
                # Back-calculate rho from latest measurement
                # This is approximate - proper way is to track R during identification
                rho = self._estimate_rho()
            else:
                rho = 1500.0  # Nominal material density (kg/m²)
        
        # Calculate web inertia
        J_web = (rho * np.pi * self.L_roller / 2.0) * (R**4 - self.R_core**4)
        
        # Total inertia
        J_total = self.J_motor + self.J_roller + J_web
        
        return J_total
    
    def _estimate_rho(self) -> float:
        """
        Estimate material density from identified J_total.
        
        Assumes a reference radius R_ref where J was identified.
        """
        # For now, use nominal reference (will improve with tracked R history)
        R_ref = 0.10  # 100mm typical reference radius
        
        J_web_identified = self.theta[0] - self.J_motor - self.J_roller
        
        denom = (np.pi * self.L_roller / 2.0) * (R_ref**4 - self.R_core**4)
        if abs(denom) < 1e-6:
            return 1500.0  # Avoid division by zero
        
        rho = J_web_identified / denom
        
        # Sanity check
        rho = np.clip(rho, 500.0, 10000.0)  # Reasonable material range
        
        return rho
    
    def get_uncertainty(self) -> float:
        """
        Calculate current estimate uncertainty from covariance matrix.
        
        Returns:
            Uncertainty percentage (%)
        """
        if self.state in [IdentificationState.IDLE, IdentificationState.COLLECTING]:
            return 100.0  # High uncertainty - not identified
        
        if self.state == IdentificationState.IDENTIFYING:
            return 50.0  # Medium uncertainty during identification
        
        if self.state == IdentificationState.CONFIRMED:
            # After batch ID, use residual-based uncertainty
            if self.residual_history:
                residual = self.residual_history[-1]
                # Map residual to uncertainty: 0→1%, 0.1→5%, 0.2→15%
                uncertainty_pct = min(residual * 50.0, 100.0)
                return max(uncertainty_pct, 1.0)  # At least 1%
            return 10.0  # Default for confirmed
        
        # TRACKING state: Use RLS covariance
        variance_J = self.P[0, 0]
        std_J = np.sqrt(variance_J)
        
        uncertainty_pct = (std_J / (abs(self.theta[0]) + 1e-6)) * 100.0
        
        # Clamp to reasonable range
        return np.clip(uncertainty_pct, 0.1, 100.0)
    
    def get_confidence(self) -> float:
        """
        Calculate confidence score (0-1).
        
        Based on convergence status and residual quality.
        """
        if self.state in [IdentificationState.IDLE, IdentificationState.FAILURE]:
            return 0.0
        elif self.state == IdentificationState.COLLECTING:
            return 0.3
        elif self.state == IdentificationState.IDENTIFYING:
            return 0.5
        elif self.state == IdentificationState.CONFIRMED:
            return 0.8
        elif self.state == IdentificationState.TRACKING:
            # Confidence based on convergence
            return min(0.9 + self.convergence_counter / 100.0, 1.0)
        else:
            return 0.5
    
    def _generate_estimate(self) -> InertiaEstimate:
        """Generate output estimate structure"""
        J_total = self.theta[0]
        J_web = J_total - self.J_motor - self.J_roller
        rho_est = self._estimate_rho()
        
        uncertainty = self.get_uncertainty()
        confidence = self.get_confidence()
        
        residual_norm = self.residual_history[-1] if self.residual_history else 0.0
        
        return InertiaEstimate(
            J_total=J_total,
            J_web=J_web,
            f_coulomb=self.theta[1],
            f_viscous=self.theta[2],
            rho_estimated=rho_est,
            uncertainty=uncertainty,
            confidence=confidence,
            residual_norm=residual_norm,
            state=self.state.value,
            timestamp=self.current_time,
            num_samples=len(self.data_buffer)
        )
    
    def reset(self):
        """Reset estimator to initial state"""
        self.state = IdentificationState.IDLE
        self.time_in_state = 0.0
        self.theta = np.array([0.1, 1.0, 0.01])
        self.P = np.eye(3) * 10.0
        self.data_buffer = []
        self.convergence_counter = 0
        self.residual_history = []
        self.theta_history = []
        logger.info("InertiaEstimator reset")

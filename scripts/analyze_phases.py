"""
Detailed debug of sequential identification phases
"""
import sys
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from prowinder.control.inertia_estimator import MeasurementData

# Ground truth
J_true = 0.150
f_coulomb_true = 10.0
f_viscous_true = 0.2
R = 0.10
T_web = 50.0

# Generate synthetic data - 200 samples
n_samples = 200
dt = 0.01
data_buffer = []

# Multi-phase velocity profile (same as test suite)
# Optimized for 200 samples (2.0s)
omega_ref = np.zeros(n_samples)
for i in range(n_samples):
    t = i * dt
    if t < 0.3:
        omega_ref[i] = 5.0 + 50.0 * (t / 0.3)  # Rapid accel
    elif t < 0.9:
        omega_ref[i] = 20.0  # High constant
    elif t < 1.1:
        omega_ref[i] = 20.0 - 70.0 * ((t - 0.9) / 0.2)  # Decel
    else:
        omega_ref[i] = 6.0  # Low constant (Phase 0!)

# Calculate alpha using central differences
alpha = np.zeros(n_samples)
alpha[0] = (omega_ref[1] - omega_ref[0]) / dt
for i in range(1, n_samples - 1):
    alpha[i] = (omega_ref[i+1] - omega_ref[i-1]) / (2 * dt)
alpha[-1] = (omega_ref[-1] - omega_ref[-2]) / dt

# Light Gaussian smoothing
from scipy.ndimage import gaussian_filter1d
alpha = gaussian_filter1d(alpha, sigma=1.0)

# Build data buffer
for i in range(n_samples):
    omega = omega_ref[i]
    tau_motor = (
        J_true * alpha[i] +
        f_coulomb_true * np.sign(omega + 1e-6) +
        f_viscous_true * omega +
        T_web * R
    )
    
    data_buffer.append(MeasurementData(
        tau_motor=tau_motor,
        omega=omega,
        alpha=alpha[i],
        T_web=T_web,
        R=R,
        timestamp=i * dt
    ))

# Analyze phases
print("=== DATA ANALYSIS ===\n")

print(f"Total samples: {len(data_buffer)}")
print(f"ω range: {min(d.omega for d in data_buffer):.2f} to {max(d.omega for d in data_buffer):.2f} rad/s")
print(f"α range: {min(d.alpha for d in data_buffer):.2f} to {max(d.alpha for d in data_buffer):.2f} rad/s²\n")

# Phase 0: Low velocity, low alpha
phase0 = [d for d in data_buffer if abs(d.omega) < 8.0 and abs(d.alpha) < 0.5]
print(f"Phase 0 candidates (ω<8, |α|<0.5): {len(phase0)} samples")
if phase0:
    print(f"  ω range: {min(d.omega for d in phase0):.2f} to {max(d.omega for d in phase0):.2f}")
    print(f"  α range: {min(d.alpha for d in phase0):.2f} to {max(d.alpha for d in phase0):.2f}")
    
    # Try rough f_coulomb estimate
    fc_estimates = []
    for d in phase0:
        if abs(d.omega) > 1.0:
            fc_est = (d.tau_motor - d.T_web * d.R) / (np.sign(d.omega) + 1e-6)
            if 0 < fc_est < 50:
                fc_estimates.append(fc_est)
    
    if fc_estimates:
        fc_median = np.median(fc_estimates)
        fc_mean = np.mean(fc_estimates)
        print(f"  Rough f_c estimates: median={fc_median:.2f}, mean={fc_mean:.2f}, std={np.std(fc_estimates):.2f}")
        print(f"  (True f_c = {f_coulomb_true:.2f})")
print()

# Phase 1: Constant velocity for f_viscous
phase1 = [d for d in data_buffer if abs(d.alpha) < 0.5 and abs(d.omega) > 5.0]
print(f"Phase 1 candidates (|α|<0.5, ω>5): {len(phase1)} samples")
if phase1:
    print(f"  ω range: {min(d.omega for d in phase1):.2f} to {max(d.omega for d in phase1):.2f}")
    print(f"  α range: {min(d.alpha for d in phase1):.2f} to {max(d.alpha for d in phase1):.2f}")
print()

# Phase 2: Transient for f_coulomb + J
phase2 = [d for d in data_buffer if abs(d.alpha) > 0.5]
print(f"Phase 2 candidates (|α|>0.5): {len(phase2)} samples")
if phase2:
    print(f"  ω range: {min(d.omega for d in phase2):.2f} to {max(d.omega for d in phase2):.2f}")
    print(f"  α range: {min(d.alpha for d in phase2):.2f} to {max(d.alpha for d in phase2):.2f}")
print()

# Phase 3: High acceleration for J refinement
phase3 = [d for d in data_buffer if abs(d.alpha) > 2.0]
print(f"Phase 3 candidates (|α|>2): {len(phase3)} samples")
if phase3:
    print(f"  ω range: {min(d.omega for d in phase3):.2f} to {max(d.omega for d in phase3):.2f}")
    print(f"  α range: {min(d.alpha for d in phase3):.2f} to {max(d.alpha for d in phase3):.2f}")
print()

# Detailed torque analysis for Phase 0
print("=== PHASE 0 TORQUE BREAKDOWN ===")
if phase0:
    for i, d in enumerate(phase0[:10]):  # First 10 samples
        tau_total = d.tau_motor
        tau_web = d.T_web * d.R
        tau_inertia = J_true * d.alpha
        tau_coulomb = f_coulomb_true * np.sign(d.omega)
        tau_viscous = f_viscous_true * d.omega
        tau_residual = tau_total - tau_web
        
        print(f"Sample {i}: ω={d.omega:.2f}, α={d.alpha:.2f}")
        print(f"  τ_total={tau_total:.2f}, τ_web={tau_web:.2f}, τ_residual={tau_residual:.2f}")
        print(f"  Components: J·α={tau_inertia:.2f}, f_c={tau_coulomb:.2f}, f_v={tau_viscous:.2f}")
        print(f"  (τ - T·R) / sign(ω) = {tau_residual / np.sign(d.omega):.2f} (compare to f_c={f_coulomb_true})")

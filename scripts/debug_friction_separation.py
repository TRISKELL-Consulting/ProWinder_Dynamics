"""
Debug script for friction separation test case
Tests with f_coulomb=10.0, f_viscous=0.2
"""
import sys
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from prowinder.control.inertia_estimator import InertiaEstimator, MeasurementData

# System parameters
params = {
    'J_motor': 0.05,
    'J_roller': 0.02,
    'R_core': 0.050,
    'L_roller': 1.0,
    'dt': 0.01,
}

# Ground truth with higher friction values
J_true = 0.150        # kg·m²
f_coulomb_true = 10.0 # N·m (much larger)
f_viscous_true = 0.2  # N·m·s/rad (larger)
R = 0.10              # m
T_web = 50.0          # N

# Create estimator
estimator = InertiaEstimator(**params)

# Generate synthetic data - 200 samples = 2 seconds
# Use same profile as test suite
n_samples = 200
dt = 0.01
data = []

# Multi-phase velocity profile optimized for Phase 0 data
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

# Calculate alpha with central differences + Gaussian smoothing
alpha = np.zeros(n_samples)
alpha[0] = (omega_ref[1] - omega_ref[0]) / dt
for i in range(1, n_samples - 1):
    alpha[i] = (omega_ref[i+1] - omega_ref[i-1]) / (2 * dt)
alpha[-1] = (omega_ref[-1] - omega_ref[-2]) / dt

from scipy.ndimage import gaussian_filter1d
alpha = gaussian_filter1d(alpha, sigma=1.0)

# Simulate dynamics
for i in range(n_samples):
    omega = omega_ref[i]
    
    # Ground truth torque
    tau_motor = (
        J_true * alpha[i] +
        f_coulomb_true * np.sign(omega + 1e-6) +
        f_viscous_true * omega +
        T_web * R
    )
    
    measurement = MeasurementData(
        tau_motor=tau_motor,
        omega=omega,
        alpha=alpha[i],
        T_web=T_web,
        R=R,
        timestamp=i * dt
    )
    data.append(measurement)
    
    # Update estimator
    estimate = estimator.update(
        measurement.tau_motor,
        measurement.omega,
        measurement.alpha,
        measurement.T_web,
        measurement.R
    )
    
    # Print detailed info during identification
    if estimator.state in ['identifying', 'confirmed'] and i % 20 == 0:
        print(f"\n[t={measurement.timestamp:.2f}s] State: {estimator.state}")
        print(f"  ω={omega:.2f}, α={alpha[i]:.2f}, τ={tau_motor:.2f}")
        if estimate.J_total > 0:
            print(f"  J={estimate.J_total:.4f} (true: {J_true})")
            print(f"  f_c={estimate.f_coulomb:.2f} (true: {f_coulomb_true})")
            print(f"  f_v={estimate.f_viscous:.4f} (true: {f_viscous_true})")

# Final result
print("\n" + "="*60)
print("=== Final Result ===")
print(f"State: {estimator.state}")
print(f"J_identified:  {estimate.J_total:.4f} (true: {J_true})")
print(f"f_coulomb:     {estimate.f_coulomb:.2f} (true: {f_coulomb_true})")
print(f"f_viscous:     {estimate.f_viscous:.4f} (true: {f_viscous_true})")
print(f"Uncertainty:   {estimate.uncertainty*100:.2f}%")
print(f"Confidence:    {estimate.confidence:.2f}")

# Calculate errors
J_err = abs(estimate.J_total - J_true) / J_true * 100
fc_err = abs(estimate.f_coulomb - f_coulomb_true) / f_coulomb_true * 100
fv_err = abs(estimate.f_viscous - f_viscous_true) / f_viscous_true * 100

print(f"\nErrors:")
print(f"  J:         {J_err:.2f}%")
print(f"  f_coulomb: {fc_err:.2f}%")
print(f"  f_viscous: {fv_err:.2f}%")
print("="*60)

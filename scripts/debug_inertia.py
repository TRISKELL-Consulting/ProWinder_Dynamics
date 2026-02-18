"""
Debug script for InertiaEstimator

Quick test to understand what's happening with identification
"""

import numpy as np
import sys
sys.path.insert(0, 'src')

from prowinder.control.inertia_estimator import InertiaEstimator, MeasurementData

# Known parameters
J_total_true = 0.150
f_coulomb_true = 3.0
f_viscous_true = 0.05
R = 0.10
T_web = 50.0

# Create estimator
estimator = InertiaEstimator(
    J_motor=0.05,
    J_roller=0.02,
    R_core=0.050,
    L_roller=1.0,
    dt=0.01
)


print(f"=== Generating Synthetic Data ===")
print(f"True values: J={J_total_true}, f_c={f_coulomb_true}, f_v={f_viscous_true}")

# Generate simple test data
data = []
dt = 0.01
for i in range(200):
    t = i * dt
    
    # Simple velocity ramp
    if t < 1.0:
        omega = 5.0 + 10.0 * t  # Ramp up
        alpha = 10.0
    else:
        omega = 15.0  # Constant
        alpha = 0.1
    
    # Calculate torque from true dynamics
    tau = J_total_true * alpha + f_coulomb_true * np.sign(omega) + f_viscous_true * omega + T_web * R
    
    data.append(MeasurementData(
        tau_motor=tau,
        omega=omega,
        alpha=alpha,
        T_web=T_web,
        R=R,
        timestamp=t
    ))

print(f"Generated {len(data)} samples")
print(f"Sample tau range: {min(d.tau_motor for d in data):.2f} - {max(d.tau_motor for d in data):.2f} N·m")
print(f"Sample omega range: {min(d.omega for d in data):.2f} - {max(d.omega for d in data):.2f} rad/s")
print(f"Sample alpha range: {min(d.alpha for d in data):.2f} - {max(d.alpha for d in data):.2f} rad/s²\n")

# Feed to estimator
print("=== Running Identification ===")
for i, measurement in enumerate(data):
    estimate = estimator.update(
        measurement.tau_motor,
        measurement.omega,
        measurement.alpha,
        measurement.T_web,
        measurement.R
    )
    
    if i % 50 == 0:
        print(f"Step {i}: state={estimator.state.value}, J={estimate.J_total:.4f}, "
              f"f_c={estimate.f_coulomb:.2f}, f_v={estimate.f_viscous:.4f}")

print(f"\n=== Final Result ===")
print(f"State: {estimate.state}")
print(f"J_identified: {estimate.J_total:.4f} (true: {J_total_true})")
print(f"f_coulomb: {estimate.f_coulomb:.2f} (true: {f_coulomb_true})")
print(f"f_viscous: {estimate.f_viscous:.4f} (true: {f_viscous_true})")
print(f"Error: J={(abs(estimate.J_total-J_total_true)/J_total_true*100):.2f}%")
print(f"Uncertainty: {estimate.uncertainty:.2f}%")
print(f"Confidence: {estimate.confidence:.2f}")
print(f"Residual: {estimate.residual_norm:.4f}")
print(f"Num samples: {estimate.num_samples}")

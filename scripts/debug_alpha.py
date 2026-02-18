"""
Analyze omega and alpha during constant-velocity phases
"""
import sys
import numpy as np
from pathlib import Path
from scipy.ndimage import gaussian_filter1d

# Generate test profile
n_samples = 200
dt = 0.01

omega_ref = np.zeros(n_samples)
for i in range(n_samples):
    t = i * dt
    if t < 0.5:
        omega_ref[i] = 5.0 + 15.0 * (t / 0.5)
    elif t < 1.5:
        omega_ref[i] = 20.0  # Constant high
    elif t < 2.0:
        omega_ref[i] =20.0 - 14.0 * ((t - 1.5) / 0.5)
    elif t < 3.0:
        omega_ref[i] = 6.0  # Constant LOW (should give Phase 0 data)
    elif t < 3.5:
        omega_ref[i] = 6.0 + 6.0 * ((t - 3.0) / 0.5)
    else:
        omega_ref[i] = 12.0

# Calculate alpha with central differences
alpha = np.zeros(n_samples)
alpha[0] = (omega_ref[1] - omega_ref[0]) / dt
for i in range(1, n_samples - 1):
    alpha[i] = (omega_ref[i+1] - omega_ref[i-1]) / (2 * dt)
alpha[-1] = (omega_ref[-1] - omega_ref[-2]) / dt

alpha_smooth = gaussian_filter1d(alpha, sigma=1.0)

# Analyze t=2.0-3.0 (low constant velocity phase)
# t=2.0s → i=200, but we only have 200 samples (0-199)
# So t=2.0s is beyond our data!
print("=== LOW VELOCITY PHASE (t=2.0-3.0s expect, but only have 2.0s of data!) ===\n")
print(f"Data duration: {n_samples * dt:.2f}s (samples 0-{n_samples-1})\n")

# Find actual low-velocity region
low_omega_samples = [(i, i*dt, omega_ref[i], alpha[i], alpha_smooth[i]) 
                     for i in range(n_samples) if omega_ref[i] < 8.0]

if low_omega_samples:
    print(f"Found {len(low_omega_samples)} samples with ω < 8.0:\n")
    print("Sample   t      ω     α_raw    α_smooth  Phase0?")
    print("-" * 60)
    
    phase0_count = 0
    for i, t, omega, a_raw, a_smooth in low_omega_samples[:30]:
        is_phase0 = (abs(omega) < 8.0 and abs(a_smooth) < 0.5)
        marker = " <-- YES" if is_phase0 else ""
        if is_phase0:
            phase0_count += 1
        print(f"{i:4d}   {t:4.2f}   {omega:5.2f}   {a_raw:7.2f}   {a_smooth:7.2f}    {is_phase0}{marker}")
    
    if len(low_omega_samples) > 30:
        print(f"... (showing first 30 of {len(low_omega_samples)} samples)")
    
    print(f"\nTotal Phase 0 samples (ω<8, |α|<0.5): {phase0_count}")
else:
    print("NO samples with ω < 8.0 found!")

# Also check high velocity phase
print("\n=== HIGH VELOCITY PHASE (t=0.5-1.5s, ω should be 20.0) ===\n")
print("Sample   t      ω     α_raw    α_smooth  Phase1?")
print("-" * 60)

phase1_count = 0
for i in range(50, 150):
    t = i * dt
    if 0.5 <= t < 1.5:
        is_phase1 = (abs(alpha_smooth[i]) < 0.5 and abs(omega_ref[i]) > 5.0)
        marker = " <-- YES" if is_phase1 else ""
        if is_phase1:
            phase1_count += 1
        
        print(f"{i:4d}   {t:4.2f}   {omega_ref[i]:5.2f}   {alpha[i]:7.2f}   {alpha_smooth[i]:7.2f}    {is_phase1}{marker}")
        
        if i == 70:
            print("... (showing first 20 samples)")
            break

print(f"\nTotal Phase 1 samples in HIGH velocity region: {phase1_count}")

print("\n=== ALPHA STATISTICS ===")
print(f"α_raw: min={min(alpha):.2f}, max={max(alpha):.2f}, std={np.std(alpha):.2f}")
print(f"α_smooth: min={min(alpha_smooth):.2f}, max={max(alpha_smooth):.2f}, std={np.std(alpha_smooth):.2f}")

# Count samples in each phase zone with smoothed alpha
phase0_all = sum(1 for i in range(n_samples) 
                 if abs(omega_ref[i]) < 8.0 and abs(alpha_smooth[i]) < 0.5)
phase1_all = sum(1 for i in range(n_samples) 
                 if abs(alpha_smooth[i]) < 0.5 and abs(omega_ref[i]) > 5.0)

print(f"\nTOTAL across all data:")
print(f"  Phase 0 (ω<8, |α|<0.5): {phase0_all} samples")
print(f"  Phase 1 (ω>5, |α|<0.5): {phase1_all} samples")

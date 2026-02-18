"""
Validation script for T2.1.2 Inertia Estimator
=============================================

Validates compliance with ProWinder Roadmap requirements.

Roadmap Requirements (ACTION_PLAN_3MONTHS.md):
-----------------------------------------------
- Auto-identification of inertia
- Recursive Least-Squares (RLS) for online tracking  
- Performance: <5% precision, <10s convergence

Test Scenarios:
---------------
[TEST  1] Precision requirement: J identification <5% error
[TEST 2] Convergence requirement: Identification complete <10s
[TEST 3] RLS stability: Online tracking without drift
[TEST 4] Material change detection: Trigger re-identification on 20% drift
"""
import sys
import numpy as np
from pathlib import Path
import time

# Add project to path
import os
os.chdir(Path(__file__).parent.parent.parent)
sys.path.insert(0, str(Path.cwd() / 'src'))

from prowinder.control.inertia_estimator import InertiaEstimator, MeasurementData

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text:^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

def print_test(num, desc):
    print(f"\n{YELLOW}[TEST {num}]{RESET} {desc}")
    print("-" * 70)

def print_result(passed, message):
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status}: {message}")
    return passed

def generate_test_data(n_samples, J_true, f_c, f_v, R=0.10, T_web=50.0):
    """Generate synthetic measurement data"""
    dt = 0.01
    data = []
    
    # Multi-phase velocity profile for rich excitation
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
            omega_ref[i] = 6.0  # Low constant
    
    # Calculate alpha
    alpha = np.diff(omega_ref, prepend=omega_ref[0]) / dt
    alpha = np.convolve(alpha, np.ones(3)/3, mode='same')
    
    # Generate measurements
    for i in range(n_samples):
        omega = omega_ref[i]
        tau_motor = (
            J_true * alpha[i] +
            f_c * np.sign(omega + 1e-6) +
            f_v * omega +
            T_web * R
        )
        
        data.append(MeasurementData(
            tau_motor=tau_motor,
            omega=omega,
            alpha=alpha[i],
            T_web=T_web,
            R=R,
            timestamp=i * dt
        ))
    
    return data

def test_1_precision():
    """[TEST 1] Precision requirement: <5% error"""
    print_test(1, "Precision Requirement (<5% error)")
    
    # Ground truth
    J_true = 0.150
    f_c_true = 3.0
    f_v_true = 0.05
    
    # Create estimator
    estimator = InertiaEstimator(
        J_motor=0.05,
        J_roller=0.02,
        R_core=0.050,
        L_roller=1.0,
        dt=0.01
    )
    
    # Generate data
    data = generate_test_data(200, J_true, f_c_true, f_v_true)
    
    # Feed to estimator
    for measurement in data:
        estimate = estimator.update(
            measurement.tau_motor,
            measurement.omega,
            measurement.alpha,
            measurement.T_web,
            measurement.R
        )
    
    # Calculate errors
    J_error = abs(estimate.J_total - J_true) / J_true * 100
    fc_error = abs(estimate.f_coulomb - f_c_true) / f_c_true * 100
    fv_error = abs(estimate.f_viscous - f_v_true) / f_v_true * 100
    
    print(f"  J_identified:  {estimate.J_total:.4f} (true: {J_true}) → {J_error:.2f}% error")
    print(f"  f_coulomb:     {estimate.f_coulomb:.2f} (true: {f_c_true}) → {fc_error:.2f}% error")
    print(f"  f_viscous:     {estimate.f_viscous:.4f} (true: {f_v_true}) → {fv_error:.2f}% error")
    print(f"  State:         {estimator.state}")
    print(f"  Uncertainty:   {estimate.uncertainty*100:.2f}%")
    
    # Requirement: <5% precision for J
    passed = J_error < 5.0
    return print_result(passed, f"J precision: {J_error:.2f}% (requirement: <5%)")

def test_2_convergence():
    """[TEST 2] Convergence requirement: <10s"""
    print_test(2, "Convergence Time (<10s)")
    
    J_true = 0.150
    
    estimator = InertiaEstimator(
        J_motor=0.05,
        J_roller=0.02,
        R_core=0.050,
        L_roller=1.0,
        dt=0.01
    )
    
    # Generate long sequence
    data = generate_test_data(1000, J_true, 3.0, 0.05)  # 10s of data
    
    start_time = time.time()
    convergence_time = None
    
    for i, measurement in enumerate(data):
        estimate = estimator.update(
            measurement.tau_motor,
            measurement.omega,
            measurement.alpha,
            measurement.T_web,
            measurement.R
        )
        
        # Check if converged (CONFIRMED or TRACKING state)
        if convergence_time is None:
            if estimator.state.name in ['CONFIRMED', 'TRACKING']:
                convergence_time = measurement.timestamp
    
    elapsed = time.time() - start_time
    
    print(f"  Convergence time:  {convergence_time:.2f}s")
    print(f"  Processing time:   {elapsed*1000:.2f}ms (real-time factor: {10/elapsed:.1f}x)")
    print(f"  Final state:       {estimator.state}")
    
    # Requirement: convergence <10s
    passed = convergence_time is not None and convergence_time < 10.0
    return print_result(passed, f"Converged in {convergence_time:.2f}s (requirement: <10s)")

def test_3_rls_stability():
    """[TEST 3] RLS online tracking stability"""
    print_test(3, "RLS Stability (online tracking)")
    
    J_true = 0.150
    
    estimator = InertiaEstimator(
        J_motor=0.05,
        J_roller=0.02,
        R_core=0.050,
        L_roller=1.0,
        dt=0.01
    )
    
    # Initial identification
    data_init = generate_test_data(200, J_true, 3.0, 0.05)
    for measurement in data_init:
        estimate = estimator.update(
            measurement.tau_motor,
            measurement.omega,
            measurement.alpha,
            measurement.T_web,
            measurement.R
        )
    
    J_init = estimate.J_total
    
    # Continue tracking with more data
    data_track = generate_test_data(500, J_true, 3.0, 0.05)
    J_estimates = []
    
    for measurement in data_track:
        estimate = estimator.update(
            measurement.tau_motor,
            measurement.omega,
            measurement.alpha,
            measurement.T_web,
            measurement.R
        )
        if estimator.state.name == 'TRACKING':
            J_estimates.append(estimate.J_total)
    
    # Check stability: std should be small
    if J_estimates:
        J_mean = np.mean(J_estimates)
        J_std = np.std(J_estimates)
        drift = abs(J_mean - J_init) / J_init * 100
        
        print(f"  Initial J:     {J_init:.4f}")
        print(f"  Tracking mean: {J_mean:.4f}")
        print(f"  Std deviation: {J_std:.4f}")
        print(f"  Drift:         {drift:.2f}%")
        
        # Requirement: <3% drift, <2% std
        passed = drift < 3.0 and (J_std / J_mean) < 0.02
        return print_result(passed, f"RLS stable: {drift:.2f}% drift, {J_std/J_mean*100:.2f}% std")
    else:
        return print_result(False, "Never reached TRACKING state")

def test_4_drift_detection():
    """[TEST 4] Material change detection"""
    print_test(4, "Drift Detection (material change)")
    
    J_true_1 = 0.150
    J_true_2 = 0.195  # +30% change (material buildup)
    
    estimator = InertiaEstimator(
        J_motor=0.05,
        J_roller=0.02,
        R_core=0.050,
        L_roller=1.0,
        dt=0.01
    )
    
    # Phase 1: Initial material
    data1 = generate_test_data(200, J_true_1, 3.0, 0.05)
    for measurement in data1:
        estimate = estimator.update(
            measurement.tau_motor,
            measurement.omega,
            measurement.alpha,
            measurement.T_web,
            measurement.R
        )
    
    print(f"  Initial J:    {estimate.J_total:.4f} (state: {estimator.state.name})")
    
    # Phase 2: Material change (+30%)
    data2 = generate_test_data(300, J_true_2, 3.0, 0.05)
    reidentified = False
    
    for measurement in data2:
        estimate = estimator.update(
            measurement.tau_motor,
            measurement.omega,
            measurement.alpha,
            measurement.T_web,
            measurement.R
        )
        
        # Check if re-identification triggered
        if estimator.state.name == 'IDENTIFYING':
            reidentified = True
    
    final_J = estimate.J_total
    final_error = abs(final_J - J_true_2) /J_true_2 * 100
    
    print(f"  New J_true:   {J_true_2:.4f} (+30% change)")
    print(f"  Final J_est:  {final_J:.4f}")
    print(f"  Final error:  {final_error:.2f}%")
    print(f"  Reidentified: {reidentified}")
    print(f"  Final state:  {estimator.state.name}")
    
    # Requirement: detect 20%+ drift and re-identify
    passed = reidentified and final_error < 10.0
    return print_result(passed, f"Drift detected: {reidentified}, Final accuracy: {final_error:.2f}%")

# ============================================================================
# MAIN VALIDATION
# ============================================================================

if __name__ == "__main__":
    print_header("T2.1.2 INERTIA ESTIMATOR VALIDATION")
    print("\nValidating compliance with ProWinder Roadmap requirements...")
    print(f"Implementation: Sequential Parameter Estimation + RLS Tracking")
    
    results = []
    
    # Run all tests
    results.append(test_1_precision())
    results.append(test_2_convergence())
    results.append(test_3_rls_stability())
    results.append(test_4_drift_detection())
    
    # Summary
    print_header("VALIDATION SUMMARY")
    passed = sum(results)
    total = len(results)
    percentage = passed / total * 100
    
    print(f"\n  Tests passed: {passed}/{total} ({percentage:.0f}%)")
    
    if passed == total:
        print(f"\n  {GREEN}✓ ALL TESTS PASSED - T2.1.2 VALIDATED{RESET}")
        sys.exit(0)
    elif passed >= total * 0.75:
        print(f"\n  {YELLOW}⚠ PARTIAL PASS - Some issues remain{RESET}")
        sys.exit(1)
    else:
        print(f"\n  {RED}✗ VALIDATION FAILED - Critical issues detected{RESET}")
        sys.exit(2)

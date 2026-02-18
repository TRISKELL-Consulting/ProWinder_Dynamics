"""
Validation script for T2.1.3 Tension Observer

Scenarios:
1) Zero speed: torque-based tension estimation
2) Blend transition: mid speed
3) High speed: span model dominance
"""
import sys
from pathlib import Path

import numpy as np

# Ensure src is on path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

from prowinder.control.tension_observer import TensionObserver
from prowinder.mechanics.material import MaterialProperties


def _material_props():
    return MaterialProperties(
        name="ValidationMaterial",
        density=1200.0,
        young_modulus=2.0e9,
        thickness=50e-6,
        width=1.0,
        viscosity=0.0,
    )


def test_zero_speed():
    props = _material_props()
    observer = TensionObserver(
        material_props=props,
        span_length=2.0,
        dt=0.01,
        omega_min=1.0,
        omega_max=5.0,
        ema_alpha=1.0,
        friction_observer=None,
        J_nominal=0.1,
    )

    estimate = observer.update(
        tau_motor=5.0,
        omega=0.0,
        alpha=0.0,
        R=0.1,
        v_upstream=0.0,
        v_downstream=0.0,
        J_total=0.1,
    )

    expected = 50.0
    error = abs(estimate.tension - expected) / expected * 100
    passed = error < 5.0
    print(f"[TEST 1] Zero speed: {error:.2f}% error (target < 5%) -> {passed}")
    return passed


def test_blend_transition():
    props = _material_props()
    observer = TensionObserver(
        material_props=props,
        span_length=2.0,
        dt=0.01,
        omega_min=1.0,
        omega_max=5.0,
        ema_alpha=1.0,
        friction_observer=None,
        J_nominal=0.1,
    )

    estimate = observer.update(
        tau_motor=10.0,
        omega=3.0,
        alpha=0.0,
        R=0.1,
        v_upstream=0.0,
        v_downstream=0.0,
        J_total=0.1,
    )

    passed = abs(estimate.weight - 0.5) < 1e-6 and estimate.mode == "fusion"
    print(f"[TEST 2] Blend transition: weight={estimate.weight:.2f}, mode={estimate.mode} -> {passed}")
    return passed


def test_high_speed_span():
    props = _material_props()
    observer = TensionObserver(
        material_props=props,
        span_length=2.0,
        dt=0.01,
        omega_min=1.0,
        omega_max=5.0,
        ema_alpha=1.0,
        friction_observer=None,
        J_nominal=0.1,
    )

    estimate = None
    for _ in range(200):
        estimate = observer.update(
            tau_motor=0.0,
            omega=6.0,
            alpha=0.0,
            R=0.1,
            v_upstream=10.0,
            v_downstream=10.5,
            J_total=0.1,
        )

    passed = estimate is not None and estimate.mode == "span" and estimate.tension_span > 0.0
    print(f"[TEST 3] High speed span: tension_span={estimate.tension_span:.2f} -> {passed}")
    return passed


def main():
    print("T2.1.3 Tension Observer Validation")
    results = [test_zero_speed(), test_blend_transition(), test_high_speed_span()]
    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} tests passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

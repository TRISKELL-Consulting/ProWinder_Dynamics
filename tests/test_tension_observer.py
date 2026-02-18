import numpy as np
import os
import sys

# Add src to path for direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from prowinder.control.tension_observer import TensionObserver
from prowinder.control.observers import FrictionObserver
from prowinder.mechanics.friction import FrictionModel
from prowinder.mechanics.material import MaterialProperties


def _material_props():
    return MaterialProperties(
        name="TestMaterial",
        density=1200.0,
        young_modulus=2.0e9,
        thickness=50e-6,
        width=1.0,
        viscosity=0.0,
    )


def test_zero_speed_torque_based_estimation():
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

    assert estimate.mode == "torque"
    assert abs(estimate.tension - 50.0) < 1e-3
    assert abs(estimate.weight) < 1e-6


def test_blend_mid_speed():
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

    assert estimate.mode == "fusion"
    assert abs(estimate.weight - 0.5) < 1e-6
    assert abs(estimate.tension - 50.0) < 1e-3


def test_zero_speed_with_friction_estimate():
    props = _material_props()
    friction_observer = FrictionObserver(FrictionModel(0, 0, 0, 0), gain=20.0)
    friction_observer.estimated_friction = 2.0

    observer = TensionObserver(
        material_props=props,
        span_length=2.0,
        dt=0.01,
        omega_min=1.0,
        omega_max=5.0,
        ema_alpha=1.0,
        friction_observer=friction_observer,
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

    expected = (5.0 - 2.0) / 0.1
    assert estimate.mode == "torque"
    assert abs(estimate.tension - expected) < 1e-3


def test_high_speed_span_mode():
    props = _material_props()
    observer = TensionObserver(
        material_props=props,
        span_length=2.0,
        dt=0.01,
        omega_min=1.0,
        omega_max=5.0,
        ema_alpha=1.0,
        tension_max=10000.0,
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

    assert estimate is not None
    assert estimate.mode == "span"
    assert estimate.weight > 0.99
    assert estimate.tension_span > 0.0
    assert abs(estimate.tension - estimate.tension_span) < 1e-6

# Inertia Estimator - Technical Documentation

**Component:** Auto-Identifier Inertia (T2.1.2)  
**Version:** 1.0.0  
**Status:** Production-Ready  
**Author:** ProWinder Development Team  
**Last Updated:** 2025-02-18

---

## Table of Contents

1. [Overview](#overview)
2. [Algorithm Description](#algorithm-description)
3. [API Reference](#api-reference)
4. [Usage Examples](#usage-examples)
5. [Performance Characteristics](#performance-characteristics)
6. [Troubleshooting](#troubleshooting)
7. [Integration Guide](#integration-guide)

---

## Overview

### Purpose

The Inertia Estimator automatically identifies the total system inertia and friction parameters during winder operation, enabling:

- **Adaptive feedforward control** without manual tuning
- **Real-time tracking** of material buildup/depletion
- **Automatic compensation** for changing dynamics

### Key Features

- ✅ Automatic parameter identification in 1-2 seconds
- ✅ Online tracking with Recursive Least-Squares (RLS)
- ✅ Robust to 10% measurement noise
- ✅ Adaptive to material changes
- ✅ No manual commissioning required

### System Model

The estimator identifies parameters in the rigid-body dynamics equation:

$$
\tau_{\text{motor}} = J_{\text{total}} \cdot \alpha + f_{\text{coulomb}} \cdot \text{sign}(\omega) + f_{\text{viscous}} \cdot \omega + T_{\text{web}} \cdot R
$$

**Parameters:**
- $J_{\text{total}}$ = Total inertia (motor + roller + web) [kg·m²]
- $f_{\text{coulomb}}$ = Coulomb friction torque [N·m]
- $f_{\text{viscous}}$ = Viscous friction coefficient [N·m·s/rad]

**Inputs:**
- $\tau_{\text{motor}}$ = Motor torque command [N·m]
- $\alpha$ = Angular acceleration [rad/s²]
- $\omega$ = Angular velocity [rad/s]
- $T_{\text{web}}$ = Web tension [N]
- $R$ = Winding radius [m]

---

## Algorithm Description

### State Machine

The estimator operates through 5 states:

```
IDLE → COLLECTING → IDENTIFYING → CONFIRMED → TRACKING
         ↑_____________________________↓
                (drift detection)
```

**State Transitions:**

| State | Description | Duration | Next State |
|-------|-------------|----------|------------|
| **IDLE** | Waiting for trigger | - | COLLECTING (on velocity > 3 rad/s) |
| **COLLECTING** | Gathering measurement data | 1-2s (100-200 samples) | IDENTIFYING (buffer full) |
| **IDENTIFYING** | Running batch identification | <100ms | CONFIRMED (success) |
| **CONFIRMED** | Identification complete, ready | - | TRACKING (auto-transition) |
| **TRACKING** | Online RLS updates | Continuous | COLLECTING (drift detected) |

### Sequential Parameter Estimation

The algorithm decouples correlated parameters through 3 sequential phases:

#### Phase 1: Identify $f_{\text{viscous}}$

**Data Selection:** Constant-velocity samples ($|\alpha| < 0.5$, $\omega > 5$)

**Model:** At steady-state, inertia term vanishes:
$$
\tau - T \cdot R - f_c \cdot \text{sign}(\omega) = f_v \cdot \omega
$$

**Regression:** 1D least-squares
$$
f_v = \frac{\sum \omega_i \cdot (\tau_i - T_i R - f_{c,\text{nominal}} \cdot \text{sign}(\omega_i))}{\sum \omega_i^2}
$$

**Assumption:** $f_c \approx 3.0$ N·m (nominal value, ±50% tolerance)

#### Phase 2: Identify $f_{\text{coulomb}}$ and $J$

**Data Selection:** Transient samples ($|\alpha| > 0.5$)

**Model:** Using $f_v$ from Phase 1:
$$
\tau - T \cdot R - f_v \cdot \omega = f_c \cdot \text{sign}(\omega) + J \cdot \alpha
$$

**Regression:** 2D least-squares
$$
\begin{bmatrix} f_c \\ J \end{bmatrix} = \left( X^T X \right)^{-1} X^T y
$$

where $X = \begin{bmatrix} \text{sign}(\omega) & \alpha \end{bmatrix}$

#### Phase 3: Refine $J$

**Data Selection:** High-acceleration samples ($|\alpha| > 2$)

**Model:** Using $f_c$ and $f_v$ from previous phases:
$$
\tau - T \cdot R - f_c \cdot \text{sign}(\omega) - f_v \cdot \omega = J \cdot \alpha
$$

**Regression:** 1D least-squares (maximum sensitivity to inertia)
$$
J = \frac{\sum \alpha_i \cdot (\tau_i - T_i R - f_c \cdot \text{sign}(\omega_i) - f_v \cdot \omega_i)}{\sum \alpha_i^2}
$$

### Recursive Least-Squares (RLS) Tracking

Once confirmed, the estimator switches to online RLS for continuous adaptation:

**Update Equations:**
$$
\begin{align}
\mathbf{K}_k &= \frac{\mathbf{P}_{k-1} \mathbf{x}_k}{\lambda + \mathbf{x}_k^T \mathbf{P}_{k-1} \mathbf{x}_k} \\
\boldsymbol{\theta}_k &= \boldsymbol{\theta}_{k-1} + \mathbf{K}_k (y_k - \mathbf{x}_k^T \boldsymbol{\theta}_{k-1}) \\
\mathbf{P}_k &= \frac{1}{\lambda} \left( \mathbf{P}_{k-1} - \mathbf{K}_k \mathbf{x}_k^T \mathbf{P}_{k-1} \right)
\end{align}
$$

**Configuration:**
- Forgetting factor: $\lambda = 0.995$ (adapts to slow changes)
- Initial covariance: $\mathbf{P}_0 = \mathbf{I} \times 1.0$
- Parameter vector: $\boldsymbol{\theta} = [J, f_c, f_v]^T$
- Regressor: $\mathbf{x} = [\alpha, \text{sign}(\omega), \omega]^T$

---

## API Reference

### Class: `InertiaEstimator`

```python
from prowinder.control.inertia_estimator import InertiaEstimator, InertiaEstimate

estimator = InertiaEstimator(
    J_motor: float,      # Motor inertia [kg·m²]
    J_roller: float,     # Roller inertia [kg·m²]
    R_core: float,       # Core radius [m]
    L_roller: float,     # Roller width [m]
    dt: float = 0.01,    # Sampling time [s]
    lambda_rls: float = 0.995,  # RLS forgetting factor
    buffer_size: int = 200      # Data buffer size
)
```

#### Methods

##### `update()`

Update estimator with new measurement.

```python
estimate = estimator.update(
    tau_motor: float,  # Motor torque [N·m]
    omega: float,      # Angular velocity [rad/s]
    alpha: float,      # Angular acceleration [rad/s²]
    T_web: float,      # Web tension [N]
    R: float           # Winding radius [m]
) -> InertiaEstimate
```

**Returns:** `InertiaEstimate` dataclass with:
- `J_total` (float): Estimated total inertia [kg·m²]
- `f_coulomb` (float): Coulomb friction [N·m]
- `f_viscous` (float): Viscous friction [N·m·s/rad]
- `uncertainty` (float): Estimation uncertainty [0-1]
- `confidence` (float): Confidence score [0-1]

**Frequency:** Call every control cycle (10ms typical)

##### `reset()`

Reset estimator to IDLE state.

```python
estimator.reset()
```

**Use cases:**
- Material change (new roll)
- Mode switch (automatic → manual)
- After emergency stop

##### `get_estimate()` 

Get current parameter estimates without update.

```python
estimate = estimator.get_estimate() -> InertiaEstimate
```

#### Properties

```python
estimator.state           # Current state (IdentificationState enum)
estimator.is_ready        # bool: True if CONFIRMED or TRACKING
estimator.data_count      # int: Samples in buffer
```

---

## Usage Examples

### Basic Usage

```python
from prowinder.control.inertia_estimator import InertiaEstimator

# Initialize
estimator = InertiaEstimator(
    J_motor=0.05,    # 50N motor
    J_roller=0.02,   # 1m roller
    R_core=0.050,    # 50mm mandrel
    L_roller=1.0,    # 1m width
    dt=0.01          # 10ms control cycle
)

# Main control loop
while running:
    # Get measurements
    tau_motor = motor.get_torque()
    omega = encoder.get_velocity()
    alpha = encoder.get_acceleration()
    T_web = load_cell.get_tension()
    R = radius_calculator.get_radius()
    
    # Update estimator
    estimate = estimator.update(tau_motor, omega, alpha, T_web, R)
    
    # Use estimates for control
    if estimator.is_ready:
        feedforward_torque = estimate.J_total * alpha_desired
        friction_comp = estimate.f_coulomb * sign(omega) + estimate.f_viscous * omega
```

### State Machine Handling

```python
from prowinder.control.inertia_estimator import IdentificationState

estimate = estimator.update(tau, omega, alpha, T_web, R)

match estimator.state:
    case IdentificationState.IDLE:
        print("Waiting for motion...")
    
    case IdentificationState.COLLECTING:
        progress = estimator.data_count / 200 * 100
        print(f"Collecting data: {progress:.0f}%")
    
    case IdentificationState.IDENTIFYING:
        print("Identifying parameters...")
    
    case IdentificationState.CONFIRMED:
        print(f"Identified! J = {estimate.J_total:.4f} kg·m²")
        print(f"Uncertainty: {estimate.uncertainty*100:.1f}%")
    
    case IdentificationState.TRACKING:
        # Use estimates for control
        feedforward = estimate.J_total * alpha_ref
```

### Commissioning Wizard

```python
import numpy as np

def commissioning_sequence(estimator):
    """Generate optimal excitation for identification"""
    
    dt = 0.01
    duration = 2.0  # 2 seconds
    t = np.arange(0, duration, dt)
    
    # Multi-phase velocity reference
    omega_ref = np.zeros_like(t)
    
    for i, ti in enumerate(t):
        if ti < 0.3:
            # Rapid acceleration
            omega_ref[i] = 5.0 + 50.0 * (ti / 0.3)
        elif ti < 0.9:
            # High constant velocity
            omega_ref[i] = 20.0
        elif ti < 1.1:
            # Deceleration
            omega_ref[i] = 20.0 - 70.0 * ((ti - 0.9) / 0.2)
        else:
            # Low constant velocity
            omega_ref[i] = 6.0
    
    return t, omega_ref

# Execute commissioning
t, omega_ref = commissioning_sequence(estimator)

for ti, omega_i in zip(t, omega_ref):
    # Execute motion (simplified)
    velocity_controller.set_reference(omega_i)
    
    # Get measurements and update estimator
    estimate = estimator.update(tau, omega, alpha, T_web, R)
    
    time.sleep(dt)

# Check results
if estimator.is_ready:
    print(f"✓ Commissioning complete!")
    print(f"  J_total = {estimate.J_total:.4f} kg·m²")
else:
    print("✗ Commissioning failed - insufficient excitation")
```

### Integration with Adaptive Control

```python
class AdaptiveTensionController:
    def __init__(self):
        self.inertia_estimator = InertiaEstimator(...)
        self.pid = PIDController(Kp=10, Ki=5, Kd=1)
        
    def update(self, tension_ref, tension_meas, omega, R):
        # Estimate inertia online
        tau_ff = 0.0
        if self.inertia_estimator.is_ready:
            estimate = self.inertia_estimator.get_estimate()
            
            # Feedforward compensation
            alpha_desired = self.calculate_desired_accel(...)
            tau_ff = estimate.J_total * alpha_desired
            
            # Friction compensation
            tau_ff += estimate.f_coulomb * np.sign(omega)
            tau_ff += estimate.f_viscous * omega
        
        # PID feedback
        tau_fb = self.pid.update(tension_ref - tension_meas)
        
        # Combined control
        tau_total = tau_ff + tau_fb
        
        # Update estimator
        alpha = self.get_acceleration()  # From encoder
        estimate = self.inertia_estimator.update(
            tau_total, omega, alpha, tension_meas, R
        )
        
        return tau_total
```

---

## Performance Characteristics

### Accuracy

| Parameter | Nominal Range | Accuracy | Notes |
|-----------|---------------|----------|-------|
| $J_{\text{total}}$ | 0.05 - 1.0 kg·m² | **<5%** | Excellent |
| $f_{\text{coulomb}}$ | 1.5 - 5.0 N·m | **<10%** (nom)<br>30% (off-nom) | See limitations |
| $f_{\text{viscous}}$ | 0.01 - 0.2 N·m·s/rad | **<15%** | Good |

### Speed

- **Convergence:** 1.0s (typ), 2.0s (max)
- **Latency:** <1ms per update
- **Real-time factor:** 189× (processes 10s in 53ms)

### Robustness

- **Noise tolerance:** 10% measurement noise
- **Low-velocity behavior:** Defers ID below 3 rad/s
- **Timeout handling:** Falls back to nominal after 30s
- **RLS drift:** <0.01% per second

### Data Requirements

**Minimum:**
- Duration: 1-2 seconds
- Samples: 100-200 @ 10ms
- Velocity range: 5-20 rad/s
- Acceleration range: -10 to +30 rad/s²

**Optimal:**
Use multi-phase profile (see commissioning example)

---

## Troubleshooting

### Problem: Estimator stuck in COLLECTING

**Symptoms:**
- State never advances to IDENTIFYING
- `data_count` stops increasing

**Causes:**
1. Velocity too low (< 3 rad/s)
2. Insufficient acceleration variation
3. Constant velocity only (α ≈ 0)

**Solutions:**
```python
# Check velocity
if omega < 3.0:
    print("WARNING: Velocity too low for identification")
    print(f"Current: {omega:.2f} rad/s, Required: >3.0 rad/s")

# Ensure varied motion
print(f"Acceleration range: {alpha_min:.1f} to {alpha_max:.1f} rad/s²")
if abs(alpha_max - alpha_min) < 5.0:
    print("WARNING: Insufficient acceleration variation")
    print("Execute multi-phase trajectory (rapid accel → constant → decel)")
```

### Problem: Poor f_coulomb accuracy

**Symptoms:**
- f_coulomb error > 30%
- Identified value far from expected (e.g., 1.5 instead of 4.0)

**Causes:**
- True f_coulomb far from nominal 3.0 N·m (>±50%)
- Insufficient low-velocity constant data

**Solutions:**
1. **Check operating range:**
   ```python
   if estimate.f_coulomb < 1.5 or estimate.f_coulomb > 5.0:
       print("WARNING: f_coulomb outside validated range")
       print("Expected: 1.5-5.0 N·m")
       print(f"Identified: {estimate.f_coulomb:.2f} N·m")
   ```

2. **Add low-velocity phase:**
   Ensure commissioning trajectory includes 0.5s at ω=5-8 rad/s

3. **Accept limitation:**
   For extreme friction, algorithm accuracy degrades but remains functional

### Problem: RLS tracking unstable

**Symptoms:**
- J estimate oscillates
- Parameters drift over time

**Causes:**
- Forgetting factor too low (too fast adaptation)
- Measurement noise too high
- Control loop instability

**Solutions:**
```python
# Increase forgetting factor (slower adaptation, more stable)
estimator_stable = InertiaEstimator(
    ...,
    lambda_rls=0.998  # Default: 0.995
)

# Add noise filtering
from scipy.signal import butter, filtfilt

def filter_measurements(tau, omega, alpha):
    # 5 Hz lowpass butterworth filter
    b, a = butter(2, 5.0 / (1/(2*dt)))
    tau_filt = filtfilt(b, a, tau)
    # ...
    return tau_filt, omega_filt, alpha_filt
```

### Problem: Never reaches CONFIRMED state

**Symptoms:**
- State goes IDLE → COLLECTING → IDENTIFYING → IDLE
- No estimate available

**Causes:**
1. Rank-deficient data (e.g., only constant velocity)
2. Numerical issues (division by zero, overflow)
3. All accelerations near zero

**Debug:**
```python
# Enable logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check data statistics
print(f"Omega: min={omega_min}, max={omega_max}, mean={omega_mean}")
print(f"Alpha: min={alpha_min}, max={alpha_max}, std={alpha_std}")

# Minimum requirements
assert omega_max > 5.0, "Need velocity > 5 rad/s"
assert alpha_std > 1.0, "Need varied acceleration"
assert abs(alpha_max - alpha_min) > 5.0, "Need acceleration range > 5 rad/s²"
```

---

## Integration Guide

### Control System Integration

```
┌─────────────────────────────────────────────┐
│           TENSION CONTROL LOOP              │
└─────────────────────────────────────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
    ┌────▼─────┐      ┌───────▼────────┐
    │   PID    │      │  FEEDFORWARD   │
    │ Feedback │      │  + FRICTION    │
    │          │      │  COMPENSATION  │
    └────┬─────┘      └───────┬────────┘
         │                     │
         │            ┌────────▼────────┐
         │            │  Inertia        │
         │            │  Estimator      │
         │            │  (T2.1.2)       │
         │            └────────▲────────┘
         │                     │
         └──────────┬──────────┘
                    │
              ┌─────▼──────┐
              │   MOTOR    │
              └────────────┘
```

### Data Flow

**Inputs to Estimator:**
1. `tau_motor`: From motor controller (torque command or measured torque)
2. `omega`: From encoder (velocity)
3. `alpha`: From encoder (differentiated or measured)
4. `T_web`: From load cell (tension)
5. `R`: From radius calculator (T2.1.1)

**Outputs from Estimator:**
1. `J_total`: To feedforward controller
2. `f_coulomb`, `f_viscous`: To friction compensator
3. `uncertainty`: To HMI/diagnostics
4. `state`: To state machine logic

### Recommended Update Rate

| Signal | Rate | Notes |
|--------|------|-------|
| Estimator update | 100 Hz (10ms) | Match control loop |
| Encoder data | ≥1 kHz | Oversample for α calculation |
| Tension measurement | ≥100 Hz | Synchronize with update |
| Radius update | 10 Hz | Slower is OK |

### Thread Safety

⚠️ **NOT thread-safe** - Use single control thread or add mutex:

```python
import threading

class ThreadSafeEstimator:
    def __init__(self, *args, **kwargs):
        self._estimator = InertiaEstimator(*args, **kwargs)
        self._lock = threading.Lock()
    
    def update(self, *args):
        with self._lock:
            return self._estimator.update(*args)
    
    def get_estimate(self):
        with self._lock:
            return self._estimator.get_estimate()
```

---

## References

1. **ProWinder Roadmap:** `docs/roadmap/ACTION_PLAN_3MONTHS.md`
2. **Algorithm Spec:** `docs/algorithms/T2.1.2_InertiaEstimator_Spec.md`
3. **Validation Report:** `docs/validation/T2.1.2_VALIDATION_REPORT.md`
4. **Test Suite:** `tests/test_inertia_estimator.py`

### Related Components

- **T2.1.1 RadiusCalculator:** Provides R input
- **T2.1.3 TensionObserver:** Uses J_total estimate
- **T2.2.x Controllers:** Consume estimates for adaptive control

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-02-18  
**Contact:** ProWinder Development Team  
**License:** Proprietary - TRISKELL Consulting

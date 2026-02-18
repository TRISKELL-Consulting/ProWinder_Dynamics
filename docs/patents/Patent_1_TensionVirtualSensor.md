# Patent #1 - Virtual Sensor Tension Control (Sensorless at V=0)

**Project:** ProWinder Dynamics
**Date:** 2026-02-18
**Inventor:** Jaouher ROMDHANE
**Status:** Draft - Technical Description

---

## 1. Title

**Virtual Sensor for Web Tension Estimation at Zero or Low Velocity**

---

## 2. Field of the Invention

This invention relates to web handling systems (winding and unwinding) and, more specifically, to a method and system for estimating web tension without direct tension sensors when the web speed is zero or near zero.

---

## 3. Background and Problem

Industrial winding/unwinding systems typically measure web tension using load cells. At zero or very low speed, load cell readings become unreliable due to drift, noise, and static friction effects. Existing systems often fail to regulate tension in these regimes, leading to slack, wrinkling, or web breaks during start/stop and splicing operations.

There is a need for a sensorless (virtual) tension estimation approach that remains accurate even at $\omega \to 0$.

---

## 4. Summary of the Invention

The invention provides a **virtual tension sensor** that estimates web tension using a combination of:

- A **friction observer** to estimate disturbance torque at low speed
- A **dynamic model of the web span** to propagate strain and tension
- A **fusion mechanism** (e.g., Kalman-style or weighted blending) that switches or blends between direct measurements (when speed is sufficient) and virtual estimation (when speed is near zero)

This enables stable tension control in regimes where conventional load cells are unreliable or unavailable.

---

## 5. Core Innovation

### 5.1 Sensorless Estimation at V=0

At low speed, the motor torque balance is dominated by friction and static tension. The invention exploits:

$$
\tau_{\text{motor}} = J \cdot \alpha + \tau_{\text{friction}} + T \cdot R
$$

By estimating $\tau_{\text{friction}}$ with an observer and measuring $\tau_{\text{motor}}$, $\alpha$, and $R$, the tension $T$ can be inferred:

$$
T = \frac{\tau_{\text{motor}} - J \cdot \alpha - \tau_{\text{friction}}}{R}
$$

This formula holds even when $\omega \approx 0$.

### 5.2 Fusion With Web Span Model

A model of the web span is used to propagate strain and tension dynamically:

$$
\frac{d\epsilon}{dt} = \frac{v_2 - v_1}{L} + \frac{v_1}{L}(\epsilon_{\text{in}} - \epsilon)
$$

The estimated tension from the motor torque balance is fused with the modeled tension to reduce noise and improve robustness.

### 5.3 Mode Switching / Blending Logic

The invention defines operating regimes:

- **High speed ($|\omega| > \omega_{\text{min}}$):** trust load cell or direct measurement
- **Low speed ($|\omega| \le \omega_{\text{min}}$):** use virtual sensor estimate
- **Transition:** weighted blending to avoid discontinuity

---

## 6. Key Advantages

- Maintains tension estimation at zero or near-zero speed
- Reduces dependency on load cells (cost, calibration, drift)
- Improves start/stop and splicing reliability
- Enables smoother tension control during transient regimes

---

## 7. Claims (Draft)

1. **A method for estimating web tension in a winding/unwinding system**, comprising:
   - measuring motor torque, angular acceleration, and winding radius;
   - estimating friction torque using a disturbance observer;
   - computing web tension from the torque balance even when web speed is near zero.

2. **The method of claim 1**, further comprising:
   - modeling web span strain dynamics;
   - fusing the model-based tension with the torque-based tension estimate.

3. **The method of claim 1**, wherein the system switches or blends between direct tension measurement and virtual estimation based on web speed.

4. **A system for sensorless web tension estimation**, comprising:
   - a motor torque sensor or command input;
   - an inertia estimator and friction observer;
   - a computation module configured to output web tension at $\omega \approx 0$.

5. **The system of claim 4**, wherein a Kalman or weighted fusion mechanism is used to ensure smooth transition between estimation modes.

---

## 8. Potential Prior Art Gaps

- Most existing systems use load cells or require motion for estimation
- Known observers focus on friction or torque, not tension at zero speed
- Fusion of span dynamics with torque-balance for sensorless tension at V=0 appears novel

---

## 9. Implementation Notes

ProWinder implementation will be located in:

- `src/prowinder/control/tension_observer.py`
- Integration with `FrictionObserver` and `WebSpan`
- Validation script: `scripts/validation/validate_T2.1.3.py`

Current integration:
- Digital Twin closed-loop tension mode uses the sensorless estimate at low speed
- Measured tension can be blended at higher speed

---

## 10. Next Steps

- Extend validation with friction and V=0 transients
- Compare against load cell data (if available)
- Refine claims with legal counsel

---

**End of Document**

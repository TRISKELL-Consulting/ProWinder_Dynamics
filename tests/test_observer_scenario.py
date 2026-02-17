import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# Add src to path so we can import the package
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from prowinder.mechanics.friction import FrictionModel
from prowinder.control.observers import FrictionObserver

def run_simulation():
    # 1. Setup Simulation Parameters
    dt = 0.001  # 1 ms sample time
    total_time = 2.0
    time_steps = int(total_time / dt)
    time = np.linspace(0, total_time, time_steps)
    
    # System Parameters
    J_system = 0.05  # Inertia (kg.m^2)
    
    # 2. Define Real Plant Friction (The "Truth")
    # Stribeck curve parameters
    real_plant_friction = FrictionModel(
        coulomb_coeff=0.5,   # Nm
        viscous_coeff=0.01,  # Nm/(rad/s)
        stiction_coeff=1.0,  # Nm (Peak at zero speed)
        stribeck_velocity=0.1 # rad/s
    )
    
    # 3. Define Observer (The "Estimator")
    # The observer might have slightly imperfect knowledge of the model structure, 
    # but here we give it a simple model reference and rely on the disturbance estimator.
    observer_model = FrictionModel(0, 0, 0, 0) # Observer starts with empty knowledge in this test
    observer = FrictionObserver(observer_model, gain=50.0) # High gain for fast tracking
    
    # 4. Simulation Arrays
    velocities_real = np.zeros(time_steps)
    velocities_meas = np.zeros(time_steps)
    
    torques_applied = np.zeros(time_steps)
    friction_real_hist = np.zeros(time_steps)
    friction_est_hist = np.zeros(time_steps)
    
    # Initial State
    omega = 0.0
    
    print("Starting Friction Observer Simulation...")
    print(f"Simulating {total_time}s with dt={dt}s")
    
    for i in range(time_steps):
        t = time[i]
        
        # A. Profile de Couple (Applied Torque)
        # Sequence: 0 -> Ramp Up -> Constant -> Ramp Down -> Zero Cross -> Negative
        if t < 0.2:
            torque_motor = 0
        elif t < 0.8:
            torque_motor = 1.5 # Break stiction (needs > 1.0 Nm)
        elif t < 1.4:
            torque_motor = 0.6 # Lower torque, maintain speed
        else:
            torque_motor = -1.2 # Reverse
            
        torques_applied[i] = torque_motor
        
        # B. Real System Dynamics (Physics)
        # Calculate real friction based on current velocity
        torque_friction_real = real_plant_friction.compute_torque(omega)
        friction_real_hist[i] = torque_friction_real
        
        # Newton's Law: J * dw/dt = T_motor - T_friction
        accel = (torque_motor - torque_friction_real) / J_system
        omega += accel * dt
        
        # Stop perfectly at zero if friction > torque (simple zero-clamping for simulation)
        if abs(omega) < 1e-4 and abs(torque_motor) < abs(real_plant_friction.Ts):
             # Stick phase logic simplified
             if abs(omega) < 1e-5:
                 omega = 0
        
        velocities_real[i] = omega
        
        # C. Sensor Noise (Optional)
        measurement_noise = np.random.normal(0, 0.001)
        omega_measured = omega + measurement_noise
        velocities_meas[i] = omega_measured
        
        # D. Observer Update
        # The observer assumes: J * dw/dt = T_motor - T_friction_est
        # It corrects T_friction_est based on prediction errors
        friction_est = observer.update(omega_measured, torque_motor, dt, J_system)
        friction_est_hist[i] = friction_est

    # 5. Visualisation
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 8))
    
    # Plot Velocity
    ax1.plot(time, velocities_real, 'b-', label='Vitesse Réelle (rad/s)', linewidth=2)
    ax1.set_ylabel('Vitesse (rad/s)')
    ax1.set_title('Test Observateur de Friction - Scénario Démarrage / Inversion')
    ax1.grid(True)
    ax1.legend()
    
    # Plot Friction: Truth vs Estimate
    ax2.plot(time, friction_real_hist, 'g-', label='Friction Réelle (Modèle)', alpha=0.6, linewidth=2)
    ax2.plot(time, friction_est_hist, 'r--', label='Friction Estimée (Observateur)')
    ax2.plot(time, torques_applied, 'k:', label='Couple Moteur Appliqué', alpha=0.3)
    
    ax2.set_xlabel('Temps (s)')
    ax2.set_ylabel('Couple (Nm)')
    ax2.grid(True)
    ax2.legend()
    
    plt.tight_layout()
    print("Simulation complete. Saving plot to 'friction_observer_test.png'")
    # Check if we assume a display is available, otherwise save
    try:
        plt.savefig('friction_observer_test.png')
        print("Plot saved successfully.")
    except Exception as e:
        print(f"Could not save plot: {e}")

if __name__ == "__main__":
    run_simulation()

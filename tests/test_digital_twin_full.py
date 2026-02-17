import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from prowinder.simulation.digital_twin import DigitalTwin, SystemConfig
from prowinder.mechanics.material import MaterialProperties
from prowinder.mechanics.motor import MotorSpecs

def run_full_simulation():
    # 1. Setup Simulation Configuration
    # We want a scenario that highlights the elasticity and inertia effects
    config = SystemConfig(
        dt=0.001,          # 1 ms time step
        duration=4.0,      # 4 seconds simulation
        initial_radius=0.3, # Start with a partial roll
        # Thin PET film (elastic)
        material=MaterialProperties(
            name="PET_Film", 
            density=1400, 
            young_modulus=4e9, # 4 GPa
            thickness=50e-6,   # 50 microns
            width=1.0          # 1 meter
        ),
        # High performance servo motor
        motor_specs=MotorSpecs(
            name="Servo_10Nm",
            rated_torque=10.0,
            max_speed=300.0,
            rotor_inertia=0.005
        ),
        span_length=2.0 # 2 meters of web span
    )
    
    twin = DigitalTwin(config)
    
    # 2. Define Reference Profiles
    # Standard trapezoidal speed profile
    def get_references(t):
        # Speed Ramp: 0 -> 5 m/s in 1.0s
        if t < 0.5:
            v_ref = 0.0
        elif t < 1.5:
            v_ref = (t - 0.5) * 5.0 # Slope = 5 m/s^2
        else:
            v_ref = 5.0
            
        # Tension Reference: 100 N constant
        t_ref = 100.0
        
        return v_ref, t_ref

    # 3. Run Simulation Loop
    steps = int(config.duration / config.dt)
    print(f"Running Full Digital Twin Simulation ({steps} steps)...")
    
    for i in range(steps):
        t = i * config.dt
        v_ref, t_ref = get_references(t)
        
        twin.step(speed_ref=v_ref, tension_ref=t_ref)

    # 4. Extract Data
    history = twin.history
    time = np.array(history['time'])
    speed = np.array(history['omega']) * np.array(history['radius']) # Line speed approx
    radius = np.array(history['radius'])
    tension = np.array(history['tension'])
    torque = np.array(history['torque'])

    # 5. Plotting
    fig, axs = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
    
    # Plot 1: Speed
    axs[0].plot(time, speed, 'b-', label='Vitesse Linéaire (m/s)')
    # Add reference preview
    ref_speed = [get_references(ti)[0] for ti in time]
    axs[0].plot(time, ref_speed, 'k--', alpha=0.5, label='Consigne Vitesse')
    axs[0].set_ylabel('Vitesse (m/s)')
    axs[0].set_title('Digital Twin: Performance Dynamique')
    axs[0].legend()
    axs[0].grid(True)

    # Plot 2: Tension
    axs[1].plot(time, tension, 'r-', label='Tension Réelle (WebSpan)')
    axs[1].axhline(y=100.0, color='k', linestyle='--', alpha=0.5, label='Consigne (100N)')
    axs[1].set_ylabel('Tension (N)')
    axs[1].legend()
    axs[1].grid(True)
    
    # Plot 3: Radius & Torque
    ax3 = axs[2]
    ax3.plot(time, torque, 'g-', label='Couple Moteur (Nm)')
    ax3.set_ylabel('Couple (Nm)', color='g')
    ax3.tick_params(axis='y', labelcolor='g')
    ax3.grid(True)
    
    ax3b = ax3.twinx()
    ax3b.plot(time, radius * 1000, 'm--', label='Rayon (mm)')
    ax3b.set_ylabel('Rayon (mm)', color='m')
    ax3b.tick_params(axis='y', labelcolor='m')
    
    axs[2].set_xlabel('Temps (s)')
    
    plt.tight_layout()
    plot_file = 'digital_twin_full_test.png'
    try:
        plt.savefig(plot_file)
        print(f"Simulation comparison saved to {plot_file}")
    except Exception as e:
        print(f"Error saving plot: {e}")

if __name__ == "__main__":
    run_full_simulation()

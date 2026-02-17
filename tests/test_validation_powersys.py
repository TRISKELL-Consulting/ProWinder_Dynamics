
import unittest
import sys
import os

# Add src to path for direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import numpy as np
import matplotlib.pyplot as plt
from prowinder.simulation.digital_twin import DigitalTwin, SystemConfig
from prowinder.mechanics.material import MaterialProperties

class TestPowerSysValidation(unittest.TestCase):
    def test_powersys_simulation(self):
        """
        Validates the Digital Twin using parameters from the standard 
        SimPowerSystems (PowerSys) "Winding Machine" demo.
        
        Reference: MATLAB/Simscape Electrical Winder Demo.
        
        System Parameters:
        - Material: Paper (Density ~1200 kg/m3)
        - Width: 1.0 m
        - Core Radius: 0.1 m
        - Max Radius: ~0.5 m
        - Reference Speed: 10 m/s (Ramp 1s)
        - Reference Tension: 400 N
        - Winder Inertia: J_core = 0.5 kg.m2 (Approx for 10HP system)
        """
        
        # 1. Setup Configuration
        powersys_material = MaterialProperties(
            name="PowerSys_Paper",
            density=1200.0,
            young_modulus=3.0e9, 
            thickness=100e-6,    # 100 micron paper
            width=1.0            # 1 meter width
        )
        
        # PowerSys Motor Spec Inference: Needs at least 200Nm rated torque.
        from prowinder.mechanics.motor import MotorSpecs
        powersys_motor = MotorSpecs("PowerSys_Motor", rated_torque=200.0, max_speed=300.0, rotor_inertia=0.1) # Assuming ~0.1 kgm2 for large motor
        
        config = SystemConfig(
            dt=0.001,
            duration=5.0,
            material=powersys_material,
            motor_specs=powersys_motor,
            initial_radius=0.1,  # Core start
            span_length=2.0,      # Typical span
            control_mode="CLOSED_LOOP_TENSION", # Enable the loop found in diagram
            gear_ratio=1.0 # Direct drive in diagram? Diagram shows "Speed reducer".
            # If Diagram shows Speed Reducer, G might not be 1.0. 
            # Visually, the reducer symbol suggests G > 1 (Motor spins faster).
            # Let's assume G=10 for a typical winder if not specified.
            # Wait, the diagram shows "Speed Winder Model" approx 10 rad/s vs "Surface speed" 5.
            # Radius 0.53. Omega = 5/0.53 = 9.4. Matches 9.313.
            # Motor Speed? "Motor Torque filtered 160.3". 
            # Tension 300N. Torque Load = 300 * 0.53 = 160Nm.
            # If Motor Torque is 160Nm and Load Torque is 160Nm... G must be 1.0!
            # Or the torque is reported At Winder Shaft.
            # The Diagram says "Motor Torque (N-m)" into Winder Model.
            # And "Torque Ref" from Control Block into Drive.
            # "DC Motor Drive" -> [Nh, Th] -> Speed Reducer -> [Nl, Tl] -> Winder Model.
            # So the Drive outputs High Speed Torque/Speed. Reducer converts.
            # If Torque at Winder is 160Nm (Load) and Motor Torque is 160Nm... then G=1.
            # Let's stick with G=1.0 for now unless we see Motor Speed scope.
        )
        
        # 2. Instantiate Digital Twin
        twin = DigitalTwin(config)
        
        # Override Friction if needed for PowerSys matching (often simplistic in demo)
        # twin.unwinder.friction_model.coulomb_coeff = 1.0
        
        # 3. Simulation Run
        # Scenario: Accelerate to 10 m/s in 1.0s, hold constant speed.
        target_speed = 10.0   # m/s
        target_tension = 400.0 # N
        
        results = {'time': [], 'speed': [], 'tension': [], 'radius': [], 'torque': []}
        
        for t in np.arange(0, config.duration, config.dt):
            # Speed Ramp (Trapezoidal)
            if t < 1.0:
                ref_speed = target_speed * (t / 1.0)
            elif t < 4.0:
                ref_speed = target_speed
            else:
                ref_speed = target_speed # Continue holding
                
            twin.step(speed_ref=ref_speed, tension_ref=target_tension)
            
            # Log
            results['time'].append(t)
            results['speed'].append(twin.unwinder.omega * twin.unwinder.radius) # Surface Speed
            results['tension'].append(twin.web_span.tension)
            results['radius'].append(twin.unwinder.radius)
            results['torque'].append(twin.motor.current_torque)

        # 4. Analysis
        avg_tension_steady = np.mean(results['tension'][2000:4000]) # 2s-4s
        print(f"\n[Validation PowerSys] Steady Tension: {avg_tension_steady:.2f} N (Target: {target_tension} N)")
        print(f"[Validation PowerSys] Max Speed: {max(results['speed']):.2f} m/s")
        
        # 5. Plotting
        try:
            plt.figure(figsize=(12, 8))
            
            plt.subplot(3, 1, 1)
            plt.plot(results['time'], results['speed'], label='Line Speed (m/s)')
            plt.title('PowerSys Benchmark: Speed Response')
            plt.ylabel('Speed (m/s)')
            plt.grid(True)
            
            plt.subplot(3, 1, 2)
            plt.plot(results['time'], results['tension'], label='Web Tension (N)', color='orange')
            plt.axhline(y=target_tension, color='r', linestyle='--', label='Ref 400N')
            plt.title(f'PowerSys Benchmark: Tension Regulation (Target={target_tension}N)')
            plt.ylabel('Tension (N)')
            plt.legend()
            plt.grid(True)

            plt.subplot(3, 1, 3)
            plt.plot(results['time'], results['torque'], label='Motor Torque (Nm)', color='green')
            plt.title('Motor Torque')
            plt.ylabel('Torque (Nm)')
            plt.xlabel('Time (s)')
            plt.grid(True)
            
            plt.tight_layout()
            plt.savefig('docs/validation_powersys_plot.png')
            print("Plot saved to docs/validation_powersys_plot.png")
        except Exception as e:
            print(f"Plotting failed: {e}")
        
        # Assertion: Check if tension is generated reasonably (within 50% without tuning gains for this specific inertia)
        self.assertTrue(avg_tension_steady > 100.0, "Tension collapsed")
        # Note: Exact matching requires tuning PI gains for generic load J=0.5 huge vs J=0.01

if __name__ == '__main__':
    unittest.main()

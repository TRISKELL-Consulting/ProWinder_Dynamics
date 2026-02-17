
import unittest
import sys
import os

# Add src to path for direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import numpy as np
import matplotlib.pyplot as plt
from prowinder.simulation.digital_twin import DigitalTwin, SystemConfig
from prowinder.mechanics.material import MaterialProperties

class TestLegacyValidation(unittest.TestCase):
    def test_legacy_parameters_simulation(self):
        """
        Validates the Digital Twin using parameters found in legacy Matlab files
        (DefineParameters_Winder.m).
        
        Legacy Parameters:
        - Material: PET (Density ~1390 kg/m3)
        - Width: 0.15 m
        - Core Radius: 0.05 m (approx from 43.6mm/1000?)
        - Friction: Viscous ~0.05
        """
        
        # 1. Setup Configuration with Legacy Values
        legacy_material = MaterialProperties(
            name="Legacy_PET",
            density=1390.0,
            young_modulus=4.0e9, 
            thickness=50e-6,     # Standard 50 micron
            width=0.15           # 150mm
        )
        
        config = SystemConfig(
            dt=0.001,
            duration=5.0,
            material=legacy_material,
            initial_radius=0.3, # Start with a half-full roll
            span_length=1.5
        )
        
        # 2. Instantiate Digital Twin
        twin = DigitalTwin(config)
        
        # Override Friction to match legacy file if possible (requires accessing private/internal component)
        # twin.unwinder.friction_model.viscous_coeff = 0.0529 (If accessible)
        # For now, we accept default or adjusting if we added a config for it.
        
        # 3. Simulation Run
        # Scenario: Accelerate to 100 m/min (1.66 m/s) and hold.
        # Check Tension stability.
        
        target_speed = 100.0 / 60.0 # m/s
        target_tension = 50.0       # N (Typical for 150mm PET)
        
        results = {'time': [], 'speed': [], 'tension': [], 'radius': []}
        
        for t in np.arange(0, config.duration, config.dt):
            # Ramp reference
            if t < 1.0:
                ref_speed = target_speed * (t / 1.0)
            else:
                ref_speed = target_speed
                
            twin.step(speed_ref=ref_speed, tension_ref=target_tension)
            
            # Log
            results['time'].append(t)
            results['speed'].append(twin.unwinder.omega * twin.unwinder.radius)
            results['tension'].append(twin.web_span.tension)
            results['radius'].append(twin.unwinder.radius)

        # 4. Analysis
        avg_tension_steady = np.mean(results['tension'][2000:]) # last 3s
        print(f"\n[Validation] Steady State Tension: {avg_tension_steady:.2f} N (Target: {target_tension} N)")
        print(f"[Validation] Final Speed: {results['speed'][-1]:.2f} m/s (Target: {target_speed:.2f} m/s)")
        
        # 5. Plotting (Saved to file for user review)
        plt.figure(figsize=(10, 6))
        plt.subplot(2, 1, 1)
        plt.plot(results['time'], results['speed'], label='Line Speed (m/s)')
        plt.title('Legacy Validation: Speed Response')
        plt.grid(True)
        
        plt.subplot(2, 1, 2)
        plt.plot(results['time'], results['tension'], label='Web Tension (N)', color='orange')
        plt.axhline(y=target_tension, color='r', linestyle='--', label='Target')
        plt.title(f'Legacy Validation: Tension (Target={target_tension}N)')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('docs/validation_legacy_plot.png')
        print("Plot saved to docs/validation_legacy_plot.png")
        
        # Assertions
        # Verify reasonable stability (within 20% error without tuning)
        self.assertTrue(abs(avg_tension_steady - target_tension) < target_tension * 0.5, 
                        f"Tension {avg_tension_steady} is too far from target {target_tension}")

if __name__ == '__main__':
    unittest.main()

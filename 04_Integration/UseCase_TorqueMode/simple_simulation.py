import sys
import os

# Add the project root to the python path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import numpy as np
import matplotlib.pyplot as plt
from src.winding_lib.models.roller import Roller
from src.winding_lib.control.tension_control.pid_controller import PIDController

# Simulation parameters
dt = 0.01  # Time step
simulation_time = 10.0  # Total simulation time
steps = int(simulation_time / dt)

# Create components
roller = Roller(inertia=0.5, friction_coeff=0.1)
controller = PIDController(Kp=2.0, Ki=1.0, Kd=0.1, dt=dt)

# Target speed (rad/s)
target_speed = 10.0

# Simulation loop
time = np.linspace(0, simulation_time, steps)
speeds = []
torques = []

for t in time:
    current_speed = roller.angular_velocity
    
    # Calculate control output (torque)
    torque = controller.compute(target_speed, current_speed)
    
    # Update mechanics
    roller.update(torque, dt)
    
    # Store data
    speeds.append(current_speed)
    torques.append(torque)

# Plotting
plt.figure(figsize=(10, 6))
plt.subplot(2, 1, 1)
plt.plot(time, speeds, label='Roller Speed')
plt.axhline(target_speed, color='r', linestyle='--', label='Target Speed')
plt.title('Speed Control Simulation')
plt.ylabel('Speed (rad/s)')
plt.legend()
plt.grid(True)

plt.subplot(2, 1, 2)
plt.plot(time, torques, color='orange', label='Control Torque')
plt.xlabel('Time (s)')
plt.ylabel('Torque (N*m)')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()

print("Simulation complete. Check the plot.")

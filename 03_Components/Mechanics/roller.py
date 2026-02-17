import numpy as np

class Roller:
    """
    Represents a mechanical roller with inertia and friction.
    """
    def __init__(self, inertia, friction_coeff):
        """
        Initialize the roller.

        :param inertia: Moment of inertia (kg*m^2)
        :param friction_coeff: Viscous friction coefficient (N*m*s/rad)
        """
        self.inertia = inertia
        self.friction_coeff = friction_coeff
        self.angular_velocity = 0.0 # rad/s

    def update(self, torque, dt):
        """
        Update the roller's state based on applied torque.

        :param torque: Net torque applied to the roller (N*m)
        :param dt: Time step (s)
        """
        # Dynamics: T = J * alpha + B * omega
        # alpha = (T - B * omega) / J
        friction_torque = self.friction_coeff * self.angular_velocity
        net_torque = torque - friction_torque
        angular_acceleration = net_torque / self.inertia
        
        self.angular_velocity += angular_acceleration * dt
        return self.angular_velocity

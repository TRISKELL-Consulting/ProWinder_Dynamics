import numpy as np

class PIDController:
    """
    A simple PID controller implementation.
    """
    def __init__(self, Kp, Ki, Kd, dt):
        """
        Initialize the PID controller.

        :param Kp: Proportional gain
        :param Ki: Integral gain
        :param Kd: Derivative gain
        :param dt: Time step
        """
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.dt = dt
        self.integral = 0
        self.prev_error = 0

    def compute(self, setpoint, measured_value):
        """
        Compute the control output based on the setpoint and measured value.

        :param setpoint: The desired value
        :param measured_value: The current value from the sensor
        :return: Control output
        """
        error = setpoint - measured_value
        self.integral += error * self.dt
        derivative = (error - self.prev_error) / self.dt
        output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)
        self.prev_error = error
        return output

    def reset(self):
        """Reset the integral and previous error terms."""
        self.integral = 0
        self.prev_error = 0

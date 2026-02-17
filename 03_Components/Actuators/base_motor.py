class MotorInterface:
    def get_torque(self):
        raise NotImplementedError

    def set_speed(self, speed):
        raise NotImplementedError

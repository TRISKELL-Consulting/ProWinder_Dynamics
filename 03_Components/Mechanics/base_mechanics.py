class MechanicalComponent:
    def get_inertia(self):
        raise NotImplementedError

    def apply_forces(self):
        raise NotImplementedError

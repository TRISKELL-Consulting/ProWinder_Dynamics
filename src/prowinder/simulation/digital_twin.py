import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict

from prowinder.mechanics.motor import Motor, MotorSpecs
from prowinder.mechanics.winder import Winder
from prowinder.mechanics.material import WebMaterial, MaterialProperties
from prowinder.mechanics.friction import FrictionModel
from prowinder.mechanics.web_span import WebSpan, SpanProperties
from prowinder.control.observers import FrictionObserver
from prowinder.control.tension_observer import TensionObserver
from prowinder.control.filters import AdaptiveNotchFilter
from prowinder.mechanics.dynamics import InertiaTracker

@dataclass
class SystemConfig:
    dt: float = 0.001
    duration: float = 5.0
    # Updated default to match Legacy Project Parameters (Legacy_Matlab/WindingUnwinding/Winder/2_data/DefineParameters_Winder.m)
    # PET, Density=1390, Width=0.15m, Thickness=50um. Viscosity=5e7 (Calibrated Phase 1)
    material: MaterialProperties = field(default_factory=lambda: MaterialProperties("PET_Legacy", 1390.0, 4e9, 50e-6, width=0.15, viscosity=5e7))
    motor_specs: MotorSpecs = field(default_factory=lambda: MotorSpecs("Siemens_1FK7", 10.0, 300.0, 0.005))
    initial_radius: float = 0.2
    span_length: float = 1.5  # Adjusted to match validation setup
    
    # PowerSys Compatibility
    gear_ratio: float = 1.0
    control_mode: str = "CLOSED_LOOP_TENSION" # "OPEN_LOOP_TORQUE", "SPEED_LIMIT", "CLOSED_LOOP_TENSION"
    speed_kp: float = 10.0 # Speed Loop Gain
    speed_ki: float = 5.0  # Speed Loop Integral
    tension_kp: float = 0.5 # Tension Loop Gain
    tension_ki: float = 2.0 # Tension Loop Integral

    
class DigitalTwin:
    """
    Jumeau Numérique orienté Objet (Modular Design).
    Modèle inspiré de PowerSys : Blocs Séparés (Moteur, Charge, Span).
    """
    def __init__(self, config: SystemConfig):
        self.config = config
        self.time = 0.0
        
        # 1. Instantiate Components
        self.material = WebMaterial(config.material)
        
        self.motor = Motor(config.motor_specs)
        
        friction_winder = FrictionModel(coulomb_coeff=0.5, viscous_coeff=0.01, stiction_coeff=1.2, stribeck_velocity=0.5)
        
        # The Unwinder (Dérouleur)
        self.unwinder = Winder(
            name="Unwinder_01",
            core_inertia=0.02,
            core_radius=0.05,
            material=self.material,
            friction_model=friction_winder
        )
        self.unwinder.set_initial_state(config.initial_radius, initial_speed=0.0)
        
        # The Web Span (Zone de tension)
        self.web_span = WebSpan(
            material=self.material,
            props=SpanProperties(length=config.span_length, initial_tension=config.material.width * 100) # Dummy init
        )

        # 2. Control System Elements
        self.observer = FrictionObserver(FrictionModel(0,0,0,0), gain=20.0)
        # Use actual inertia for observer initialization
        J_est = self.unwinder.get_total_inertia()
        
        self.tension_observer = TensionObserver(
            material_props=config.material,
            span_length=config.span_length,
            dt=config.dt,
            friction_observer=None, # Disabled to avoid tension absorption
            J_nominal=J_est if J_est > 0.01 else 0.01,
        )
        self.notch_filter = AdaptiveNotchFilter(20.0, 10.0, 1/config.dt)
        self.speed_integrator = 0.0 # For Speed Control Loop
        self.tension_integrator = 0.0 # For Tension Control Loop
        self.prev_omega = 0.0
        
        # Data Logging
        self.history = {
            'time': [],
            'omega': [],
            'radius': [],
            'tension': [],
            'tension_est': [],
            'tension_mode': [],
            'torque': []
        }

    def step(self, speed_ref: float, tension_ref: float):
        dt = self.config.dt
        G = self.config.gear_ratio
        
        # --- A. SENSING (Virtual Sensors) ---
        meas_speed_winder = self.unwinder.omega 
        est_inertia_roll = self.unwinder.get_total_inertia()
        # Add Motor Inertia reflection: J_total = J_roll + J_motor * G^2
        # (Assuming perfect coupling)
        J_motor = self.config.motor_specs.rotor_inertia
        est_inertia_total = est_inertia_roll + J_motor * (G**2)
        
        meas_radius = self.unwinder.radius
        meas_tension = self.web_span.tension # Measured by Load Cell on span
        v_unwinder_surface = self.unwinder.omega * self.unwinder.radius
        v_process = speed_ref

        # Improve Acceleration Estimation (Crucial for V~0 and transients)
        # Simple backward difference introduces lag and noise.
        # But for simulation with clean signals, it should be fine IF timed correctly.
        # alpha_est at step k is (omega_k - omega_{k-1}) / dt. This is average accel over last step.
        # Tension at step k caused this acceleration? Or was result of torques at k-1?
        # Simulation loop:
        # Step k: Read State -> Calculate Control -> Apply Torque -> Physics Update -> State k+1
        # Here we are at State k.
        # omega_k is the result of integration from k-1 to k.
        # So (omega_k - omega_{k-1})/dt is the acceleration during (k-1, k).
        # We want to estimate tension using Torque Balance.
        # T_tension_avg = (J*alpha_avg - T_motor_avg + T_fric_avg) / R
        # We need T_motor applied during (k-1, k).
        # self.motor.current_torque stores the LAST applied torque (from k-1). Correct!
        
        alpha_est = (meas_speed_winder - self.prev_omega) / dt
        
        # Use previous step's torque for estimation to match the alpha time window
        torque_for_obs = self.motor.current_torque * G
        
        # Update history for next step
        self.prev_omega = meas_speed_winder

        tension_estimate = self.tension_observer.update(
            tau_motor=torque_for_obs,
            omega=meas_speed_winder,
            alpha=alpha_est,
            R=meas_radius,
            v_upstream=v_unwinder_surface,
            v_downstream=v_process,
            J_total=est_inertia_total,
            tension_measured=meas_tension,
        )
        meas_tension = tension_estimate.tension
        
        # --- B. CONTROL (The "Brain") ---
        
        # 1. Torque Calculation Logic
        if self.config.control_mode == "SPEED_LIMIT":
            # Speed Loop with Torque Limit (Simulating PowerSys "Winder Control" if simple drive)
            # ... (Existing SPEED_LIMIT logic - omitted for brevity)
            
            # Target Winder Speed
            w_target_winder = speed_ref / meas_radius # rad/s
            
            # Under-speed reference (e.g. 95%) to force saturation against the pull
            w_ref_ctrl = w_target_winder * 0.95 
            
            # Motor Domain
            w_ref_motor = w_ref_ctrl * G
            w_meas_motor = meas_speed_winder * G
            
            # PI Controller
            error = w_ref_motor - w_meas_motor
            self.speed_integrator += error * dt
            
            Kp = self.config.speed_kp
            Ki = self.config.speed_ki
            
            torque_pi = Kp * error + Ki * self.speed_integrator
            
            t_tension_motor = (tension_ref * meas_radius) / G
            limit_braking = t_tension_motor 
            
            # Saturation
            if torque_pi > 0: torque_pi = 0 # Unwinder shouldn't drive forward usually?
            if torque_pi < -limit_braking: torque_pi = -limit_braking
            
            torque_cmd_total = torque_pi
        
        elif self.config.control_mode == "CLOSED_LOOP_TENSION":
            # Based on User's Diagram:
            # Winder Control Block Takes Feedback (Radius, Speed, TENSION).
            # Outputs Torque Ref.
            # This is likely Torque Control + Closed Loop Tension PID Correction.
            # T_cmd = T_ff + PID(T_tens_ref - T_tens_meas)
            
            # 1. Feedforward Terms (Open Loop Estimate)
            t_ff_tension = (tension_ref * meas_radius) / G
            
            # Friction Compensation
            t_fric = self.observer.update(meas_speed_winder, self.motor.current_torque*G, dt, est_inertia_total) / G
            
            # Inertia Compensation
            w_ref_winder = speed_ref / meas_radius
            accel_comp = 0.0
            # Simple Derivative
            if hasattr(self, 'prev_w_ref'):
                accel_comp = (w_ref_winder - self.prev_w_ref) / dt
            else:
                self.prev_w_ref = w_ref_winder
            self.prev_w_ref = w_ref_winder # Actually update it!
            
            t_iner = (est_inertia_total * accel_comp) / G

            # 2. Closed Loop Tension Component (PID)
            tension_error = tension_ref - meas_tension
            
            self.tension_integrator += tension_error * dt
            # Anti-windup clamping
            if self.tension_integrator > 10000: self.tension_integrator = 10000
            if self.tension_integrator < -10000: self.tension_integrator = -10000
            
            pid_output_force = (self.config.tension_kp * tension_error) + (self.config.tension_ki * self.tension_integrator)
            
            # Convert Force Correction to Torque Correction
            t_closed_loop = (pid_output_force * meas_radius) / G
            
            # Total Torque Command (Unwinder Braking = Negative)
            # T_net must oppose motion.
            # T_ff calculated as positive magnitude.
            # T_motor = - (T_ff + T_closed_loop) - T_fric + T_iner
            
            torque_cmd_total = -(t_ff_tension + t_closed_loop) - t_fric + t_iner
            
        else:
            # "OPEN_LOOP_TORQUE" (Legacy)
            # 1. Filter
            self.notch_filter.adapt(est_inertia_total, base_inertia=1.0, base_freq=20.0)
            
            # 2. Compute Command
            t_tens = (tension_ref * meas_radius) / G
            # Friction Compensation (Reflected to Motor)
            t_fric = self.observer.update(meas_speed_winder, self.motor.current_torque*G, dt, est_inertia_total) / G
            
            # Inertia Compensation: J * alpha_ref
            # Estimate alpha_ref from speed_ref derivative? 
            # Current code used proportional error: est_inertia * (speed_ref - meas_speed) * 10
            # Let's keep it but scale by G
            # (speed_ref line speed - speed_ref_winder?)
            # The previous code was: est_inertia * (speed_ref - meas_speed) * 10.0
            # speed_ref was entered as 10.0 (m/s) in test, but meas_speed is rad/s!
            # ERROR in Previous Code: Mixing m/s and rad/s?
            # In test: twin.step(speed_ref=ref_speed...) where ref_speed is m/s.
            # In step: (speed_ref - meas_speed). 10 - 100 rad/s = -90.
            # This was causing HUGE braking torque! 
            # Correction: Convert speed_ref (m/s) to rad/s for calculation.
            
            w_ref_winder = speed_ref / meas_radius
            accel_comp = (w_ref_winder - meas_speed_winder) * 10.0 # P-gain as fake accel
            t_iner = (est_inertia_total * accel_comp) / G
            
            # For Unwinder: Tension Pulls (+), Friction (-). Motor must Braking (-) to hold back?
            # Previous code: t_tens + t_fric + t_iner.
            # If t_tens is positive, motor HELPS unwinding?
            # UNWINDER CONVENTION:
            # If Material Pulls (Tension > 0), it accelerates unwinder.
            # Motor must apply NEGATIVE torque to resist.
            # So T_motor_ref should be NEGATIVE of Tension Load.
            
            torque_cmd_total = -t_tens - t_fric + t_iner
            
        self.motor.set_torque_command(torque_cmd_total)
        
        # --- C. ACTUATION & PLANT PHYSISCS (The "World") ---
        
        # 1. Motor Dynamics
        # Motor produces torque.
        torque_applied_motor = self.motor.update(dt, meas_speed_winder*G)
        
        # Torque at Winder Shaft
        torque_at_winder = torque_applied_motor * G
        
        # 2. Web Span Dynamics (Tension Calculation)
        # V_upstream = Unwinder Surface Speed (Negative if unwinding? Let's assume V > 0 means paying out)
        # Let's say Unwinder turns positive to payload.
        # V_downstream = Process Speed (The pull roll pulling the web) - Assumed perfectly regulated at speed_ref here
        v_unwinder_surface = self.unwinder.omega * self.unwinder.radius
        v_process = speed_ref # The master axis downstream (m/s)
        
        # Update Span (Calculate Tension based on speed diff)
        # In unwinding: Upstream is the Roll, Downstream is the Process.
        real_tension = self.web_span.update(v_upstream=v_unwinder_surface, v_downstream=v_process, dt=dt)
        
        # 3. Mechanical Dynamics (Winder Shaft)
        # Torque Balance: J*alpha = T_motor_shaft - T_friction + T_tension_load
        
        torque_friction = self.unwinder.get_friction_torque() # Computed on winder speed
        load_torque = real_tension * self.unwinder.radius # Pulls the roll (+)
        
        # Net Torque on Winder
        # Motor Torque (typically negative for unwinder braking)
        # Load Torque (Positive, pulling material out)
        # Friction (Negative, opposing rotation)
        
        net_torque = torque_at_winder + load_torque - torque_friction
        
        # Use TOTAL INERTIA (Motor + Roll) for dynamics?
        # Ideally simulation separates them if shaft is compliant, but here stiff shaft.
        # Winder.apply_dynamics uses self.core_inertia + material_inertia.
        # We need to add reflected motor inertia to the "physical plant" too.
        # But Winder class might not support external inertia addition easily without modifying it.
        # Workaround: Pass effective torque to Winder scaled by inertia ratio? 
        # Better: Update Winder Inertia to include Motor Reflected?
        # Let's assume Winder.apply_dynamics uses J_roll.
        # acceleration = net_torque / J_total
        
        J_roll = self.unwinder.get_total_inertia()
        J_total = J_roll + J_motor * (G**2)
        
        alpha = net_torque / J_total
        
        # Manually update state instead of calling apply_dynamics which divides by J_roll
        self.unwinder.omega += alpha * dt
        # self.unwinder.apply_dynamics(net_torque, dt) <--- skipping this to use correct J_total
        
        self.unwinder.update_geometric(dt)
        
        self.time += dt
        
        # Log
        self.history['time'].append(self.time)
        self.history['omega'].append(self.unwinder.omega)
        self.history['radius'].append(self.unwinder.radius)
        self.history['tension'].append(real_tension)
        self.history['tension_est'].append(tension_estimate.tension)
        self.history['tension_mode'].append(tension_estimate.mode)
        self.history['torque'].append(torque_applied_motor)


    def run(self):
        steps = int(self.config.duration / self.config.dt)
        for _ in range(steps):
            self.step(speed_ref=5.0, tension_ref=100.0)
        return self.history

if __name__ == "__main__":
    # Quick self-test
    sim = DigitalTwin(SystemConfig())
    results = sim.run()
    # Simplified print
    print(f"Simulation done. Final Radius: {results['radius'][-1]:.3f} m")

import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from prowinder.control.filters import AdaptiveNotchFilter

def run_filter_simulation():
    # 1. Simulation Parameters
    fs = 1000.0       # Sampling frequency (Hz)
    dt = 1.0 / fs
    duration = 3.0    # Seconds
    t = np.arange(0, duration, dt)
    n_samples = len(t)

    # 2. System Evolution (Simulating Unwinding)
    # Inertia decreases from J_max to J_min
    # f_resonance increases as sqrt(1/J)
    J_start = 10.0
    J_end = 2.0
    # Linear change in Inertia for simplicity of visualization
    inertia_profile = np.linspace(J_start, J_end, n_samples)
    
    # Theoretical Resonance Frequency: f ~ k / sqrt(J)
    # Let's say at J=10, f=20Hz. So k = 20 * sqrt(10) ≈ 63.2
    k_stiffness = 20.0 * np.sqrt(J_start)
    resonance_freqs = k_stiffness / np.sqrt(inertia_profile)

    # 3. Setup Filter
    # Initialize near the starting frequency
    initial_freq = resonance_freqs[0]
    notch_filter = AdaptiveNotchFilter(
        center_freq=initial_freq, 
        q_factor=30.0,  # Narrow notch
        sampling_rate=fs
    )

    # 4. Generate Signals
    # Base signal: A slow sine wave representing actual speed command
    base_speed = 5.0 * np.sin(2 * np.pi * 1.0 * t) 
    
    # Vibration: Sine wave at the CHANGING resonance frequency
    # We need to integrate phase because frequency is changing
    phase = np.cumsum(2 * np.pi * resonance_freqs * dt)
    vibration_noise = 0.5 * np.sin(phase) # 10% noise amplitude
    
    dirty_signal = base_speed + vibration_noise
    clean_signal_est = np.zeros_like(dirty_signal)
    filter_freq_log = np.zeros_like(dirty_signal)
    
    print("Starting Adaptive Notch Filter Simulation...")
    print(f"Simulating Resonance change: {resonance_freqs[0]:.1f}Hz -> {resonance_freqs[-1]:.1f}Hz")

    # 5. Runtime Loop
    for i in range(n_samples):
        # A. Measure current Inertia (in real life, from Radius calc)
        current_J = inertia_profile[i]
        
        # B. Adapt Filter
        # The filter needs a reference point. 
        # adapt(current_inertia, base_inertia, base_freq)
        # We tell it: "At J=10.0, the freq is 20.0Hz. Where is it now at J=current?"
        notch_filter.adapt(current_inertia=current_J, base_inertia=J_start, base_freq=20.0)
        
        # C. Process Filter
        clean_signal_est[i] = notch_filter.process(dirty_signal[i])
        
        # Log internal state
        filter_freq_log[i] = notch_filter.f0

    # 6. Visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Plot 1: Signals
    ax1.plot(t, dirty_signal, 'r-', alpha=0.3, label='Signal Bruité (Vibration Variable)')
    ax1.plot(t, base_speed, 'k--', linewidth=1, label='Vitesse Réelle (Cible)')
    ax1.plot(t, clean_signal_est, 'b-', linewidth=1.5, label='Sortie Filtre Adaptatif')
    ax1.set_ylabel('Amplitude')
    ax1.set_title('Filtrage de Résonance Variable (Déroulement)')
    ax1.legend(loc='upper right')
    ax1.grid(True)

    # Plot 2: Frequency Tracking
    ax2.plot(t, resonance_freqs, 'g--', linewidth=2, label='Fréquence Résonance Physique')
    ax2.plot(t, filter_freq_log, 'm-', linewidth=1.5, label='Fréquence Filtre (Tracking)')
    ax2.set_ylabel('Fréquence (Hz)')
    ax2.set_xlabel('Temps (s)')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    try:
        output_file = 'adaptive_filter_test.png'
        plt.savefig(output_file)
        print(f"Plot saved successfully to {output_file}")
    except Exception as e:
        print(f"Could not save plot: {e}")

if __name__ == "__main__":
    run_filter_simulation()

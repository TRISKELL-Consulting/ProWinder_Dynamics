import numpy as np
import matplotlib.pyplot as plt
from prowinder.mechanics.material import MaterialProperties, WebMaterial
from prowinder.mechanics.web_span import WebSpan, SpanProperties

def test_kelvin_voigt_step_response():
    """
    Validation IV.1 : Réponse Indicielle du Modèle de Bande (Calibration Kelvin-Voigt).
    On simule un échelon de vitesse aval (v_downstream) et on observe la tension.
    On compare avec/sans viscosité pour calibrer l'amortissement.
    """
    
    dti = 0.001
    duration = 2.0 # Increased duration to see steady state
    time = np.arange(0, duration, dti)
    
    # 1. Setup Material (PET Standard)
    # E = 4 GPa, Width = 1m, Thickness = 50um
    mat_hooke_prop = MaterialProperties("PET_Hooke", 1390.0, 4e9, 50e-6, 1.0, viscosity=0.0)
    # Viscosity calibration: 
    # With 5e7, we saw minimal difference. Let's try 5e8.
    viscosity_val = 1e8 
    mat_kv_prop = MaterialProperties("PET_KV", 1390.0, 4e9, 50e-6, 1.0, viscosity=viscosity_val) 
    
    span_props = SpanProperties(length=2.0, initial_tension=100.0)
    
    span_hooke = WebSpan(WebMaterial(mat_hooke_prop), span_props)
    span_kv = WebSpan(WebMaterial(mat_kv_prop), span_props)
    
    # Check variables
    section = mat_hooke_prop.young_modulus * mat_hooke_prop.thickness * mat_hooke_prop.width
    print(f"Stiffness K = E*S = {section/1000:.1f} kN")
    
    # 2. Simulation Loop
    v1 = 5.0 
    v2_base = 5.0
    v2_step = 5.05 # 1% stretch
    
    results_hooke = []
    results_kv = []
    
    for t in time:
        v2 = v2_base if t < 0.2 else v2_step
        
        # Note: If v1 is constant, strain_upstream is likely constant (assuming derived from v1 perfectly matching upstream speed)
        # In this simple test, we assume upstream strain corresponds to initial_tension (steady state)
        section_area = mat_hooke_prop.thickness * mat_hooke_prop.width
        strain_up = 100.0 / (mat_hooke_prop.young_modulus * section_area)
        
        # Important: WebSpan.update takes strain_upstream argument!
        # Default is 0.0 if not provided. This was a bug in previous test run (implicit 0)!
        # If strain_upstream is 0, the transport term tries to bring tension to 0.
        # But we started at 100N. So it decayed towards 0 + step?
        # Let's feed proper strain_upstream.
        
        t_h = span_hooke.update(v_upstream=v1, v_downstream=v2, dt=dti, strain_upstream=strain_up)
        t_k = span_kv.update(v_upstream=v1, v_downstream=v2, dt=dti, strain_upstream=strain_up)
        
        results_hooke.append(t_h)
        results_kv.append(t_k)
        
    # 3. Plotting
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(time, results_hooke, label='Hooke (eta=0)')
        plt.plot(time, results_kv, label=f'Kelvin-Voigt (eta={viscosity_val:.0e})', linestyle='--')
        plt.title('Validation: Step Response of Web Span (Viscosity Calibration)')
        plt.xlabel('Time (s)')
        plt.ylabel('Tension (N)')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('docs/validation_kelvin_voigt.png')
        print("Calibration Plot saved to docs/validation_kelvin_voigt.png")
    except Exception as e:
        print(f"Plotting failed: {e}")
    
    print(f"Final Tension Hooke: {results_hooke[-1]:.2f} N")
    print(f"Final Tension KV: {results_kv[-1]:.2f} N")
    
    eps_steady = strain_up + (v2_step/v1 - 1.0)
    tens_steady = (mat_hooke_prop.young_modulus * section_area) * eps_steady
    print(f"Theoretical Steady State: {tens_steady:.2f} N")

if __name__ == "__main__":
    test_kelvin_voigt_step_response()

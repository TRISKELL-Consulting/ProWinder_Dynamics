# Documentation Technique : Observateur de Friction et "Virtual Sensor"

## 1. Contexte et Problématique
Dans les systèmes d'enroulement haute performance, la phase la plus critique est le **démarrage à vitesse nulle** et l'inversion de sens.
Les contrôleurs traditionnels (PID) échouent souvent ici car :
1.  Les capteurs de vitesse ont une résolution limitée à très basse vitesse.
2.  Le frottement statique (**Stiction**) est non-linéaire et discontinu.
3.  Sans capteur de force (Load Cell), la tension de bande n'est pas mesurable à l'arrêt ($Couple = J\dot{\omega} + Frottement + Tension$). Si $\dot{\omega}=0$, on ne sait pas distinguer le couple de tension du couple de frottement.

L'**Observateur de Friction** (Friction Observer) résout ce problème en estimant mathématiquement le couple de frottement inhérent à la mécanique pour l'"isoler" et permettre un contrôle pur de la tension.

---

## 2. Modèle Mathématique de Frottement (Stribeck)
L'algorithme repose sur le modèle de Stribeck complet, implémenté dans `src/prowinder/mechanics/friction.py`.

$$
T_{f}(\omega) = \underbrace{T_c \cdot \text{sgn}(\omega)}_{\text{Coulomb}} + \underbrace{K_v \cdot \omega}_{\text{Visqueux}} + \underbrace{(T_s - T_c) \cdot e^{-(\omega/\omega_s)^2}}_{\text{Stribeck (Stiction)}}
$$

Où :
*   $T_c$ : Couple de frottement de Coulomb (constant en mouvement).
*   $K_v$ : Coefficient visqueux (proportionnel à la vitesse).
*   $T_s$ : Couple de frottement statique (pic au démarrage).
*   $\omega_s$ : Vitesse de Stribeck (constante de temps du décrochage).

---

## 3. Algorithme de l'Observateur
Implémenté dans `src/prowinder/control/observers.py`.

C'est un observateur d'état de type **Luenberger** simplifié, qui utilise l'erreur entre la vitesse prédite et la vitesse mesurée pour corriger l'estimation du couple perturbateur (le frottement).

### Équations de Mise à Jour
1.  **Prédiction Vitesse** : On utilise le modèle physique de Newton.
    $$ \hat{\omega}_{k+1} = \hat{\omega}_k + \frac{dt}{J} (T_{moteur} - \hat{T}_{friction}) $$
2.  **Calcul de l'Erreur** :
    $$ \epsilon = \omega_{mesurée} - \hat{\omega}_{k+1} $$
3.  **Correction (Innovation)** :
    $$ \hat{T}_{friction} \leftarrow \hat{T}_{friction} - L \cdot J \cdot \epsilon $$
    *   $L$ est le gain de l'observateur. Plus il est élevé, plus la convergence est rapide, mais plus il est sensible au bruit.

---

## 4. Résultats de Simulation et Validation
Le script de test `tests/test_observer_scenario.py` valide le comportement sur un cycle : Démarrage $\rightarrow$ Vitesse stable $\rightarrow$ Inversion.

### Interprétation des tests
*   **Zone critique** : Au passage par zéro (t=1.4s), l'observateur parvient à tracker le saut brutal du couple de frottement (changement de signe).
*   **Stabilité** : L'estimation converge en moins de 50ms, ce qui est suffisant pour empêcher le mou de bande au démarrage.

---

## 5. Utilisation dans le Projet
```python
from prowinder.control.observers import FrictionObserver

# Initialisation
observer = FrictionObserver(model, gain=50.0)

# Dans la boucle temps réel (PLC ou Python)
friction_torque = observer.update(
    measured_velocity=current_speed,
    applied_torque=current_torque_command,
    dt=sample_time,
    inertia=current_estimated_inertia
)

# Compensation dans la commande moteur
torque_command = tension_torque + inertia_comp + friction_torque
```

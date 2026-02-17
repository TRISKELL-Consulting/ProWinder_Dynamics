# Documentation Technique : Filtre Anti-Vibration (Adaptive Notch Filter)

## 1. Contexte et Problématique
Dans le bobinage de films minces ou de batteries, une problématique majeure est l'apparition de **vibrations** (ondes stationnaires) dans la bande.
Ces vibrations sont souvent causées par la résonance mécanique de la bobine elle-même.

**Le Défi** : La fréquence de résonance n'est pas fixe.
Elle change en permanence car le diamètre de la bobine change.
*   Bobine pleine (Inertie max $J_{max}$) $\rightarrow$ Fréquence basse.
*   Bobine vide (Inertie min $J_{min}$) $\rightarrow$ Fréquence haute.

Un filtre fixe est donc inutile (il filtrerait la mauvaise fréquence 90% du temps). Il faut un filtre qui "bouge" avec la bobine.

---

## 2. Physique du Problème
La fréquence de résonance $f_{res}$ d'un système masse-ressort rotatif est liée à la raideur $K$ (élasticité de la bande) et à l'inertie $J$ (bobine).

$$ f_{res} \approx \frac{1}{2\pi} \sqrt{\frac{K}{J}} $$

Comme l'inertie $J$ varie en fonction du rayon $R$ ($J \propto R^4$), la fréquence varie selon :

$$ f_{res}(R) \propto \frac{1}{R^2} $$

Cette relation hyperbolique est la clé de notre stratégie de contrôle.

---

## 3. Algorithme : Adaptive Notch Filter
Implémenté dans `src/prowinder/control/filters.py`.

Nous utilisons un filtre coupe-bande (Notch Filter) numérique de type IIR (Infinite Impulse Response) dont les coefficients sont recalculés en temps réel.

### Fonctionnement (Gain Scheduling)
L'algorithme ne cherche pas à détecter la fréquence (ce qui est lent et instable), mais la **calcule** a priori grâce au modèle physique connue de la machine.

1.  **Entrée** : Inertie actuelle ($J_{est}$) fournie par le `RadiusCalculator`.
2.  **Loi de Variation** :
    $$ f_{center} = f_{base} \cdot \sqrt{\frac{J_{base}}{J_{est}}} $$
3.  **Mise à jour des Coefficients** : À chaque cycle (ou changement significatif), les coefficients $a_i, b_i$ du filtre sont mis à jour pour centrer le "trou" du filtre sur $f_{center}$.

---

## 4. Résultats de Simulation
Le script `tests/test_filter_scenario.py` simule une phase de déroulement (Inertie $10 \to 2$ kg.m²).

*   **Fréquence Réelle** : Passe de 20 Hz à ~45 Hz.
*   **Tracking** : Le filtre suit parfaitement cette évolution (courbe Magenta sur courbe Verte).
*   **Efficacité** : Le signal de vitesse (Bruité) est nettoyé (Bleu) sans introduire de déphasage sur la commande principale (basse fréquence).

---

## 5. Intégration dans ProWinder
Ce filtre doit être placé sur le retour de vitesse ou sur la commande de couple, juste avant le régulateur PID.

```python
from prowinder.control.filters import AdaptiveNotchFilter

# Initialisation
notch = AdaptiveNotchFilter(center_freq=20.0, q_factor=30.0, sampling_rate=1000)

# Dans la boucle de régulation
# 1. Mise à jour de la fréquence cible basée sur l'inertie
notch.adapt(current_inertia=J_total, base_inertia=J_max, base_freq=20.0)

# 2. Filtrage du signal
clean_velocity = notch.process(noisy_velocity_measurement)
```

### Avantages Stratégiques
*   **Stabilité** : Permet d'augmenter les gains du PID sans risquer d'osciller sur la fréquence propre.
*   **Qualité** : Réduit les micro-variations de tension sur le produit fini.

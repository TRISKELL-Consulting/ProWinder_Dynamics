# ProWinder Dynamics

## Structure du Projet

Ce projet utilise une architecture modulaire standard pour séparer la physique (Plant), le contrôle (Controller) et la simulation.

### Organisation des dossiers

* `src/winding_lib/` : Code source principal (package Python).
    * `models/` : Modèles physiques (Moteurs, Mécanique, Bande).
    * `control/` : Algorithmes de contrôle (PID, Observateurs, Stratégies).
    * `simulation/` : Moteur de simulation et scénarios.
    * `utils/` : Utilitaires mathématiques et physiques.
* `tests/` : Tests unitaires et d'intégration (pytest).
* `notebooks/` : Analyses exploratoires et visualisation (Jupyter).
* `config/` : Fichiers de configuration (paramètres machines).
* `docs/` : Documentation.

## Installation

```bash
pip install -e .
```

## Utilisation

Voir le dossier `notebooks/` pour des exemples de simulation.

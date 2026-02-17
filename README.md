# ProWinder Dynamics 🎯

**Système de contrôle avancé pour enrouleurs/dérouleurs industriels**

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-15%2F15-brightgreen.svg)](tests/)
[![Phase](https://img.shields.io/badge/Phase-2%20(40%25)-yellow.svg)](docs/strategy/PROJECT_ROADMAP.md)

---

## 🚀 Démarrage Rapide

### Installation

```bash
# Clone du projet
git clone https://github.com/TRISKELL-Consulting/ProWinder_Dynamics.git
cd ProWinder_Dynamics

# Installation en mode développement
pip install -e .

# Exécution des tests
pytest tests/ -v
```

### Premier Test

```python
from prowinder.control.radius_estimator import RadiusCalculator

# Créer un estimateur de rayon
calc = RadiusCalculator(
    R0=0.05,              # Mandrin 50mm
    film_thickness=50e-6, # Film 50µm
    roller_length=1.0     # Rouleau 1m
)

# Estimer le rayon
result = calc.estimate(
    v_linear=60.0,    # 60 m/min
    omega=10.0,       # 10 rad/s
    film_thickness_measured=50e-6,
    dt=0.01
)

print(f"Rayon: {result.radius*1000:.1f} mm")
print(f"Mode: {result.mode}")
print(f"Confiance: {result.confidence:.2%}")
```

---

## 📁 Structure du Projet

```
ProWinder_Dynamics/
├── src/prowinder/              # Package principal
│   ├── control/                # Algorithmes de contrôle
│   │   ├── filters.py          # Filtres adaptatifs
│   │   ├── observers.py        # Observateurs d'état
│   │   └── radius_estimator.py # ✅ Estimateur de rayon (T2.1.1)
│   ├── mechanics/              # Modèles mécaniques
│   │   ├── dynamics.py         # Dynamique système
│   │   ├── friction.py         # Modèles de friction
│   │   ├── roller.py           # Modèle rouleau
│   │   └── web_span.py         # Modèle bande (Kelvin-Voigt)
│   └── simulation/             # Moteur de simulation
│
├── tests/                      # Tests unitaires (pytest)
│   ├── test_radius_calculator.py  # ✅ 15/15 tests validés
│   ├── test_digital_twin_full.py
│   └── test_validation_*.py
│
├── scripts/                    # Scripts utilitaires
│   ├── validation/             # Scripts de validation
│   │   └── validate_T2.1.1.py  # Validation roadmap T2.1.1
│   └── activate_venv.ps1
│
├── docs/                       # Documentation
│   ├── strategy/               # 📊 Documents stratégiques
│   │   ├── INDEX_STRATEGIE.md      # Navigation centrale
│   │   ├── EXECUTIVE_SUMMARY.md    # Résumé exécutif
│   │   └── PROJECT_ROADMAP.md      # Feuille de route détaillée
│   ├── algorithms/             # Documentation algorithmes
│   │   └── RadiusCalculator.md     # ✅ Doc complète T2.1.1
│   ├── technical/              # Spécifications techniques
│   │   ├── Digital_Twin_Architecture.md
│   │   ├── Friction_Observer_Algo.md
│   │   └── Web_Model_Validation.md
│   ├── bibliography/           # Bibliographie & recherche
│   └── validation/             # Rapports de validation
│
├── notebooks/                  # Analyses Jupyter
├── config/                     # Configurations
└── 01-06_*/                    # Dossiers méthodologiques

```

---

## 📚 Documentation

### 🎯 Pour les Décideurs (5 min)
👉 **[Résumé Exécutif](docs/strategy/EXECUTIVE_SUMMARY.md)**
- Vision projet et positionnement marché
- ROI et business case
- Comparaison concurrents (ABB, Siemens, Lenze)

### 🗺️ Pour les Chefs de Projet (1-2h)
👉 **[Roadmap Projet](docs/strategy/PROJECT_ROADMAP.md)**
- Planning détaillé 4 phases
- Tâches et dépendances
- Jalons et livrables

### 🔧 Pour les Développeurs
👉 **[Index Stratégie](docs/strategy/INDEX_STRATEGIE.md)** (navigation centrale)
👉 **[Documentation Algorithmes](docs/algorithms/)** (spécifications techniques)
👉 **[Documentation Technique](docs/technical/)** (architecture digitale twin)

### 📖 Pour les Chercheurs
👉 **[Bibliographie](docs/bibliography/)** (état de l'art industriel)

---

## 🎮 Fonctionnalités Implémentées

### ✅ Phase 1: Digital Twin & Modélisation (100%)

- **Modèles Physiques**
  - ✅ Friction (Coulomb + Stribeck + Viscous)
  - ✅ Dynamique enrouleur variable (J(R), inertie)
  - ✅ Web span (Kelvin-Voigt viscoélastique)
  
- **Observateurs d'État**
  - ✅ Friction Observer
  - ✅ Web Tension Estimator

### 🔄 Phase 2: Algorithmes de Contrôle (40%)

- **Estimateurs** (T2.1)
  - ✅ **RadiusCalculator** (T2.1.1) - Fusion hybride vitesse/intégration
    - Précision: 0.997% (< 2% requis)
    - Latence: 0.052 ms (< 100 ms requis)
  - ⏳ Auto-Identifier Inertie (T2.1.2)
  - ⏳ Sensorless Tension @ V=0 (T2.1.3)

- **Contrôleurs** (T2.2)
  - ⏳ InertiaCompensator (feedforward)
  - ⏳ DancerController (boucle position)
  - ⏳ TorqueController (couple/tension)
  - ⏳ Architecture SISO/MIMO hybride

- **Filtres** (T2.3)
  - ⏳ Adaptive Notch Filter
  - ⏳ Anti-Vibration Soft-Winding

### ⏹️ Phase 3: Validation & Code Generation (0%)

- ⏳ Scénarios critiques testés
- ⏳ Code embarqué généré
- ⏳ Documentation utilisateur

### ⏹️ Phase 4: Déploiement Industriel (0%)

- ⏳ API Standardisée
- ⏳ PLC Integration
- ⏳ Support clients

---

## 🧪 Tests & Validation

```bash
# Tous les tests
pytest tests/ -v

# Test spécifique RadiusCalculator
pytest tests/test_radius_calculator.py -v

# Validation roadmap T2.1.1
python scripts/validation/validate_T2.1.1.py
```

**Couverture actuelle:**
- ✅ 15/15 tests RadiusCalculator
- ✅ Digital Twin complet validé
- ✅ Observateurs friction testés

---

## 🛠️ Technologies

- **Python 3.13+** (langage principal)
- **NumPy / SciPy** (calcul scientifique)
- **Pytest** (tests unitaires)
- **Jupyter** (analyses exploratoires)
- **Git / GitHub** (versioning)

---

## 📊 Progression Projet

```
PHASE 1: Digital Twin & Modélisation
|--------[████████████] ✅ COMPLÉTÉE (100%)

PHASE 2: Algorithmes de Contrôle
|--------[█████░░░░░░░] 🔄 EN COURS (40%)
         └─ T2.1.1 RadiusCalculator ✅

PHASE 3: Validation & Code Generation  
|--------[░░░░░░░░░░░░] ⏹️ À FAIRE (0%)

PHASE 4: Déploiement Industriel
|--------[░░░░░░░░░░░░] ⏹️ À FAIRE (0%)
```

**Prochaine étape:** T2.1.2 Auto-Identifier Inertie

---

## 🤝 Contribution

Projet interne TRISKELL Consulting - R&D ProWinder Dynamics

**Contact:** Équipe R&D  
**Licence:** Internal Use Only  
**Classification:** Technique Propriétaire

---

## 📈 Performances Clés

| Algorithme | Critère | Requis | Mesuré | Statut |
|------------|---------|--------|--------|--------|
| **RadiusCalculator** | Précision | < 2% | **0.997%** | ✅ |
| **RadiusCalculator** | Latence | < 100ms | **0.052ms** | ✅ |
| FrictionObserver | Erreur | < 5% | **2.1%** | ✅ |
| WebSpanModel | Convergence | < 1s | **0.3s** | ✅ |

---

**Version:** 1.0.0-alpha  
**Dernière mise à jour:** 17 Février 2026

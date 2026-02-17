# Rapport d'Étude Bibliographique et Feuille de Route R&D

**Projet :** ProWinder Dynamics  
**Date :** 16 Février 2026  
**Objet :** Synthèse de l'état de l'art académique et industriel, définition de la stratégie technique et roadmap du projet.

---

## 1. Introduction et Contexte

Ce document synthétise l'analyse approfondie du corpus documentaire du projet (`01_Requirements/Bibliography`), couvrant la recherche académique, les standards des leaders du marché (ABB, Lenze, Rockwell, Siemens) et l'existant interne (Schneider Electric / STIE).

L'objectif est de définir l'architecture technologique optimale pour **ProWinder**, une solution de contrôle d'enroulement/déroulement haute performance, capable de rivaliser avec les meilleurs standards actuels tout en répondant aux problématiques de robustesse identifiées chez les clients finaux (Sylvamo).

---

## 2. État de l'Art Académique (Recherche & Théorie)

L'analyse des publications scientifiques (Dossiers `General` & `ScienceDirect`) révèle que l'enroulement est un problème "Système Complexe" typique.

### A. Verrous Technologiques Identifiés & Analyse de Risques
L'analyse approfondie a mis en évidence deux points critiques souvent sous-estimés par les approches standards :

1.  **Stiction au Démarrage (Zero-Speed Control)** :
    *   *Problème* : À vitesse nulle ou très basse, le frottement statique (Stiction) est non-linéaire et discontinu. Les modèles classiques échouent à prédire le couple nécessaire pour initier le mouvement sans à-coup de tension.
    *   *Impact* : Risque de rupture ou de perte de tension (mou de bande) au démarrage.
    *   *Solution Requise* : Modèle de Stribeck + Observateur de Friction.

2.  **Résonance Mécanique (Vibration)** :
    *   *Problème* : La fréquence propre du système varie avec le rayon de la bobine ($f_{res} \propto 1/\sqrt{J(R)}$). Une vitesse critique peut exciter cette fréquence.
    *   *Impact* : Ondes stationnaires dans la bande, qualité d'enroulement dégradée.
    *   *Solution Requise* : Filtres Notch Adaptatifs (Gain Scheduling sur la fréquence).

3.  **Couplage Fort (MIMO)** :
    *   La vitesse linéaire ($v$) et la tension de bande ($T$) sont interdépendantes. Une variation de vitesse provoque immédiatement une variation de tension ($\dot{T} \propto \Delta v$). Les contrôleurs découplés simples (SISO) atteignent leurs limites sur les matériaux fragiles.
*   **Non-Linéarités Critiques** :
    *   **Inertie Variable** : $J(t) \propto R(t)^4$. L'inertie peut varier d'un facteur 1 à 100 entre le début et la fin de l'enroulement.
    *   **Rayon Variable** : Le gain du système change continuellement ($Couple = T \times R$).
*   **Dynamique des Matériaux** : La loi de Hooke est insuffisante pour les films polymères ou composites (batteries Li-Ion). Les modèles visco-élastiques (Kelvin-Voigt) sont nécessaires pour prédire le comportement réel.

### B. Stratégies de Commande Avancées
1.  **Robust Control ($H_\infty$)** : Préféré dans la recherche pour garantir la stabilité malgré les incertitudes paramétriques (masse volumique variable, frottements mal connus).
2.  **Sliding Mode Control (SMC)** : Très efficace pour rejeter les perturbations brutales (coups de couple), mais peut générer du "chattering" (vibrations) s'il est mal réglé.
3.  **Gain Scheduling (Adaptatif)** : La méthode "Reine" en industrie. On adapte les gains du PID en temps réel en fonction du rayon ($K_p(R)$).

---

## 3. Benchmark Industriel (Les "Gold Standards")

L'analyse des solutions concurrentes a permis d'extraire les "Best Practices" à intégrer dans ProWinder.

| Constructeur | Philosophie Technique | Points Forts à Intégrer ("Must Have") |
| :--- | :--- | :--- |
| **ABB** | **Performance Couple (DTC)** | • **Indirect Tension Control** : Régulation de tension sans capteur de force (Load Cell) grâce à une commande de couple ultra-rapide.<br>• **Taper Tension** : Profils hyperboliques pour gérer la dureté de la bobine. |
| **Lenze** | **Flexibilité Modulaire** | • **Architecture "FAST"** : Séparation stricte des classes `DancerMode` (Position) et `TorqueMode` (Couple).<br>• **Auto-Tuning** : Fonctions d'identification automatique des temps de réponse. |
| **Rockwell** | **Approche Mécatronique** | • **Feedforward Dominant** : Le couple est calculé par la physique ($J\dot{\omega} + F_{frot} + T_{tens}$), le PID ne corrige que l'erreur. C'est la clé de la stabilité.<br>• **Sécurité** : Détection de rupture de bande (Slack Web) intégrée. |
| **Siemens** | **Motion Control (Sync)** | • **Gear Ratio Variable** : L'enrouleur est un axe esclave synchronisé avec un ratio $1/R(t)$.<br>• **Filtres Adaptatifs** : Filtres réjecteurs qui suivent la fréquence de résonance mécanique ($f \propto 1/\sqrt{J}$). |

---

## 4. Analyse de l'Existant Interne (SE / STIE)

*   **L'Existant (Legacy)** : Solution fonctionnelle mais limitée en dynamique (architecture automate classique avec latences).
*   **Le Besoin (Sylvamo/Meetings)** : 
    *   Passer à une approche **Model-Based Design (MBD)** pour valider les performances avant mise en service.
    *   Réduire la complexité de mise en œuvre (tendance "Sensorless" pour réduire les coûts).
    *   Besoin de robustesse face aux variations de matériaux (Best-in-class performance).

---

## 5. Stratégie Technique ProWinder

Sur la base de cette étude, ProWinder adoptera l'architecture hybride suivante :

### A. Architecture de Contrôle : "Physics-Based Feedforward"
Plutôt qu'un simple PID, nous utiliserons une structure à 3 étages :
1.  **Feedforward Physique (80% du couple)** :
    *   Compensation d'Inertie dynamique ($J(R) \cdot \alpha$).
    *   Compensation de Friction (Modèle de Stribeck complet pour gérer la Stiction).
    *   Couple de Tension théorique ($F \cdot R$).
2.  **PID Adaptatif (20% restant)** :
    *   Gains $K_p, K_i$ adaptés en continu selon le rayon $R$.
3.  **Observateurs et Filtres Avancés** :
    *   **Friction Observer** : Estime le couple de frottement réel pour corriger le modèle théorique (essentiel pour le "Virtual Sensor").
    *   **Adaptive Notch Filter** : Filtre suiveur qui élimine les fréquences de résonance variables ($f(J)$) pour stabiliser la boucle de vitesse.

### B. Modèles Mathématiques Critiques à Implémenter
1.  **Estimateur de Rayon Hybride** : Fusion du calcul vitesse ($v/\omega$) et de l'intégration épaisseur ($R_0 + \Sigma e$) avec logique de basculement.
2.  **Modèle de Bande Élastique** : $\frac{dT}{dt} = \frac{E \cdot S}{L} (v_{aval} - v_{amont}) + \frac{v_{amont}}{L} (T_{amont} - T)$.
3.  **Inertie Totale Variable** : $J_{tot} = J_{moteur} + J_{rouleau} + \frac{\pi \rho L}{2} (R^4 - R_{mandrin}^4)$.

---

## 6. Feuille de Route du Projet (Roadmap R&D)

Cette roadmap est mise à jour pour refléter l'approche Model-Based Design.

### Phase 1 : Digital Twin & Modélisation (Mois 1-2)
*   **Objectif** : Disposer d'un banc d'essai virtuel fiable incluant les phénomènes critiques.
*   **Tâches** :
    *   [x] Création structure projet Python (`src/prowinder/`).
    *   [x] Implémentation Modèles de Friction (`src/prowinder/mechanics/friction.py`).
    *   [x] Implémentation Observateurs (`src/prowinder/control/observers.py`).
    *   [x] Calibration du modèle de bande élastique (Kelvin-Voigt) (`docs/technical/Web_Model_Validation.md`).
    *   [x] Validation du comportement en boucle ouverte (réponse indicielle).

### Phase 2 : Développement des Algorithmes de Contrôle (Mois 2-3)
*   **Objectif** : Dépasser les performances standards.
*   **Tâches** :
    *   [ ] Implémenter `RadiusCalculator` (algorithme robuste).
    *   [ ] Développer `InertiaCompensator` (Feedforward).
    *   [ ] Créer l'architecture de contrôle modulaire (`DancerController`, `TorqueController`).
    *   [ ] Tuner les correcteurs via simulation (Ziegler-Nichols auto-ajusté).

### Phase 3 : Validation & Code Generation (Mois 4)
*   **Objectif** : Préparer le déploiement industriel.
*   **Tâches** :
    *   [ ] Simuler les scénarios critiques (Arrêt d'urgence, Rupture bande, Changement bobine).
    *   [ ] Traduire les algorithmes Python validés en Structured Text (ST) pour Control Expert.
    *   [ ] Rédiger la documentation technique finale.

---

## 7. Opportunités d'Innovation et Brevets

Trois axes d'innovation ont été identifiés pour protéger la propriété intellectuelle :

1.  **"Virtual Sensor Tension Control"** : Méthode d'estimation de la tension à vitesse nulle utilisant un observateur de friction avancé (résout le problème classique des sensorless au démarrage).
2.  **"Auto-Adaptive Inertia ID"** : Séquence d'identification automatique de l'inertie et de la friction sans déconnecter la charge.
3.  **"Anti-Vibration Soft-Winding"** : Algorithme de modulation de vitesse pour casser les ondes stationnaires sur les films ultra-fins (inspiré de l'acoustique).

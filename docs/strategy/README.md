# 📋 Strategy & Roadmap

Documents stratégiques, feuilles de route et plans d'exécution du projet ProWinder Dynamics.

## 📚 Contenu

### [INDEX_STRATEGIE.md](./INDEX_STRATEGIE.md) - Navigation Centrale
Guide de navigation et index de tous les documents stratégiques.
- Hiérarchie documentaire
- Sélection par profil (CEO, PM, Dev, etc.)
- FAQ documentaire
- **À lire en premier!**

### [EXECUTIVE_SUMMARY.md](./EXECUTIVE_SUMMARY.md) - Résumé Exécutif (5 min)
Vue d'ensemble pour décideurs et comités.
- Positionnement marché et business case
- Tableau de bord d'avancement
- Risques et opportunités
- Business impact et ROI

### [PROJECT_ROADMAP.md](./PROJECT_ROADMAP.md) - Feuille de Route Détaillée
Guide d'exécution complet du projet (5 mois).
- 4 Phases: Digital Twin → Déploiement
- Tâches granulaires avec estimations
- Jalons clés et critères d'acceptation
- Ressources, budget, gouvernance

---

## 🎯 Accès Rapide par Profil

| Profil | À Lire | Temps |
|--------|--------|-------|
| **PDG / Direction** | EXECUTIVE_SUMMARY.md | 5 min |
| **Steering Committee** | EXECUTIVE_SUMMARY.md + PROJECT_ROADMAP.md p.1-3 | 15 min |
| **Project Manager** | PROJECT_ROADMAP.md (complet) | 1-2 h |
| **Technical Lead** | PROJECT_ROADMAP.md Phase 2-4 + `../bibliography/` | 2 h |
| **Développeurs** | PROJECT_ROADMAP.md tâche spécifique + `../technical/` | Variable |

---

## 🗂️ Accès Depuis Racine

Pour accéder à ces documents depuis la racine du projet:
```bash
# Depuis la racine
cat docs/strategy/EXECUTIVE_SUMMARY.md
cat docs/strategy/PROJECT_ROADMAP.md
cat docs/strategy/INDEX_STRATEGIE.md

# Ou directement
cd docs/strategy
ls -lh
```

---

## 📊 Structure Globale docs/

```
docs/
├── strategy/                    ← Vous êtes ici
│   ├── INDEX_STRATEGIE.md
│   ├── EXECUTIVE_SUMMARY.md
│   ├── PROJECT_ROADMAP.md
│   └── README.md (ce fichier)
│
├── bibliography/                ← Études & références
│   ├── general/
│   ├── suppliers/
│   └── patents/
│
├── technical/                   ← Spécifications techniques
│   ├── Digital_Twin_Architecture.md
│   ├── Web_Model_Validation.md
│   └── [autre].md
│
├── validation/                  ← Résultats tests
│   ├── validation_report.md
│   └── [*.png graphs]
│
└── README.md                    ← Index principal docs/
```

---

**Dernière mise à jour:** 17 Février 2026

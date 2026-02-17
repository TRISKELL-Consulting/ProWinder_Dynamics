# Scripts de Validation Roadmap

Ce dossier contient les scripts de validation des tâches de la roadmap du projet.

## Scripts Disponibles

### validate_T2.1.1.py

**Tâche:** T2.1.1 - RadiusCalculator (Robuste)  
**Status:** ✅ Validé

Script de validation automatique des critères roadmap pour le RadiusCalculator.

**Critères validés:**
- ✅ Précision < 2% (mesuré: 0.997%)
- ✅ Latence < 100 ms (mesuré: 0.052 ms)
- ✅ Latence moyenne < 10 ms (mesuré: 0.015 ms)
- ✅ Robustesse sur plage paramètres complète

**Utilisation:**

```bash
cd ProWinder_Dynamics
python scripts/validation/validate_T2.1.1.py
```

**Sortie attendue:**

```
======================================================================
VALIDATION ROADMAP T2.1.1: RadiusCalculator
======================================================================

[TEST 1] Précision < 2%
----------------------------------------------------------------------
✅ VALIDÉ - Erreur 0.997% < 2%

[TEST 2] Latence < 100 ms (appel unique)
----------------------------------------------------------------------
✅ VALIDÉ - Latence 0.052 ms < 100 ms

...

🎉 TÂCHE T2.1.1 (RadiusCalculator) VALIDÉE
======================================================================
```

---

## Organisation

Les scripts de validation sont organisés par tâche roadmap:

- `validate_T2.1.1.py` → Tâche T2.1.1 (RadiusCalculator)
- `validate_T2.1.2.py` → Tâche T2.1.2 (Auto-Identifier Inertie) [À créer]
- `validate_T2.1.3.py` → Tâche T2.1.3 (Sensorless Tension) [À créer]
- ...

## Conventions

Chaque script de validation doit:

1. **Importer le module testé** depuis `src/prowinder/`
2. **Tester tous les critères** définis dans la roadmap
3. **Afficher résultats clairs** avec statut ✅/❌
4. **Retourner code exit 0** si validé, 1 sinon
5. **Documenter les mesures** obtenues vs requis

## Lien avec Tests Unitaires

Les scripts de validation **complètent** les tests unitaires (`tests/`):

- **Tests unitaires** (pytest): Vérifications détaillées, edge cases, couverture
- **Scripts validation**: Vérification critères roadmap, benchmarks, validation formelle

Les deux doivent passer pour considérer une tâche comme ✅ complétée.

---

**Voir aussi:**
- [Roadmap Projet](../../docs/strategy/PROJECT_ROADMAP.md)
- [Tests Unitaires](../../tests/)

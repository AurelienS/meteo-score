# Feedback & Observations

Notes rapides capturées pendant le dev - à traiter en rétro BMAD.

---

## Sprint Actuel

### Dev Notes

#### Page About/Methodology
- [x] URL incohérente : `/about` devrait être `/methodology` (ou inverse) ✅ Story 6-1
- [x] Liens GitHub cassés : pointent vers `my-org/...` au lieu de `https://github.com/AurelienS/meteo-score` ✅ Story 6-1
- [x] Vérifier tous les liens externes de la page ✅ Story 6-1

#### Futures évolutions (tech debt / features)

**Theming (Light/Dark mode)**
- [x] Implémenter un système de thème light/dark ✅ Story 6-2
- Doit être bien architecturé : refonte UI possible plus tard mais theming restera
- Prévoir une abstraction propre (CSS variables, theme provider, etc.)

**Internationalisation (i18n)**
- [x] Mettre en place i18n sur l'app ✅ Story 6-3
- Langues initiales : FR + EN
- Anticiper l'ajout de langues futures
- Note : EN = "Meteo Score" (sans accent), FR = "Météo Score"

**Typographie**
- [ ] Revoir les fonts Geist - rendu actuel pas top (Story 6-4 backlog)
- Vérifier si c'est un problème de chargement ou de config
- Éventuellement tester d'autres alternatives

**Animations UI**
- [ ] Ajouter des micro-animations (Story 6-5 backlog)
- Style : léger mais moderne/classe
- Transitions subtiles, hover states, loading states
- Éviter le "too much" - rester épuré

---

## Bugs à Corriger

### BUG-001: Forecast Collection Broken - Wrong Parameter Names

**Date:** 2026-01-17
**Severity:** Critical
**Status:** ✅ Fixed (2026-01-17)

**Symptom:**
```
MeteoParapente collection failed for Passy Plaine Joux: MeteoParapenteCollector.collect_forecast() got an unexpected keyword argument 'forecast_time'
MeteoParapente collection failed for Semnoz: MeteoParapenteCollector.collect_forecast() got an unexpected keyword argument 'forecast_time'
AROME collection failed for Passy Plaine Joux: AROMECollector.collect_forecast() got an unexpected keyword argument 'forecast_time'
AROME collection failed for Semnoz: AROMECollector.collect_forecast() got an unexpected keyword argument 'forecast_time'
```

**Root Cause:**
Parameter mismatch in `backend/scheduler/jobs.py` when calling collectors.

**Details:**

1. **Wrong parameter name:** Jobs use `forecast_time` but collectors expect `forecast_run`
2. **Missing required parameters:** `latitude` and `longitude` are not passed (available in site config)

**Affected Files:**
- `backend/scheduler/jobs.py:134-137` (MeteoParapente call)
- `backend/scheduler/jobs.py:159-162` (AROME call)

**Current Code (BROKEN):**
```python
data = await mp_collector.collect_forecast(
    site_id=site["site_id"],
    forecast_time=forecast_time,  # WRONG
)
```

**Expected Code (FIX):**
```python
data = await mp_collector.collect_forecast(
    site_id=site["site_id"],
    forecast_run=forecast_time,  # Correct param name
    latitude=site["latitude"],   # Missing - required
    longitude=site["longitude"], # Missing - required
)
```

**Testing Required:**
- [x] Fix parameter names in jobs.py ✅
- [x] Add latitude/longitude from site config ✅
- [ ] Run manual forecast collection test via admin API
- [ ] Verify data is being collected in database
- [ ] Run existing unit tests for collectors


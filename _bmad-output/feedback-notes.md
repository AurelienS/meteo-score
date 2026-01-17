# Feedback & Observations

Notes rapides capturées pendant le dev - à traiter en rétro BMAD.

---

## Sprint Actuel

### Dev Notes

#### Page About/Methodology
- [ ] URL incohérente : `/about` devrait être `/methodology` (ou inverse)
- [ ] Liens GitHub cassés : pointent vers `my-org/...` au lieu de `https://github.com/AurelienS/meteo-score`
- [ ] Vérifier tous les liens externes de la page

#### Futures évolutions (tech debt / features)

**Theming (Light/Dark mode)**
- [ ] Implémenter un système de thème light/dark
- Doit être bien architecturé : refonte UI possible plus tard mais theming restera
- Prévoir une abstraction propre (CSS variables, theme provider, etc.)

**Internationalisation (i18n)**
- [ ] Mettre en place i18n sur l'app
- Langues initiales : FR + EN
- Anticiper l'ajout de langues futures
- Note : EN = "Meteo Score" (sans accent), FR = "Météo Score"

**Typographie**
- [ ] Revoir les fonts Geist - rendu actuel pas top
- Vérifier si c'est un problème de chargement ou de config
- Éventuellement tester d'autres alternatives

**Animations UI**
- [ ] Ajouter des micro-animations
- Style : léger mais moderne/classe
- Transitions subtiles, hover states, loading states
- Éviter le "too much" - rester épuré



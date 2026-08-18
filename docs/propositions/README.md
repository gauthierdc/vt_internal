# Propositions d'optimisation — vt_internal

Analyse des personnalisations `vt_internal` (front JS + back Python) avec un focus
sur le système de **pointage / timer** (feuilles de temps, fiches de travail),
cité comme exemple par l'utilisateur.

Chaque fichier est autonome et priorisé. Les extraits de code sont des **pistes**,
à valider avant application.

> ✅ **Statut : implémenté.** Les propositions 01→05 ont été appliquées.
> Voir [IMPLEMENTATION.md](IMPLEMENTATION.md) pour la liste des fichiers modifiés
> et les étapes de déploiement (`migrate` + `clear-cache` + `restart`).

## Résumé exécutif

Le constat central : **il n'existe aucun module JS partagé**. Chaque personnalisation
de doctype réimplémente ses helpers. Résultat concret :

- Le helper `timer_api` (~10 lignes) est **copié-collé à l'identique** dans
  `visite_technique.js` et `fiche_de_travail.js`.
- Le bloc de boutons de pointage (~40 lignes de `if current_task !== "..."`) est
  **dupliqué à l'identique** dans ces deux mêmes fichiers.
- La galerie photos (~180 lignes : `is_image`, `upload_photos`, `delete_photo`,
  `render`) est **dupliquée** (avec suffixe `_ft` dans l'une des deux copies).
- Chaque action de timer déclenche un `location.reload()` complet — UX brutale.
- Le back a **un bug d'accumulation** (heures par fiche mal cumulées), un **double
  arrondi** divergent, et des **messages toast erronés** (copier-coller).

## Index des propositions

| # | Fichier | Sujet | Impact | Effort |
|---|---------|-------|--------|--------|
| 01 | [01-timer-code.md](01-timer-code.md) | Factorisation code du timer (front + back) | 🔥 Élevé | Moyen |
| 02 | [02-timer-usage.md](02-timer-usage.md) | UX du pointage (widget unique, mobile, live) | 🔥 Élevé | Moyen |
| 03 | [03-galerie-photos.md](03-galerie-photos.md) | Factorisation galerie photos | Élevé | Faible |
| 04 | [04-architecture-frontend.md](04-architecture-frontend.md) | Bundle commun, styles CSS, constantes | Moyen | Moyen |
| 05 | [05-bugs-et-risques.md](05-bugs-et-risques.md) | Bugs concrets détectés dans le back | 🔥 Élevé | Faible |

## Ordre d'attaque recommandé

1. **05 (bugs)** d'abord — correctifs isolés, faible risque, gains immédiats.
2. **03 (galerie)** — factorisation la plus simple, gros volume de code supprimé,
   sert de patron pour le module partagé.
3. **01 (timer code)** — s'appuie sur le module partagé mis en place en 03.
4. **02 (timer usage)** — l'amélioration UX, une fois le code assaini.
5. **04 (architecture)** — nettoyage transverse continu.

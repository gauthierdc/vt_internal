# Implémentation — ce qui a été appliqué

Toutes les propositions 01→05 ont été mises en œuvre. Récapitulatif des fichiers.

## Backend

| Fichier | Changement |
|---|---|
| `vt_internal/constants.py` | **Nouveau.** Constantes métier partagées (types d'activité, états, statuts FT, marqueurs avancement). |
| `vt_internal/utils/time_utils.py` | **Nouveau.** `round_to_quarter()` — arrondi au quart d'heure unique (fin du double arrondi divergent). |
| `vt_internal/events/timesheet.py` | BUG 1 (cumul heures/FT via `setdefault`), BUG 2 (`flt` au lieu de `max(0, None)`), BUG 3 (garde division par zéro). `validate` et `on_submit`/`on_cancel` factorisés (`_hours_per_fiche`, `_apply_ft_costs`). Arrondi unifié. Constantes. |
| `vt_internal/api/timesheet.py` | `timesheet_state()` (état + actions autorisées pilotées par le back), `timesheet_html_block()` devient un alias. `timesheet_post_api` refactoré en **dispatch** de handlers. BUG 4 corrigé (`update_fiche_de_travail_status`, priorité des marqueurs). `print`/debug retirés. `ft_timer_html` rendu via template Jinja. |
| `vt_internal/templates/includes/ft_timer.html` | **Nouveau.** Template du récap d'heures (remplace le HTML concaténé). |
| `vt_internal/patches/recompute_ft_labor_from_timesheets.py` | **Nouveau.** Recalcule `time_spent`/`labor_costs` des fiches faussés par le BUG 1. Enregistré dans `patches.txt`. |
| `vt_internal/hooks.py` | Enregistre `timesheet_state`. Ajoute `vt_common.bundle.js` et `vt_forms.bundle.css`. |

## Frontend

| Fichier | Changement |
|---|---|
| `public/js/vt/timer.js` | **Nouveau.** `vt.timer` : `get_state`, `post`, `render_buttons`, `start_activity`. |
| `public/js/vt/photos.js` | **Nouveau.** `vt.photos` : galerie réutilisable (`render`, upload, delete) pilotée par une liste de sources. |
| `public/js/vt/timer_widget.js` | **Nouveau.** Widget de pointage global flottant (chrono live, actions rapides), défensif. |
| `public/js/vt_common.bundle.js` | **Nouveau.** Point d'entrée bundle qui agrège les modules ci-dessus. |
| `public/css/vt_forms.bundle.css` | **Nouveau.** Styles galerie / sections / widget / bouton Maps (remplace les styles inline JS). |
| `doctype/visite_technique/visite_technique.js` | Réécrit : ~200 lignes dupliquées supprimées. Utilise `vt.timer` + `vt.photos`. Styles → classes CSS. Gardes null ajoutées. |
| `doctype/fiche_de_travail/fiche_de_travail.js` | Réécrit : ~250 lignes dupliquées supprimées. `vt.timer` + `vt.photos`. Bouton 🎯 conservé via `vt.timer.start_activity`. Garde WCR corrigée. Bug `frm.doc.project` → `frm.doc.projet`. |

## Résultat chiffré

- **~450 lignes de JS dupliqué supprimées** (galerie + timer × 2 doctypes).
- Bundle commun `vt_common.bundle.js` ≈ 12,5 Kb (buildé).
- 4 bugs backend corrigés + 1 patch de correction des données.

## Déploiement

Le build des assets est **déjà fait** (`bench build --app vt_internal`). Reste à
appliquer sur l'environnement cible :

```bash
# 1. Récupérer le code (les .bundle sont buildés ; rebuild si autre machine)
bench build --app vt_internal          # si build non partagé

# 2. Appliquer le patch de recalcul + recharger les hooks
bench --site vt.locale migrate         # exécute recompute_ft_labor_from_timesheets

# 3. Recharger hooks (app_include_js/css + timesheet_state) et vider le cache
bench --site vt.locale clear-cache
bench restart                          # ou redémarrage du process web
```

> ⚠️ Le patch `recompute_ft_labor_from_timesheets` **écrase** `time_spent` et
> `labor_costs` de toutes les fiches à partir des feuilles validées. Le lancer une
> seule fois, idéalement après une sauvegarde. S'il ne doit pas tourner
> automatiquement, retirer sa ligne de `patches.txt` et l'exécuter à la main via
> `bench execute`.

## Points à valider en recette

- Pointage depuis une fiche de travail et une visite technique (atelier / visite /
  pause / 🎯 tâche / fin de journée) — plus de `location.reload()`.
- Le bouton 🎯 relie bien la tâche à la fiche ; les boutons génériques **non**.
- Galerie photos : upload (caméra + galerie), suppression, affichage des photos VT
  liées sur la fiche.
- Widget flottant : s'affiche pour un employé, chrono live, masqué sinon.
- Confirmation « Terminer la journée ».

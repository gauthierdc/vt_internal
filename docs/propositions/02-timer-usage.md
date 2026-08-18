# 02 — UX du pointage (usage)

Au-delà du code, l'**expérience** du pointage peut être nettement améliorée. Les
poseurs/opérateurs l'utilisent sur mobile, en chantier, souvent une main prise.

**Fichiers concernés**
- `visite_technique.js`, `fiche_de_travail.js` (boutons de pointage)
- `api/timesheet.py` (`timesheet_state`, `ft_timer_html`)

---

## Constat d'usage actuel

1. Les boutons de pointage n'existent **que** sur une fiche de travail ou une visite
   technique ouverte. Pour pointer « Atelier » sans fiche, il faut d'abord ouvrir un
   document quelconque. Le pointage devrait être **accessible partout**.
2. Chaque clic fait un `location.reload()` → 1 à 3 s d'attente, écran blanc, en 4G
   sur chantier c'est pénible et on ne sait pas si l'action a été prise en compte.
3. Aucune **indication de la tâche en cours ni du temps écoulé** en direct. On ne
   voit pas « Atelier depuis 1h15 ». L'employé re-clique par doute.
4. Jusqu'à **4 boutons** dispersés dans le menu `⏱️` : sur mobile c'est beaucoup de
   scroll pour une action simple.

---

## Proposition A — Un widget de pointage global et persistant

Un petit widget en barre de navigation (ou en bas d'écran sur mobile), présent sur
**toutes** les pages du Desk, chargé via `app_include_js` :

```
┌───────────────────────────────┐
│ 🟢 Atelier · 1h15   [⏸] [⏹]  │   ← état live + actions rapides
└───────────────────────────────┘
```

- **Chrono live** côté client : le back renvoie `from_time` de la tâche courante
  (déjà disponible dans `timesheet_state`), le front incrémente l'affichage avec un
  `setInterval` — zéro appel réseau pour le tic-tac.
- Boutons contextuels : en pause → « ▶️ Reprendre » ; en cours → « ⏸ Pause » + « ⏹ Fin ».
- Clic sur « démarrer une tâche » → un seul dialog qui demande type + fiche (le
  `startActivity` existant, mais accessible partout).

Bénéfice : le pointage n'est plus couplé à l'ouverture d'un document. C'est l'outil
métier qui devient central, pas un sous-menu d'une fiche.

## Proposition B — Supprimer le `location.reload()`

Remplacé par un re-render local des boutons/widget (cf. prop. 01 §B, `onDone`).
Gain : action perçue comme **instantanée**, feedback immédiat via le toast déjà présent.

## Proposition C — Un seul bouton principal contextuel

Au lieu de 4 boutons, **un** bouton primaire dont le libellé dépend de l'état, +
un menu `⏱️` pour les cas secondaires :

| État courant | Bouton principal | Menu secondaire |
|---|---|---|
| Journée non démarrée | ▶️ Démarrer la journée | — |
| Atelier / Chantier en cours | ⏸ Pause | Changer de tâche · ⏹ Fin |
| En pause | ▶️ Reprendre | Changer de tâche · ⏹ Fin |
| Journée finie | (rien, badge « Journée terminée ») | — |

La table `_allowed_actions` (prop. 01) peut porter un flag `primary: true` pour
piloter ça depuis le back.

## Proposition D — Confirmation « fin de journée »

`stop_day` est irréversible pour la saisie (pose `custom_day_finished`). Aujourd'hui
un clic suffit. Ajouter un `frappe.confirm` (« Terminer la journée ? Total : Xh »)
évite les fins de journée accidentelles à 10h.

## Proposition E — Récap live sur la fiche de travail

`ft_timer_html` (api/timesheet.py l.11-52) génère le tableau « heures par personne »
en **HTML concaténé** côté serveur, injecté via `set_value` sur un champ HTML. C'est
fonctionnel mais figé (rafraîchi seulement sur `timeline_refresh`). Deux pistes :

- Court terme : sortir le HTML inline (`<table class="table">…`) vers un **template
  Jinja** (`templates/includes/ft_timer.html`) — plus lisible, réutilisable, échappement correct.
- Moyen terme : renvoyer les **données** (`[{employee, hours}]`) et laisser le front
  rendre, cohérent avec un éventuel refresh live du widget.

---

## Priorisation UX

1. **B** (supprimer reload) — inclus « gratuitement » avec la refonte code prop. 01.
2. **C** (bouton contextuel unique) — gros gain mobile, faible effort.
3. **D** (confirmation fin de journée) — 3 lignes, évite des corrections manuelles.
4. **A** (widget global) — le plus structurant, à planifier comme chantier dédié.
5. **E** (récap) — cosmétique, à faire au passage.

# 01 — Factorisation du code du timer (pointage)

**Fichiers concernés**
- `vt_internal/vt_internal/doctype/visite_technique/visite_technique.js` (l.10-18, l.220-258)
- `vt_internal/vt_internal/doctype/fiche_de_travail/fiche_de_travail.js` (l.4-41, l.290-299, l.482-525)
- `vt_internal/vt_internal/api/timesheet.py` (l.55-200)
- `vt_internal/vt_internal/events/timesheet.py` (l.16-49)

---

## Problème 1 — `timer_api` dupliqué à l'identique

Le même helper existe deux fois, mot pour mot :

```js
// visite_technique.js l.10  ET  fiche_de_travail.js l.4  → IDENTIQUES
const timer_api = (args, message) => {
    return frappe.call({ method: "timesheet_post_api", args })
        .then(() => {
            frappe.show_alert({message: message, indicator: 'green'}, 5)
            location.reload()   // ← reload complet à chaque clic
        })
}
```

Deux problèmes : duplication **et** `location.reload()` qui recharge toute la page
(perte de scroll, re-fetch de tout le formulaire) juste pour rafraîchir 4 boutons.

## Problème 2 — Le bloc de boutons dupliqué (~40 lignes)

Ce bloc est **identique** dans `visite_technique.js` (l.220-258) et
`fiche_de_travail.js` (l.482-525) :

```js
if(r.message.current_task !== "Atelier" && r.message.current_task !== "Day finished") {
    frm.add_custom_button(__("🏠 Démarrer le chronomètre de l'atelier"), ...)
}
if(r.message.current_task !== "Visite technique" && r.message.current_task !== "Day finished") {
    frm.add_custom_button(__("📋 Commencer une visite technique"), ...)
}
// ... pause, stop_day : mêmes if imbriqués avec magic strings répétés
```

Défauts :
- **Magic strings** `"Atelier"`, `"Day finished"`, `"Day not started"`, `"Pause"`,
  `"Visite technique"` répétés partout, sans source unique. Une faute de frappe = bouton fantôme.
- La logique « quel bouton afficher selon l'état » vit **dans le front**, dupliquée.
  Le back connaît déjà l'état → il devrait dire quelles actions sont permises.
- **Messages toast erronés** (copier-coller) : « Commencer une visite technique »
  affiche `'Pause commencée'` (visite_technique.js l.239, fiche_de_travail.js l.506).

---

## Solution — un module partagé + un back qui pilote l'état

### A. Le back retourne les actions permises (plus de logique de state dans le front)

Aujourd'hui `timesheet_html_block` renvoie juste `current_task` (une string) et le
front en déduit tout. Inversons : le back renvoie l'état **et** la liste des actions
autorisées, chacune avec son libellé et son toast.

```python
# api/timesheet.py — remplacer timesheet_html_block

# Constantes partagées (source unique de vérité)
TASK_DAY_NOT_STARTED = "Day not started"
TASK_DAY_FINISHED    = "Day finished"
TASK_PAUSE           = "Pause"
TASK_ATELIER         = "Atelier"
TASK_VISITE          = "Visite technique"

@frappe.whitelist()
def timesheet_state():
    """État de pointage du jour + actions autorisées pour l'employé courant."""
    employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    ts = frappe.db.get_value(
        "Timesheet",
        {"employee": employee, "start_date": frappe.utils.today(), "docstatus": 0},
        ["name", "custom_day_finished"], as_dict=True,
    )

    state = {"timesheet": None, "current_task": TASK_DAY_NOT_STARTED,
             "from_time": None, "fiche_de_travail": None}

    if ts:
        doc = frappe.get_doc("Timesheet", ts.name)
        state["timesheet"] = doc.name
        state["from_time"] = doc.time_logs[0].from_time if doc.time_logs else None
        if ts.custom_day_finished:
            state["current_task"] = TASK_DAY_FINISHED
        else:
            last = doc.time_logs[-1]
            state["fiche_de_travail"] = last.custom_fiche_de_travail
            state["current_task"] = TASK_PAUSE if last.to_time else last.activity_type

    state["actions"] = _allowed_actions(state["current_task"])
    return state


def _allowed_actions(task):
    """Décrit les boutons à afficher côté front — logique centralisée ici."""
    finished = task in (TASK_DAY_FINISHED,)
    actions = []
    if task not in (TASK_ATELIER, TASK_DAY_FINISHED):
        actions.append({"action": "start_construction", "activity_type": TASK_ATELIER,
                        "label": "🏠 Démarrer le chronomètre de l'atelier",
                        "toast": "Atelier commencé", "group": "⏱️"})
    if task not in (TASK_VISITE, TASK_DAY_FINISHED):
        actions.append({"action": "start_construction", "activity_type": TASK_VISITE,
                        "label": "📋 Commencer une visite technique",
                        "toast": "Visite technique commencée", "group": "⏱️"})
    if task not in (TASK_PAUSE, TASK_DAY_FINISHED, TASK_DAY_NOT_STARTED):
        actions.append({"action": "start_break",
                        "label": "⏸️ Faire une pause",
                        "toast": "Pause commencée", "group": "⏱️"})
    if task not in (TASK_DAY_NOT_STARTED, TASK_DAY_FINISHED):
        actions.append({"action": "stop_day",
                        "label": "⏹️ Terminer la journée",
                        "toast": "Journée terminée", "group": "⏱️"})
    return actions
```

> On garde l'ancien `timesheet_html_block` en alias le temps de la migration, ou on
> le fait renvoyer `timesheet_state()` pour ne rien casser.

### B. Un module JS partagé `vt_timer`

Créer `vt_internal/public/js/vt_timer.bundle.js` (chargé via `app_include_js`, cf. prop. 04) :

```js
// vt_timer.bundle.js — point unique du pointage côté front
frappe.provide("vt.timer");

vt.timer.post = (args, toast) =>
    frappe.call({ method: "timesheet_post_api", args }).then(() => {
        if (toast) frappe.show_alert({ message: toast, indicator: "green" }, 5);
    });

/**
 * Injecte les boutons de pointage dans un formulaire.
 * @param {object} frm
 * @param {object} [extra] - champs ajoutés à chaque action (ex: fiche_de_travail)
 * @param {function} [onDone] - callback après action (défaut: refresh boutons)
 */
vt.timer.render_buttons = function (frm, extra = {}, onDone) {
    return frappe.call({ method: "timesheet_state" }).then((r) => {
        const state = r.message;
        // purge les anciens boutons du groupe pour éviter les doublons au refresh
        frm.clear_custom_buttons?.();
        state.actions.forEach((a) => {
            frm.add_custom_button(__(a.label), () => {
                vt.timer.post({ ...a, ...extra }, a.toast)
                    .then(() => (onDone ? onDone() : vt.timer.render_buttons(frm, extra, onDone)));
            }, a.group);
        });
        return state;
    });
};
```

### C. Les deux doctypes deviennent triviaux

```js
// fiche_de_travail.js — refresh()
vt.timer.render_buttons(frm, { fiche_de_travail: frm.doc.name });
// + bouton spécifique "🎯 Démarrer le chronomètre de cette tâche" via startActivity(frm)

// visite_technique.js — refresh()
vt.timer.render_buttons(frm, { activity_type: "Visite technique" });
```

**Bilan** : ~80 lignes dupliquées → 1 module de ~30 lignes + 2 appels. Plus de
`location.reload()`, plus de magic strings dans le front, messages toast corrects,
et la règle métier « quel bouton quand » vit à un seul endroit (le back).

---

## Problème 3 — Double arrondi divergent (back)

`timesheet_post_api` arrondit `from_time`/`to_time` au quart d'heure (l.101-108,
algo « `//15` +15 si reste ≥ 8 »). Puis `events/timesheet.py validate()` (l.25-38)
**réarrondit tout** avec un algo **différent** (`round(minutes/15.0)*15`, arrondi
banquier). Le premier arrondi est donc **inutile** et les deux algos ne donnent pas
toujours le même résultat (ex. minute 7 ou 8).

**Solution** : une seule fonction d'arrondi, utilisée aux deux endroits.

```python
# utils/time_utils.py
def round_to_quarter(dt):
    dt = frappe.utils.get_datetime(dt)
    delta = round(dt.minute / 15.0) * 15 - dt.minute
    return frappe.utils.add_to_date(
        dt.replace(second=0, microsecond=0), minutes=delta, as_datetime=True
    )
```

`timesheet_post_api` peut alors stocker `now_datetime()` brut (l'arrondi final est
garanti par `validate`), ou appeler `round_to_quarter` — mais **une seule** définition.

---

## Problème 4 — Dispatch d'action en série de `if`

`timesheet_post_api` enchaîne `if action == "duplicate"`, `if action == "start_break"`…
(l.143-200). Le pré-calcul de `rounded_time`/`duration`/création du timesheet se fait
**toujours**, même pour `duplicate` qui n'en a pas besoin. Un dispatch par dict de
handlers clarifierait et éviterait le travail inutile :

```python
HANDLERS = {
    "start_construction": _start_construction,
    "start_break": _start_break,
    "stop_day": _stop_day,
    "duplicate": _duplicate,
    "add_comment": _add_comment,
}
HANDLERS[action](doc, ctx)   # ctx = {rounded_time, duration, form_dict...}
```

Non bloquant, mais rend chaque action testable isolément.

# 05 — Bugs et risques détectés (back)

Correctifs isolés, à faible risque, à traiter **en premier** (indépendants des refactos).

---

## 🐞 BUG 1 — Heures par fiche mal cumulées (`on_submit` / `on_cancel`)

**Fichier** : `events/timesheet.py` l.70-88 (`on_submit`) et l.90-105 (`on_cancel`).

```python
for tl in doc.time_logs:
    if tl.custom_fiche_de_travail:
        time_per_ft[tl.custom_fiche_de_travail] = 0          # ← RESET à chaque tour
        if tl.custom_fiche_de_travail not in time_per_ft:    # ← toujours False (on vient de la créer)
            time_per_ft[tl.custom_fiche_de_travail] = 0
        time_per_ft[tl.custom_fiche_de_travail] += tl.hours
```

La 1re ligne remet la clé à `0` **à chaque itération**. Si une même fiche de travail
apparaît dans **plusieurs lignes** de la feuille de temps (cas courant : une pause au
milieu, ou plusieurs interventions sur la même fiche dans la journée), **seules les
heures de la dernière ligne sont comptées**. Les précédentes sont perdues.

Conséquence directe : `time_spent` et `labor_costs` de la fiche de travail sont
**sous-évalués** → coûts de main-d'œuvre faux dans le prévisionnel chantier.

**Correctif** :

```python
for tl in doc.time_logs:
    if tl.custom_fiche_de_travail:
        time_per_ft.setdefault(tl.custom_fiche_de_travail, 0)
        time_per_ft[tl.custom_fiche_de_travail] += tl.hours
```

> ⚠️ Impact données historiques : les feuilles déjà validées avec ce bug ont écrit
> des `labor_costs`/`time_spent` erronés. Prévoir un patch de recalcul si ces
> montants sont exploités.

---

## 🐞 BUG 2 — `max(0, None)` → TypeError

**Fichier** : `events/timesheet.py` l.82-83 et l.101-102.

```python
time_spent  = max(0, frappe.db.get_value("Fiche de travail", k, "time_spent"))
labor_costs = max(0, frappe.db.get_value("Fiche de travail", k, "labor_costs"))
```

Si `time_spent` / `labor_costs` est `NULL` en base (fiche jamais pointée),
`get_value` renvoie `None` et `max(0, None)` lève `TypeError: '>' not supported
between 'int' and 'NoneType'` en Python 3 → **la validation de la feuille de temps
échoue**.

**Correctif** : `max(0, frappe.utils.flt(frappe.db.get_value(...)))`.

---

## 🐞 BUG 3 — Division par zéro si `total_hours == 0`

**Fichier** : `events/timesheet.py` l.85 et l.103.

```python
percentage_of_time = time_per_ft[k] / doc.total_hours
```

Une feuille validée avec `total_hours = 0` (toutes lignes à 0h, ou lignes sans
`to_time`) provoque `ZeroDivisionError`. Garder un garde : `if doc.total_hours:` avant
la boucle de répartition.

---

## 🐞 BUG 4 — `update_fiche_de_travail_status` : `if` au lieu de `elif`

**Fichier** : `api/timesheet.py` l.209-217.

```python
if "⚫️" in statuses:
    avancement = "⚫️"
if "🔴" in statuses:          # ← devrait être elif
    avancement = "🔴"
elif "🟠" in statuses:
    ...
```

Le 1er `if` (⚫️) est **séparé** du bloc `if/elif` suivant. Si les statuts contiennent
à la fois ⚫️ et 🔴, `avancement` est écrasé par 🔴. De plus, si **aucun** 🔴/🟠/🟢
n'est présent mais ⚫️ oui, le `else` final remet `avancement = ""` → le ⚫️ est perdu.
`avancement` peut aussi être **non défini** (UnboundLocalError) si `statuses` est vide
et qu'on tombe hors des branches… en fait le `else` couvre, mais l'ordre de priorité
est incohérent.

**Correctif** : une seule chaîne `if/elif` ordonnée par priorité, ou un mapping
priorité → valeur.

```python
for marker in ("⚫️", "🔴", "🟠", "🟢"):
    if marker in statuses:
        avancement = marker
        break
else:
    avancement = ""
```

---

## 🐞 BUG 5 — Messages toast erronés (front, copier-coller)

**Fichiers** : `visite_technique.js` l.239, `fiche_de_travail.js` l.506.

Le bouton « 📋 Commencer une visite technique » affiche le toast `'Pause commencée'`.
Erreur de copier-coller, corrigée nativement par la refonte prop. 01 (le toast vient
du back). En attendant : corriger la chaîne.

---

## ⚠️ RISQUE 6 — Double arrondi divergent

Détaillé en [01-timer-code.md](01-timer-code.md#problème-3). `timesheet_post_api`
arrondit avec un algorithme (`//15` +15 si reste ≥ 8), `validate` réarrondit avec un
autre (`round(x/15)*15`). Résultats potentiellement différents autour des minutes
7-8. Unifier via une seule fonction `round_to_quarter`.

---

## ⚠️ RISQUE 7 — `r.message.name` sans garde

**Fichier** : `fiche_de_travail.js` l.387-388.

```js
frappe.db.get_value("Work Completion Receipt", {project: frm.doc.projet, docstatus: 1}, "name")
    .then(r => { if(!r.message.name) { ... } })
```

Si aucun WCR n'existe, `r.message` peut être `{}` voire `undefined` selon la version
Frappe → `r.message.name` peut lever. Utiliser `if(!r.message?.name)`.

De même `visite_technique.js` l.216-218 : `r.message.custom_quotation_approval_link`
sans garde si le devis n'a pas ce champ renseigné.

---

## Récapitulatif priorité

| Bug | Sévérité | Effort | Impact données |
|---|---|---|---|
| 1 — cumul heures/FT | 🔴 Haute | 2 lignes | Oui (recalcul) |
| 2 — max(0, None) | 🟠 Moyenne | 1 ligne | Non |
| 3 — /0 | 🟠 Moyenne | 1 ligne | Non |
| 4 — if/elif avancement | 🟠 Moyenne | 5 lignes | Cosmétique |
| 5 — toast | 🟢 Basse | 1 ligne | Non |
| 6 — double arrondi | 🟢 Basse | refacto | Marginal |
| 7 — gardes `?.` | 🟢 Basse | 2 lignes | Non |

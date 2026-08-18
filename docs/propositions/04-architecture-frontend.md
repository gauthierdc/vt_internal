# 04 — Architecture front : bundle commun, styles, constantes

Propositions transverses qui rendent possibles les prop. 01 et 03.

---

## A. Créer un bundle commun `vt_common`

Aujourd'hui il n'y a **aucun** module JS partagé (`grep` : chaque `public/js/*.js`
est autonome). D'où toutes les duplications.

Créer un point d'entrée `vt_internal/public/js/vt_common.bundle.js` qui regroupe les
sous-modules (`vt.timer`, `vt.photos`, helpers divers) et le déclarer dans `hooks.py` :

```python
# hooks.py — app_include_js
app_include_js = [
    "bundle_editor_patch.bundle.js",
    "customer_quick_entry.bundle.js",
    "vt_sidebar_default.bundle.js",
    "vt_event_popup.bundle.js",
    "vt_common.bundle.js",   # ← timer + photos + helpers partagés
]
```

Chargé une fois sur tout le Desk, disponible dans tous les `doctype_js`. C'est le
socle des factorisations 01 et 03.

## B. Sortir les styles inline vers du CSS

Des styles sont appliqués de deux façons peu maintenables :

1. **Template strings** avec `style="..."` en dur (galeries, boutons photo) — hex,
   tailles, ombres répétés des dizaines de fois.
2. **`frm.fields_dict['x'].wrapper.css('background-color', 'antiquewhite')`** en JS,
   ex. `visite_technique.js` l.286-288, `fiche_de_travail.js` l.361-365. Les noms de
   sections (`section_break_woyn`, `section_break_puil`, `section_break_qjpd`…) sont
   codés en dur ; si un champ est renommé dans l'éditeur, le JS casse silencieusement.

Proposer un `vt_internal/public/css/vt_forms.css` (bundle CSS déjà supporté, cf.
`vt_calendar.bundle.css` dans hooks) avec des classes :

```css
.vt-section--info  { background-color: antiquewhite; }
.vt-section--work  { background-color: cadetblue; }
.vt-photo-grid     { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px,1fr)); gap: 10px; }
.vt-photo-item img { width: 100%; height: 200px; object-fit: cover; cursor: pointer; }
.vt-btn-map        { background:#1E88E5; color:#fff; width:100%; border-radius:8px; /* … */ }
```

Puis en JS : `frm.get_field('travaux_section').$wrapper.addClass('vt-section--work')`.
Idéalement, la coloration de section se fait carrément **sans JS**, via le CSS du
doctype ou des propriétés de champ. Cela supprime la dépendance aux `fieldname` obscurs.

> Note : la couleur du bouton Google Maps (`visite_technique.js` l.300-359,
> `enhanceOpenInMapsButton` + `setTimeout(…, 50)`) mérite le même traitement — le
> `setTimeout` de 50 ms pour attendre le rendu est un contournement fragile.

## C. Centraliser les constantes métier

Les mêmes chaînes vivent des deux côtés (front et back), non partagées :

- Types d'activité / états : `"Atelier"`, `"Visite technique"`, `"Pause"`,
  `"Day finished"`, `"Day not started"`, `"Chantier"`.
- Statuts fiche de travail : `"À faire"`, `"En attente de fabrication"`, `"En cours"`,
  `"Fait"` (cf. `events/timesheet.py` l.23, `api/timesheet.py` l.209-217).
- Statuts d'avancement emoji `⚫️ 🔴 🟠 🟢` (`update_fiche_de_travail_status`, l.209-217)
  — noter au passage le **bug logique** : le premier `if "⚫️"` n'est pas dans le
  `elif` suivant, donc une valeur ⚫️ est écrasée par le bloc `if/elif` d'en dessous
  (voir prop. 05).

Proposer :
- Back : un `constants.py` (ou un DocType « Settings ») avec ces valeurs.
- Front : les exposer via `frappe.boot` ou les dupliquer dans `vt.const` du bundle
  commun — au moins un seul endroit par couche.

## D. Nettoyer les logs de debug

`console.log(r.message)` (visite_technique.js l.224, fiche_de_travail.js l.486) et
`print(url)` / `print(frappe.form_dict)` / `print("Aucune tâche commencé")`
(api/timesheet.py l.29, 138, 141, 219) traînent en production. À retirer ou passer en
`frappe.logger().debug(...)`.

## E. Uniformiser les helpers d'appel

Le code mélange `frappe.call({method, args}).then()`, `frappe.db.get_value(...).then()`
et `frappe.client.get_list` via `frappe.call`. `frappe.db.get_list` / `frappe.db.delete_doc`
sont plus concis et déjà utilisés ailleurs. Uniformiser dans le module commun (fait
naturellement en appliquant 01 et 03).

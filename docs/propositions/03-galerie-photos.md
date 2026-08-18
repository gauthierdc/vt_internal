# 03 — Factorisation de la galerie photos

C'est la duplication la plus volumineuse et la plus simple à corriger.

**Fichiers concernés**
- `visite_technique.js` l.20-208 (~190 lignes)
- `fiche_de_travail.js` l.43-287 (~245 lignes, suffixées `_ft`)

---

## Constat

Les deux fichiers contiennent la **même** galerie photos, à des détails près :

| Fonction | visite_technique.js | fiche_de_travail.js |
|---|---|---|
| `is_image` | l.22 | l.45 — **identique** |
| `open_photo_dialog` | l.113 | l.195 (`_ft`) — **identique** |
| `upload_photos` | l.136 | l.215 (`_ft`) — **identique** |
| `delete_photo` | l.189 | l.268 (`_ft`) — **identique** |
| `render_photos_section` | l.27 | l.50 — variante (2 sources) |

Seul `render_photos_section` diffère réellement : la fiche de travail affiche en plus
les photos de la visite technique liée. Tout le reste (upload XHR, suppression,
détection image, dialog caméra/galerie) est **strictement identique**, juste renommé.

Défauts annexes présents dans les deux :
- **Styles inline** massifs (hex, tailles) répétés dans des template strings (cf. prop. 04).
- Upload via `XMLHttpRequest` fait main alors que Frappe fournit `frappe.ui.FileUploader`.
- Hauteur d'image codée en dur et **différente** (150px vs 250px) — incohérence visuelle.

---

## Solution — module `vt_photos`

Créer `vt_internal/public/js/vt_photos.bundle.js` :

```js
frappe.provide("vt.photos");

vt.photos.is_image = (url) =>
    !!url && /\.(jpe?g|png|gif|webp|bmp|heic|heif)$/i.test(url);

vt.photos.list = (doctype, name) =>
    frappe.db.get_list("File", {
        filters: { attached_to_doctype: doctype, attached_to_name: name, is_folder: 0 },
        fields: ["name", "file_url", "file_name"],
        order_by: "creation desc", limit: 0,
    }).then((files) => files.filter((f) => vt.photos.is_image(f.file_url)));

vt.photos.delete = (name) =>
    frappe.confirm(__("Supprimer cette photo ?"), () =>
        frappe.db.delete_doc("File", name).then(() =>
            frappe.show_alert({ message: __("Photo supprimée"), indicator: "green" })));

// Upload : réutilise le FileUploader natif (drag&drop, caméra, progress inclus)
vt.photos.upload = (frm, { camera = false } = {}) =>
    new Promise((resolve) => {
        new frappe.ui.FileUploader({
            doctype: frm.doctype, docname: frm.doc.name, allow_multiple: !camera,
            restrictions: { allowed_file_types: ["image/*"] },
            on_success: resolve,
        });
    });

/**
 * Rend une galerie photos dans un champ HTML.
 * @param {object} opts.wrapper  $wrapper du champ
 * @param {Array}  opts.sources  [{ doctype, name, title, editable }]
 */
vt.photos.render = async function (frm, { field, sources }) {
    const dict = frm.fields_dict[field];
    if (!dict) return;
    if (frm.is_new()) {
        dict.$wrapper.html(vt.photos._placeholder());
        return;
    }
    const blocks = await Promise.all(sources.map(async (s) => {
        const files = await vt.photos.list(s.doctype, s.name);
        return vt.photos._section(s, files);
    }));
    dict.$wrapper.html(blocks.join(""));
    vt.photos._bind(frm, dict.$wrapper, field, sources);
};
```

`_section`, `_placeholder`, `_bind` regroupent le template HTML (idéalement en
classes CSS, cf. prop. 04) et le câblage des boutons.

## Usage résultant

```js
// visite_technique.js
vt.photos.render(frm, {
    field: "photos_section",
    sources: [{ doctype: "Visite Technique", name: frm.doc.name, editable: true }],
});

// fiche_de_travail.js
vt.photos.render(frm, {
    field: "photos",
    sources: [
        ...(frm.doc.visite_technique
            ? [{ doctype: "Visite Technique", name: frm.doc.visite_technique,
                 title: "Photos de la Visite Technique", editable: false }]
            : []),
        { doctype: "Fiche de travail", name: frm.doc.name,
          title: "Photos de cette Fiche de travail", editable: true },
    ],
});
```

**Bilan** : ~435 lignes cumulées → ~1 module de ~80 lignes + 2 appels déclaratifs.
La notion « une galerie = une liste de sources, certaines éditables » couvre les deux
cas et tout futur doctype (ex. Quality Incident, Work Completion Receipt).

## Bonus — remplacer l'upload XHR maison

Les deux `upload_photos` réimplémentent la barre de progression et le POST
`upload_file` à la main (~50 lignes chacun). `frappe.ui.FileUploader` fournit nativement
multi-fichiers, caméra, drag & drop, progress et gestion d'erreur. Suppression pure de
code + comportement plus robuste (retries, types MIME).

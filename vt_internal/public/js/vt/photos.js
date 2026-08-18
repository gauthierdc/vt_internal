// Module partagé de galerie photos.
// Remplace les ~430 lignes dupliquées entre visite_technique.js et
// fiche_de_travail.js. Chargé via vt_common.bundle.js.
//
// Modèle : une galerie = une liste de "sources", chacune {doctype, name, title, editable}.
// Une source editable affiche les boutons d'ajout et de suppression.

frappe.provide("vt.photos");

vt.photos.is_image = (url) =>
    !!url && /\.(jpe?g|png|gif|webp|bmp|heic|heif)$/i.test(url);

// Liste les fichiers image attachés à un document.
vt.photos.list = (doctype, name) =>
    frappe.db
        .get_list("File", {
            filters: { attached_to_doctype: doctype, attached_to_name: name, is_folder: 0 },
            fields: ["name", "file_url", "file_name"],
            order_by: "creation desc",
            limit: 0,
        })
        .then((files) => (files || []).filter((f) => vt.photos.is_image(f.file_url)));

// --- HTML (styles dans vt_forms.bundle.css) ---

vt.photos._placeholder = () => `
    <div class="vt-photos__placeholder">
        <p class="text-muted">Enregistrez le document pour ajouter des photos</p>
    </div>`;

vt.photos._grid = (files, canDelete) => {
    if (!files.length) {
        return `<div class="vt-photos__empty">
                    <i class="fa fa-image"></i>
                    <p class="text-muted">Aucune photo</p>
                </div>`;
    }
    const items = files
        .map(
            (f) => `
        <div class="vt-photos__item">
            <a href="${f.file_url}" target="_blank">
                <img class="vt-photos__img" src="${f.file_url}" alt="${frappe.utils.escape_html(f.file_name || "")}">
            </a>
            ${
                canDelete
                    ? `<button class="btn btn-danger btn-xs vt-photos__delete" data-file="${f.name}">
                           <i class="fa fa-times"></i>
                       </button>`
                    : ""
            }
        </div>`
        )
        .join("");
    return `<div class="vt-photos__grid">${items}</div>`;
};

vt.photos._section = (source, files) => {
    const title = source.title
        ? `<h6 class="vt-photos__title">${frappe.utils.escape_html(source.title)}</h6>`
        : "";
    const actions = source.editable
        ? `<div class="vt-photos__actions">
               <button class="btn btn-primary btn-sm vt-photos__camera"><i class="fa fa-camera"></i> Prendre une photo</button>
               <button class="btn btn-default btn-sm vt-photos__pick"><i class="fa fa-image"></i> Galerie</button>
           </div>`
        : "";
    return `<div class="vt-photos__section">${title}${actions}${vt.photos._grid(files, !!source.editable)}</div>`;
};

// --- Upload / suppression ---

vt.photos._pick_files = (camera) =>
    new Promise((resolve) => {
        const $input = $(
            camera
                ? '<input type="file" accept="image/*" capture="environment" style="display:none">'
                : '<input type="file" accept="image/*" multiple style="display:none">'
        );
        $("body").append($input);
        $input.on("change", function () {
            resolve(this.files);
            $input.remove();
        });
        $input.click();
    });

vt.photos.upload = (frm, files) => {
    const total = files.length;
    let done = 0;
    let errors = 0;
    frappe.show_progress("Upload", 0, total, "Upload en cours...");

    const next = (i) =>
        new Promise((resolve) => {
            if (i >= total) {
                frappe.hide_progress();
                if (errors)
                    frappe.msgprint(__(`${done} photo(s) ajoutée(s), ${errors} erreur(s)`));
                else frappe.show_alert({ message: __(`${done} photo(s) ajoutée(s)`), indicator: "green" });
                return resolve();
            }
            const fd = new FormData();
            fd.append("file", files[i], files[i].name);
            fd.append("doctype", frm.doctype);
            fd.append("docname", frm.doc.name);
            fd.append("is_private", 0);

            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/api/method/upload_file", true);
            xhr.setRequestHeader("X-Frappe-CSRF-Token", frappe.csrf_token);
            xhr.onload = () => {
                if (xhr.status === 200) {
                    done++;
                    frappe.show_progress("Upload", done, total, `${done}/${total} photos...`);
                } else {
                    console.error("Upload error:", xhr.responseText);
                    errors++;
                }
                next(i + 1).then(resolve);
            };
            xhr.onerror = () => {
                errors++;
                next(i + 1).then(resolve);
            };
            xhr.send(fd);
        });

    return next(0);
};

vt.photos.delete = (name) =>
    new Promise((resolve) => {
        frappe.confirm(__("Supprimer cette photo ?"), () => {
            frappe.db.delete_doc("File", name).then(() => {
                frappe.show_alert({ message: __("Photo supprimée"), indicator: "green" });
                resolve(true);
            });
        });
    });

// --- Rendu principal ---

/**
 * Rend une galerie photos dans un champ HTML du formulaire.
 * @param {object} frm
 * @param {string} opts.field   - fieldname du champ HTML
 * @param {Array}  opts.sources - [{doctype, name, title?, editable?}]
 */
vt.photos.render = function (frm, opts) {
    const dict = frm.fields_dict[opts.field];
    if (!dict) return Promise.resolve();

    frm.__vt_photos_opts = opts; // mémorisé pour re-render après upload/suppression

    if (frm.is_new() || !frm.doc.name) {
        dict.$wrapper.html(vt.photos._placeholder());
        return Promise.resolve();
    }

    const sources = opts.sources.filter((s) => s && s.name);
    return Promise.all(sources.map((s) => vt.photos.list(s.doctype, s.name))).then((lists) => {
        dict.$wrapper.html(
            `<div class="vt-photos">${sources.map((s, i) => vt.photos._section(s, lists[i])).join("")}</div>`
        );
        vt.photos._bind(frm, dict.$wrapper);
    });
};

vt.photos._rerender = (frm) => frm.__vt_photos_opts && vt.photos.render(frm, frm.__vt_photos_opts);

vt.photos._bind = function (frm, $wrapper) {
    $wrapper.find(".vt-photos__camera").off("click").on("click", () =>
        vt.photos._pick_files(true).then((files) => files.length && vt.photos.upload(frm, files).then(() => vt.photos._rerender(frm)))
    );
    $wrapper.find(".vt-photos__pick").off("click").on("click", () =>
        vt.photos._pick_files(false).then((files) => files.length && vt.photos.upload(frm, files).then(() => vt.photos._rerender(frm)))
    );
    $wrapper.find(".vt-photos__delete").off("click").on("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        vt.photos.delete($(this).data("file")).then((ok) => ok && vt.photos._rerender(frm));
    });
};

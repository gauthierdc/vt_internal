// Copyright (c) 2025, Verre & Transparence and contributors
// For license information, please see license.txt
//
// Pointage : widget global vt.timer.widget
// Galerie photos : vt.photos (vt_common.bundle.js)

frappe.ui.form.on("Visite Technique", {
    refresh: function (frm) {
        // Galerie photos de la visite technique.
        vt.photos.render(frm, {
            field: "photos_section",
            sources: [{ doctype: "Visite Technique", name: frm.doc.name, editable: true }],
        });

        // Le pointage se fait désormais via le widget global (vt.timer.widget).

        if (frm.doc.quotation) {
            frappe.db
                .get_value("Quotation", frm.doc.quotation, "custom_quotation_approval_link")
                .then((r) => {
                    const link = r.message && r.message.custom_quotation_approval_link;
                    if (link) frm.add_web_link(link, "Voir le lien du BPA");
                });
        }

        if (frm.doc.projet) {
            frm.add_custom_button(__("Événement"), function () {
                frappe.new_doc("Event", { project: frm.doc.projet, custom_visite_technique: frm.doc.name });
            }, __("Create"));

            frm.add_custom_button(__("📁"), function () {
                const dialog = new frappe.ui.Dialog({
                    size: "extra-large",
                    title: __("Details du projet"),
                    fields: [{ fieldname: "content", fieldtype: "HTML" }],
                    primary_action: function () {
                        frappe.set_route("Form", "Project", frm.doc.projet);
                    },
                    primary_action_label: __("Projet"),
                });
                frappe.call({
                    method: "vt_internal.vt_internal.api.project_details.project_details",
                    args: { project: frm.doc.projet },
                }).then((r) => dialog.fields_dict.content.$wrapper.html(r.message.html));
                dialog.show();
            });
        }

        // Couleurs de sections (cf. vt_forms.bundle.css).
        // NB : pour un Section Break, l'objet section expose `.wrapper` (jQuery),
        // pas `.$wrapper` — utiliser `.wrapper` sinon la classe n'est jamais posée.
        const paint = (field, cls) => frm.fields_dict[field] && frm.fields_dict[field].wrapper.addClass(cls);
        paint("informations_section", "vt-section--info");
        paint("section_break_woyn", "vt-section--work");
        paint("section_break_puil", "vt-section--work");

        frm.set_query("contact", function () {
            if (frm.doc.client) {
                return { filters: { link_doctype: "Customer", link_name: frm.doc.client } };
            }
        });

        // Bouton Google Maps : afficher l'adresse comme libellé + style dédié.
        enhance_maps_button(frm);
    },

    client: function (frm) {
        frm.set_query("contact", function () {
            if (frm.doc.client) {
                return {
                    query: "frappe.contacts.doctype.contact.contact.contact_query",
                    filters: { link_doctype: "Customer", link_name: frm.doc.client },
                };
            }
        });
    },

    open_in_google_maps: function (frm) {
        maps_address(frm).then((query) => {
            if (query) {
                window.open(
                    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`,
                    "_blank"
                );
            } else {
                frappe.msgprint(__("Adresse non renseignée"));
            }
        });
    },
});

// Résout l'adresse affichable (champs Address détaillés, sinon valeur brute).
function maps_address(frm) {
    if (!frm.doc.address) return Promise.resolve(frm.doc.address);
    return frappe.db
        .get_value("Address", frm.doc.address, ["address_line1", "address_line2", "city", "pincode"])
        .then((r) => {
            const a = (r && r.message) || {};
            const parts = [a.address_line1, a.address_line2, a.city, a.pincode].filter(Boolean);
            return parts.join(", ") || frm.doc.address;
        })
        .catch(() => frm.doc.address);
}

function enhance_maps_button(frm) {
    // Le champ est rendu de façon asynchrone : petite temporisation.
    setTimeout(() => {
        const field = frm.fields_dict && frm.fields_dict.open_in_google_maps;
        if (!field || !field.$wrapper) return;
        const $btn = field.$wrapper.find(".btn, button").first();
        if (!$btn.length) return;
        $btn.addClass("vt-btn-map");
        maps_address(frm).then((addr) => $btn.text(addr ? `📍 ${addr}` : "📍 Ouvrir dans Google Maps"));
    }, 50);
}

Object.assign((frappe.listview_settings["Visite Technique"] = {
    hide_name_column: true,
    add_fields: ["projet"],
    button: {
        show: (doc) => doc.projet,
        get_description: (doc) => doc.project,
        get_label: () => "📁",
        action: (doc) => frappe.set_route("Form", "Project", doc.projet),
    },
}));

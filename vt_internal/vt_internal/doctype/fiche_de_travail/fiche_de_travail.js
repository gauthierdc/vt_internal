// Fiche de travail — logique de formulaire.
// Pointage : widget global vt.timer.widget · Galerie photos : vt.photos (vt_common.bundle.js)

frappe.ui.form.on("Fiche de travail", {
    timeline_refresh: (frm) => {
        frappe.call({ method: "ft_timer_html", args: { ft: frm.doc.name } }).then((r) => {
            frm.get_field("timer_html").set_value(r.message.html);
        });
    },

    address: function (frm) {
        frappe.contacts.get_address_display(frm);
    },

    refresh: function (frm) {
        // Galerie photos : celles de la visite technique liée (lecture seule) + celles de la fiche.
        vt.photos.render(frm, {
            field: "photos",
            sources: [
                ...(frm.doc.visite_technique
                    ? [{
                        doctype: "Visite Technique",
                        name: frm.doc.visite_technique,
                        title: "Photos de la Visite Technique",
                        editable: false,
                    }]
                    : []),
                {
                    doctype: "Fiche de travail",
                    name: frm.doc.name,
                    title: "Photos de cette Fiche de travail",
                    editable: true,
                },
            ],
        });

        if (frm.doc.projet) {
            frm.add_custom_button(__("Événement"), function () {
                frappe.new_doc("Event", { project: frm.doc.projet, custom_fiche_de_travail: frm.doc.name });
            }, __("Create"));

            frappe.db.get_list("Quality Incident", {
                fields: ["name", "object"],
                filters: { project: frm.doc.projet },
            }).then((results) => {
                if (results && results.length) {
                    const links = results
                        .map((i) => `<a href="/app/quality-incident/${i.name}" target="_blank">${i.object}</a>`)
                        .join(", ");
                    frm.set_intro(`<b>🛑 Ce projet fait l'objet de ${results.length} incident(s) qualité : </b>${links}`, "red");
                }
            });

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

            frm.add_custom_button(__("Incident qualité"), function () {
                frappe.new_doc("Quality Incident", { project: frm.doc.projet, fiche_de_travail: frm.doc.name });
            }, __("Create"));
        }

        if (!frappe.is_mobile()) {
            frm.add_custom_button(__("Commande fournisseur"), function () {
                frappe.new_doc("Purchase Order", { project: frm.doc.projet, cost_center: frm.doc.cost_center });
            }, __("Create"));
        }

        // Couleurs de sections (cf. vt_forms.bundle.css).
        const paint = (field, cls) => frm.fields_dict[field] && frm.fields_dict[field].$wrapper.addClass(cls);
        paint("section_break_1", "vt-section--info");
        paint("section_break_odzh", "vt-section--info");
        paint("photos_avant_section", "vt-section--info");
        paint("travaux_section", "vt-section--work");
        paint("section_break_qjpd", "vt-section--work");

        frm.set_query("team", function () {
            return {
                filters: [
                    ["Employee", "designation", "in", ["Poseur", "Opérateur atelier"]],
                    ["Employee", "status", "=", "active"],
                    ["Employee", "company", "=", frm.doc.company],
                ],
            };
        });

        frm.set_query("visite_technique", function () {
            return { filters: [["Visite Technique", "projet", "=", frm.doc.projet]] };
        });

        // Bouton de signature « réception de travaux » si aucune réception validée.
        frappe.db
            .get_value("Work Completion Receipt", { project: frm.doc.projet, docstatus: 1 }, "name")
            .then((r) => {
                if (r.message && r.message.name) return;
                frm.add_custom_button("✍️", () => open_wcr_dialog(frm));
            });
    },
});

function open_wcr_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: "Réception de travaux",
        size: "small",
        fields: [
            { label: "Client absent", fieldname: "absent_customer", fieldtype: "Check" },
            { label: "Nom du signataire", fieldname: "signatory", fieldtype: "Data", reqd: true },
            { label: "Fait à", fieldname: "place", fieldtype: "Data", reqd: true },
            {
                label: "Signature de la réception des travaux sans réserves",
                fieldname: "signature",
                fieldtype: "Signature",
                reqd: true,
            },
            { label: "Notifier par mail", fieldname: "notify_customer", fieldtype: "Check", default: 1 },
        ],
        primary_action_label: "Valider",
        secondary_action_label: "Plus d'options",
        secondary_action(values) {
            frappe.new_doc("Work Completion Receipt", {
                sales_order: frm.doc.sales_order,
                absent_customer: frm.doc.absent_customer,
                signature_du_client: values.signature,
                notify_customer_on_validation: values.notify_customer,
                "fait_à": values.place,
            });
        },
        primary_action(values) {
            frappe.call({
                method: "frappe.client.submit",
                args: {
                    doc: {
                        doctype: "Work Completion Receipt",
                        absent_customer: values.absent_customer,
                        "fait_à": values.place,
                        project: frm.doc.projet,
                        sales_order: frm.doc.sales_order,
                        customer: frm.doc.customer,
                        accepted: 1,
                        signature_du_client: values.signature,
                        notify_customer_on_validation: values.notify_customer,
                        signatory: values.signatory,
                    },
                },
            }).then(() => {
                frappe.show_alert({ message: "Réception de travaux signé", indicator: "green" }, 5);
                frm.set_value("work_completion_receipt_signed", 1);
                frm.set_value("status", "Fait");
                frm.save();
                frm.remove_custom_button("✍️");
            });
            d.hide();
        },
    });

    // Pré-remplir le signataire avec l'utilisateur courant si le client est absent.
    d.fields_dict.absent_customer.$input.on("change", function () {
        d.set_value("signatory", d.get_value("absent_customer") ? frappe.session.user_fullname : "");
    });

    d.show();
}

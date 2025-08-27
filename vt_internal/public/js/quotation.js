// Helper functions to keep refresh tidy
function addWebLinks(frm) {
    if (frm.doc.custom_quotation_approval_link) {
        frm.add_web_link(frm.doc.custom_quotation_approval_link, 'Lien du BPA');
    }
    if (frm.doc.drive_url) {
        frm.add_web_link(frm.doc.drive_url, 'Lien du drive');
    }
}

function showCustomerAlerts(frm) {
    if (frm.doc.party_name) {
        frappe.db.get_value('Customer', frm.doc.party_name, 'custom_customer_alert').then(r => {
            if (r.message && r.message.custom_customer_alert) {
                frm.set_intro(`<b>Alerte client:</b> <br/> ${r.message.custom_customer_alert}`, 'yellow');
            }
        });
    }
    if (frm.doc.custom_insurance_client) {
        frappe.db.get_value('Customer', frm.doc.custom_insurance_client, 'custom_customer_alert').then(r => {
            if (r.message && r.message.custom_customer_alert) {
                frm.set_intro(`<b>Alerte assurance:</b> <br/> ${r.message.custom_customer_alert}`, 'yellow');
            }
        });
    }
}

function addSupplierQuotationButton(frm) {
    frm.add_custom_button(__('Devis fournisseur'), function(){
        frappe.call({
            method: 'new_visite_technique_from_quotation',
            args: {
                cost_center: frm.doc.cost_center,
                quotation_name: frm.doc.name,
                customer: frm.doc.party_name,
                company: frm.doc.company,
                address: frm.doc.shipping_address_name,
                project: frm.doc.project,
                project_type: frm.doc.custom_type_de_projet,
                référence_pièce: frm.doc.reference_piece,
                contact: frm.doc.contact_person,
            }
        }).then(res => {
            frappe.new_doc('Supplier Quotation', {}, sup => {
                sup.project = res.message.project;
                sup.reference_piece = frm.doc.reference_piece;
                sup.custom_devis = frm.doc.name;
                sup.items = [];
                frm.doc.items.forEach(i => {
                    if (i.row_type === '') {
                        let sup_item = frappe.model.add_child(sup, 'items');
                        Object.assign(sup_item, i);
                    }
                });
            });
        });
    }, __('Create'));
}

function addModelFromQuotationButton(frm) {
    if (frm.doc.docstatus !== 0) return;
    frm.add_custom_button(__('Modèle de devis'), function(){
        frappe.prompt({
            label: 'Modèle de devis',
            fieldname: 'devis',
            fieldtype: 'Link',
            options: 'Quotation',
            get_query: () => ({ filters: { custom_est_un_modèle_: 1 } })
        }, (values) => {
            frappe.db.get_doc('Quotation', values.devis).then(doc => {
                frm.set_value('custom_type_de_projet', doc.custom_type_de_projet);
                frm.set_value('secteur_vt', doc.secteur_vt);
                doc.items.forEach(t => frm.add_child('items', t));
                frm.refresh_field('items');
                frm.refresh();
            });
        });
    }, __('Get items from'));
}

function addProjectButtons(frm) {
    if (!frm.doc.project) return;

    frm.add_custom_button(__('📁'), function(){
        const dialog = new frappe.ui.Dialog({
            size: 'extra-large',
            title: __('Details du projet'),
            fields: [{ fieldname: 'content', fieldtype: 'HTML' }],
            primary_action: function() { frappe.set_route('Form', 'Project', frm.doc.project); },
            primary_action_label: __('Projet')
        });

        frappe.call({
            method: 'vt_internal.vt_internal.api.project_details.project_details',
            args: { project: frm.doc.project }
        }).then(r => dialog.fields_dict.content.$wrapper.html(r.message.html));

        dialog.show();
    });

    frm.add_custom_button(__('Incident qualité'), function(){
        frappe.new_doc('Quality Incident', { project: frm.doc.project });
    }, __('Create'));
}

function addVisiteTechniqueButton(frm) {
    frm.add_custom_button(__('Visite technique'), function(){
        frappe.call({
            method: 'new_visite_technique_from_quotation',
            args: {
                cost_center: frm.doc.cost_center,
                quotation_name: frm.doc.name,
                customer: frm.doc.party_name,
                company: frm.doc.company,
                address: frm.doc.shipping_address_name,
                project: frm.doc.project,
                project_type: frm.doc.custom_type_de_projet
            }
        }).then(res => {
            frm.reload_doc();
            frappe.route_options = {
                description: frm.doc.custom_environnement_du_chantier,
                projet: res.message.project,
                address: frm.doc.shipping_address_name,
                quotation: frm.doc.name,
                client: frm.doc.party_name,
                cost_center: frm.doc.cost_center,
                company: frm.doc.company
            };
            frappe.ui.form.make_quick_entry('Visite Technique', () => frm.reload_doc());
        });
    }, 'Créer');
}

function addProjectQuotationsButton(frm) {
    if (!frm.doc.project) return;
    frappe.db.get_list('Quotation', { fields: ['name'], filters: { project: frm.doc.project } })
    .then(records => {
        if (records.length > 1) {
            frm.add_custom_button(` ${records.length} devis du même projet`, function(){
                frappe.set_route('List', 'Quotation', { project: frm.doc.project });
            });
        }
    });
}

function addStatusDialogButton(frm) {
    frm.add_custom_button('Statut de suivi', () => {
        let options_statut;
        if (!frm.doc.custom_dernier_statut_de_suivi) {
            options_statut = `\nRelance automatique\nRelance manuelle\nCurieux (ne pas relancer)\nCommande à venir`;
        } else {
            options_statut = `\nRelance automatique\nRelance manuelle\nCurieux (ne pas relancer)\nAbsent - À rappeler\nProjet abandonné\nProjet perdu prix\nProjet perdu par le client\nProjet perdu délai\nEn cours\nÀ travailler\nAppel d'offre\nCommande à venir\nVariante`;
        }

        let d = new frappe.ui.Dialog({
            title: 'Mettre à jour le statut de suivi',
            fields: [
                { label: 'Nouveau statut', fieldname: 'status', fieldtype: 'Select', options: options_statut },
                { label: 'Description', fieldname: 'description', fieldtype: 'Small Text' },
                { label: 'Probabilité de conversion', fieldname: 'prob', fieldtype: 'Percent' },
                { label: 'Date de la prochaine relance manuelle', fieldname: 'followup_date', fieldtype: 'Date' }
            ],
            size: 'small',
            primary_action_label: 'Modifier',
            primary_action(values) {
                if (values.prob !== undefined && values.prob !== null) frm.set_value('custom_probabilite_de_conversion', values.prob);
                if (values.status || values.description) {
                    frm.add_child('custom_status_internes', { statut: values.status, description: values.description });
                }
                frm.set_value('custom_date_de_relance', values.followup_date);

                if (frm.doc.docstatus === 1) frm.save('Update'); else frm.save();
                d.hide();
            }
        });

        let today = frappe.datetime.get_today();
        let next_week = frappe.datetime.add_days(today, 7);
        d.fields_dict.status.df.onchange = function() {
            if (d.get_value('status') === 'Relance manuelle') d.set_value('followup_date', next_week);
        };
        d.show();
    });
}

// Main form handlers - keep concise and call helpers
frappe.ui.form.on('Quotation', {
    onload_post_render: (frm) => frm.remove_custom_button(__('Set as Lost')),

    refresh: function(frm) {
        addWebLinks(frm);
        showCustomerAlerts(frm);
        addSupplierQuotationButton(frm);
        addModelFromQuotationButton(frm);
        addProjectButtons(frm);
        addVisiteTechniqueButton(frm);
        addProjectQuotationsButton(frm);
        addStatusDialogButton(frm);

        // remove default button
        frm.remove_custom_button(__('Set as Lost'));
    },

    party_name(frm) {
        if (!frm.doc.party_name) return;
        frappe.db.get_value('Customer', frm.doc.party_name, ['custom_default_cost_center', 'mode_of_payment'])
        .then(r => {
            frm.set_value({ cost_center: r.message.custom_default_cost_center, mode_of_payment: r.message.mode_of_payment });
        });
    },

    cost_center(frm) {
        if (!frm.doc.cost_center) return;
        frappe.db.get_value('Cost Center', frm.doc.cost_center, ['custom_type_de_projet']).then(r => {
            frm.set_value({ custom_type_de_projet: r.message.custom_type_de_projet });
        });
    }
});
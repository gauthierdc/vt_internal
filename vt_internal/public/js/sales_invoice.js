// Converti depuis le Client Script ERP 'Facture de vente' (Sales Invoice / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Sales Invoice', {
	refresh(frm) {
	    if(frm.doc.custom_payment_request_link) {
	        frm.add_web_link(frm.doc.custom_payment_request_link, 'Voir le lien de paiement')
	    }
	    if(frm.doc.customer) {
            frappe.db.get_value("Customer", frm.doc.customer, "custom_customer_alert").then(r => {

                if (r.message.custom_customer_alert) {
                    frm.set_intro(`<b>Alerte client:</b> <br/> ${r.message.custom_customer_alert}`, 'yellow');
                }
            })
        }
        if(frm.doc.project) {
		    frappe.db.get_list("Quality Incident", {
                fields: ["name", "object"],
                filters: {
                    project: frm.doc.project
                }
            }).then(results => {
                if (results && results.length > 0) {
                    const links = results.map(incident => 
                        `<a href="/app/quality-incident/${incident.name}" target="_blank">${incident.object}</a>`
                    ).join(", ");
                    frm.set_intro(`<b>🛑 Ce projet fait l'objet de ${results.length} incident(s) qualité : </b>${links}`, 'red');
                }
            });
	    }
		if(frm.doc.project) {
            frm.add_custom_button(__('📁'), function(){
                const dialog = new frappe.ui.Dialog({
                    size: "extra-large",
            		title: __("Details du projet"),
            		fields: [
            			{
            				fieldname: "content",
            				fieldtype: "HTML",
            			},
            		],
            		primary_action: function () {
            			frappe.set_route('Form', "Project", frm.doc.project);
            		},
            		primary_action_label: __("Projet"),
            	});
            	
            	frappe.call({
                    method: "vt_internal.vt_internal.api.project_details.project_details",
                    args: {project: frm.doc.project}
                }).then((r) => dialog.fields_dict.content.$wrapper.html(r.message.html))
                dialog.show()
            });
            frm.add_custom_button(__('Incident qualité'), function(){
                frappe.new_doc("Quality Incident", {project: frm.doc.project})
            }, __("Create"));
        }
	}
})

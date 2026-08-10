// Converti depuis le Client Script ERP 'Factures d'achat' (Purchase Invoice / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Purchase Invoice', {
    refresh(frm) {
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
    },
})

// Converti depuis le Client Script ERP 'Incident qualité' (Quality Incident / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Quality Incident', {
    sav: function(frm) {
        frm.set_value('naming_prefix', frm.doc.sav ? 'SAV' : 'IQ');
    },
	refresh(frm) {
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
        }
        frm.add_custom_button(__('Fiche de travail'), function(){
                frappe.new_doc("Fiche de travail", {projet: frm.doc.project, quality_incident: frm.doc.name, customer: frm.doc.customer})
            }, __("Create"));
	}
})

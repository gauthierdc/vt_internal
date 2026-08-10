// Converti depuis le Client Script ERP 'Projet' (Project / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.


frappe.ui.form.on('Project', {
    onload(frm) {
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
            			frappe.set_route('Form', "Project", frm.doc.name);
            		},
            		primary_action_label: __("Projet"),
            	});
            	
            	frappe.call({
                    method: "vt_internal.vt_internal.api.project_details.project_details",
                    args: {project: frm.doc.name}
                }).then((r) => dialog.fields_dict.content.$wrapper.html(r.message.html))
                dialog.show()
            });
    },
    refresh(frm) {
        frm.add_custom_button(__('+ Visite technique'), function(){
            frappe.new_doc("Visite Technique", {projet: frm.doc.name, address: frm.doc.address, client: frm.doc.customer})
        });
        frm.add_custom_button(__('Incident Qualité'), function(){
            frappe.new_doc("Quality Incident", {projet: frm.doc.name})
        }, "+");
        
  },
  
});

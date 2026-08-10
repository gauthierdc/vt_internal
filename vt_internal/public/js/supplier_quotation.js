// Converti depuis le Client Script ERP 'Devis fournisseur' (Supplier Quotation / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Supplier Quotation', {
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
            frm.add_custom_button(__('Incident qualité'), function(){
                frappe.new_doc("Quality Incident", {project: frm.doc.project})
            }, __("Create"));
        }
	    if(frm.doc.supplier) {
            frappe.db.get_value("Supplier", frm.doc.supplier, "custom_supplier_alert").then(r => {
                
                if (r.message.custom_supplier_alert) {
                    frm.set_intro(`<b>Alerte fournisseur:</b> <br/> ${r.message.custom_supplier_alert}`, 'yellow');
                }
            })
        }
	}
})

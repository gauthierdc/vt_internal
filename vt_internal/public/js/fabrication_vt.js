// Converti depuis le Client Script ERP 'Fabrication VT' (Fabrication VT / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Fabrication VT', {
	refresh(frm) {
	    if(frm.doc.status !== "Fait") {
	        frm.add_custom_button(__('🟢'), function(){
	            var status = frm.get_field('status');
                status.set_value("Fait");
                frm.save()
            });
	    } else {
	        frm.remove_custom_button('🟢');
	    }
	    
	    frm.add_custom_button(__('Carte de travail'), function(){
	        frappe.new_doc("Carte de travail VT", {
	            status: "À faire",
	            fabrication_vt: frm.doc.name,
	            nomenclature: frm.doc.nomenclature,
	            quantity: frm.doc.quantity,
	            customer_order: frm.doc.customer_order,
	            company: frm.doc.company,
	            article: frm.doc.article,
	        },
                doc => {
                    doc.description = frm.doc.description;
                    doc.quantity = frm.doc.quantity;
                    doc.quantity = frm.doc.quantity;
                    doc.date_de_fin_prévue = frm.doc.date_de_fin_prévue;
                    
                });

        }, 'Créer');
        
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
		
	}
})

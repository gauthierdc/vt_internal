// Converti depuis le Client Script ERP 'Bon de livraison' (Delivery Note / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Delivery Note', {
    refresh: function(frm) {
        
        
        if(frm.doc.customer) {
            frappe.db.get_value("Customer", frm.doc.customer, "custom_customer_alert").then(r => {
                
                if (r.message.custom_customer_alert) {
                    frm.set_intro(`<b>Alerte client:</b> <br/> ${r.message.custom_customer_alert}`, 'yellow');
                }
            })
        }
        
        if(!frm.doc.custom_sms_sent) {
            frm.add_custom_button(__('SMS 💬'), function(){
                frappe.call({
                    method: "sms_delivery_note",
                    args: {
                        doc_name: frm.doc.name
                    }
                }).then(() => frm.reload_doc());
            });
        }
        
        if(!frm.doc.custom_signed) {
            frm.add_custom_button(__('Signer ✍️'), function(){
            frappe.prompt({
                label: 'Signature',
                fieldname: 'signature',
                fieldtype: 'Signature',
            }, (values) => {
                frm.set_value({
                    custom_signed: 1,
                    custom_signature_client: values.signature,
                    custom_livré: 1,
                    delivery_date: frappe.datetime.get_today()
                }).then(() => {
                if(frm.doc.docstatus === 1) {
                    frm.save('Update');
                } else {
                    frm.save()
                }
                })

            })
        
            });
        }
        
        if(!frm.doc.custom_livré && frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Livrer'), function(){
            frm.set_value('custom_livré', 1)
            frm.set_value('delivery_date', frappe.datetime.get_today())
            frm.save('Update');
            });
            
        }
        if(!frm.doc.custom_imprimé) {
            frm.add_custom_button(__('Imprimer'), function(){
                frm.set_value('custom_imprimé', 1)
                frm.save('Update').then(() => cur_frm.print_doc());
            
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
  custom_signature_client: (frm) => {
      frm.set_value("custom_signed", 1)
      frm.set_value("custom_livré", 1)
  },
  custom_livré: (frm) => {
      frm.set_value("delivery_date", frappe.datetime.get_today())
  }
});

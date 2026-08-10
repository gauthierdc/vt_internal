// Converti depuis le Client Script ERP 'Commande fournisseur' (Purchase Order / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

function set_shipping_from_cost_center(frm) {
    const cost_center_name = frm.doc.cost_center;
    if (!cost_center_name) return;

    frappe.db.get_value("Cost Center", cost_center_name, "custom_default_address")
    .then(r => {
        const address_name = r.message.custom_default_address;
        if (address_name) {
            frm.set_value("shipping_address", address_name);
        }
    });
}

frappe.ui.form.on('Purchase Order', {
    cost_center: function(frm) {
        set_shipping_from_cost_center(frm);
    },
    onload_post_render: function(frm) {
        set_shipping_from_cost_center(frm);
    },
    supplier: function(frm) {
        // Rafraîchir le champ contact_person quand on change de fournisseur
        frm.set_query('contact_person', () => {
            return {
                filters: {
                    link_doctype: 'Supplier',
                    link_name: frm.doc.supplier
                }
            };
        });

/*        // Optionnel : Effacer le contact si le fournisseur change
        frm.set_value('contact_person', null);*/
    },
    
	refresh(frm) {
	    
	    if(frm.doc.supplier) {
            frappe.db.get_value("Supplier", frm.doc.supplier, "custom_supplier_alert").then(r => {
                
                if (r.message.custom_supplier_alert) {
                    frm.set_intro(`<b>Alerte fournisseur:</b> <br/> ${r.message.custom_supplier_alert}`, 'yellow');
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
        frm.add_custom_button(__('Incident qualité'), function(){
            frappe.new_doc("Quality Incident", {project: frm.doc.project, origine: "Fournisseur", purchase_order: frm.doc.name})
        }, __("Create"));
	    
	    
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
        
        if(!frm.doc.custom_ar_validé) {
            frm.add_custom_button(__("AR"), function(){
                frm.set_value('custom_ar_validé', 1);
                frm.save('Update')
            }, "Statut");
            
        }
        
        if(frm.doc.custom_ar_validé === 1 && frm.doc.per_received === 100 && frm.doc.per_billed < 100) {
            frm.add_custom_button(__("🛒"), function(){
                frappe.call({
                    method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
                    args: {
                        source_name: frm.doc.name
                    },
                    callback: function(r) {
                        frappe.call({
                            method: 'frappe.client.submit',
                            args: {
                                doc: r.message,
                            },
                            callback: function(r) {
                                cur_list.refresh()
                            }
                        });
                    }
                });
            });
        }
        
        if(frm.doc.custom_ar_validé === 0) {
            frm.add_custom_button(__("✅ AR"), function(){
                frm.set_value("custom_ar_validé", 1)
                frm.save('Update');
            });
            
        }
        if(frm.doc.per_received < 100) {
            frm.add_custom_button(__("📥"), function(){
            frappe.call({
                method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
                args: {
                    source_name: cur_frm.doc.name
                },
                callback: function(r) {
                    frappe.call({
                        method: 'frappe.client.submit',
                        args: {
                            doc: r.message,
                        },
                        callback: function(r) {
                            frm.reload_doc();
                        }
                    });
                }
            });
            });
        }
        
	}
})

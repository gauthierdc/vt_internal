// Converti depuis le Client Script ERP 'Demande d'extraction de donnée via OCR' (OCR Request / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('OCR Request', {
	refresh(frm) {
	    if(frm.doc.supplier) {
            frappe.db.get_value("Supplier", frm.doc.supplier, "custom_supplier_alert").then(r => {
                
                if (r.message.custom_supplier_alert) {
                    frm.set_intro(`<b>Alerte fournisseur:</b> <br/> ${r.message.custom_supplier_alert}`, 'yellow');
                }
            })
        }
	    
	    
		frappe.db.get_value("Purchase Order", {
		    supplier: frm.doc.supplier,
		    grand_total: frm.doc.grand_total,
		    docstatus: ['!=', 2],
		    ocr_request: ["is", 'not set'],
		}, ["name"]).then(r => {
		    console.log(r, {
		    supplier: frm.doc.supplier,
		    grand_total: frm.doc.grand_total,
		    ocr_request: ["is", 'not set'],
		})
		    if(r.message.name) {
		        frm.add_custom_button(`Lier à ${r.message.name}`, () => {
    		        frappe.call({
    					method: "link_to_purchase_order",
    					doc: frm.doc,
    					args: {
    						orders: [r.message.name]
    					}
    				}).then(() => {
    					frm.events.trigger_purchase_invoice_creation(frm, [r.message.name])
    				})
    
    		    })
		    }
		    
		})
	}
})

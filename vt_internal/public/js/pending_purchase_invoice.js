// Converti depuis le Client Script ERP 'Facture d'achat en attente' (Pending Purchase Invoice / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Pending Purchase Invoice', {
    refresh(frm) {
            
        if(frm.doc.supplier) {
            frappe.db.get_value("Supplier", frm.doc.supplier, "custom_supplier_alert").then(r => {
                
                if (r.message.custom_supplier_alert) {
                    frm.set_intro(`<b>Alerte fournisseur:</b> <br/> ${r.message.custom_supplier_alert}`, 'yellow');
                }
            })
        }
        
        if (frm.doc.bill_no && frm.doc.supplier) {
            frappe.db.get_value('Purchase Invoice', { bill_no: frm.doc.bill_no, supplier: frm.doc.supplier }, ['name', 'supplier', 'posting_date'])
            .then(r => {
                const invoice = r.message;

                // Si on a trouvé UNE facture
                if (invoice && invoice.name) {
                    const link = `<a href="/app/purchase-invoice/${invoice.name}" target="_blank">${invoice.name}</a>`;
                    const msg = `⚠️ Ce numéro de facture fournisseur (<b>${frm.doc.bill_no}</b>) existe déjà dans la facture ${link}.`;

                    frm.set_intro(msg, 'red');
                }
            });
        }


            
        if (!frm.doc.supplier || frm.doc.supplier_grand_total === 0) return;
        
        frappe.db.get_value("Purchase Order", {
		    supplier: frm.doc.supplier,
		    grand_total: frm.doc.supplier_grand_total,
		    company: frm.doc.company,
		    status: ["!=", "Completed"],
		    docstatus: ['!=', 2],
		    ocr_request: ["is", 'not set'],
		}, ["name", "status", "custom_acheteur", "project"]).then(r => {
		    console.log(r, {
		    supplier: frm.doc.supplier,
		    grand_total: frm.doc.supplier_grand_total,
		    company: frm.doc.company,
		    ocr_request: ["is", 'not set'],
		})
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
		    
		    const isAlreadyLinked = frm.doc.items.map(i=>i.reference_docname).includes(r.message.name)
		    if(r.message.name) {
	            const link = `<a href="/app/purchase-order/${r.message.name}" target="_blank">${r.message.name}</a>`;
	            const status = __(r.message.status)
                const msg = `✅ Une commande fournisseur  au statut <b>${status}</b> de <i>${r.message.custom_acheteur}</i> du même montant TTC et du même fournisseur a été trouvé <b>${link}.</b>`;
                frm.set_intro(msg, 'yellow');
                if(!isAlreadyLinked) {
                
    		        frm.add_custom_button(`Lier à ${r.message.name}`, () => {
        		        frappe.call({
                            method: "get_document_item_lines",
                            doc: cur_frm.doc,
                            args: {
                                doctype: "Purchase Order",
                                selected_documents: [r.message.name],
                                allow_child_item_selection: false,
                                filtered_line_items: []
                            },
                            callback: function(r) {
                                if (r.message && r.message.items) {
                                    frm.clear_table("items");
                                    // Ajoute les lignes à ta facture en attente
                                    r.message.items.forEach(r => {
                                        const child = cur_frm.add_child("items", {
                        					reference_doctype: "Purchase Order",
                        					reference_docname: r.parent,
                        					row: r.name,
                        					project: r.project,
                        					cost_center: r.cost_center,
                        					price: r.price,
                        					item_code: r.item_code,
                        					rate: r.rate,
                        					qty: r.qty,
                        					amount: r.amount,
                        					expense_account: r.expense_account,
                        					description: r.description,
                        			    }
                                );
                                    });
                                    frm.refresh_field("items");
                                    frm.save().then(() => {
                                        frm.events.create_purchase_invoice(frm, true)
                                        console.log("HEYY")
                                    });
                                    console.log("📢 Ceci s'affiche avant la fin de la sauvegarde");
                                    
                                    
                                }
                            }
                        });
        
        		    })
                }

		    }
		    
		})
    }
});

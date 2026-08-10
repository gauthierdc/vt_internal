// Converti depuis le Client Script ERP 'Ordre de paiement' (Payment Order / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Payment Order', {
	refresh(frm) {
		frm.add_custom_button(__("Facture d'achat automatique"), function(){
		    frm.set_value('references', [])
		    let today = new Date();
            // Ajouter 15 jours à la date d'aujourd'hui
            today.setDate(today.getDate() + 15);
            const formattedDate = `${today.getMonth() + 1}-${today.getDate()}-${today.getFullYear()}`
            console.log(formattedDate)
            frappe.db.get_list('Purchase Invoice', {
                fields: ['name', 'outstanding_amount', 'supplier', 'due_date'],
                filters: {
                    company: frm.doc.company,
                    docstatus: 1,
                    outstanding_amount: [">", 0],
                    custom_mode_of_paiement: "Virement",
                    due_date: ["<", formattedDate]
                },
                limit:300
            }).then(records => {
                console.log(records)
                frm.set_value('payment_order_type', 'Purchase Invoice')
                records.forEach(p => {
                    frappe.db.get_value("Supplier", p.supplier, "default_bank_account").then(s=> {
                        frm.add_child('references', {
                            reference_doctype: 'Purchase Invoice',
                            reference_name: p.name,
                            amount: p.outstanding_amount,
                            supplier: p.supplier,
                            custom_due_date: p.due_date,
                            bank_account: s.message.default_bank_account,
                        });
                        frm.refresh_field('references');
                    })
                    
                })
                
                frm.refresh_field('references');
            })

	}, __("Obtenir les paiements depuis"))
	   
}
    
})

// Converti depuis le Client Script ERP 'Transaction bancaire' (Bank Transaction / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Bank Transaction', {
	refresh(frm) {
		frm.add_custom_button(__('Créer une dépense'), function(){
		    if(!frm.doc.party) {
		        frappe.throw(__("Ajoutez un tiers à la transaction"))
		    }
            frappe.new_doc("Expense", {
                expense_date: frm.doc.date,
                employee: frm.doc.party,
                custom_bank_transaction: frm.doc.name,
                
            })
        }, "Actions");
        
	}
})

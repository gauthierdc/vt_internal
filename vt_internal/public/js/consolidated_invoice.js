// Converti depuis le Client Script ERP 'Facture consolidée' (Consolidated invoice / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Consolidated invoice', {
	refresh(frm) {
		frm.add_custom_button('Génerer les factures', function(){
		    frappe.call({
                method: "generate_consolidate_sales_invoice",
            }).then((r) => {
                frappe.show_alert({
                message:__('5 factures générés'),
                indicator:'green'
            }, 5);
            })
        });
	}
})

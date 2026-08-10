// Converti depuis le Client Script ERP 'Reçu d'achat' (Purchase Receipt / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Purchase Receipt', {
	refresh(frm) {
		 if(frm.doc.project) {
            frm.add_custom_button(__('📁'), function(){
                frappe.set_route('Form', "Project", frm.doc.project)
            });
        }
	}
})

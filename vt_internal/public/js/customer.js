// Converti depuis le Client Script ERP 'Client' (Customer / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Customer', {
	refresh(frm) {
		frm.add_custom_button(__('Incident qualité'), function(){
            frappe.new_doc("Quality Incident", {customer: frm.doc.name})
        }, __("Create"));
	}
})

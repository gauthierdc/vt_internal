// Converti depuis le Client Script ERP 'Feuille de temps' (Timesheet / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Timesheet', {
	refresh(frm) {
		// your code here
	}
})

frappe.ui.form.on('Timesheet Detail', {
    custom_fiche_de_travail(frm, cdt, cdn) {
        const ft = frappe.model.get_value("Timesheet Detail", cdn, "custom_fiche_de_travail")
        if (ft) {
            frappe.db.get_value("Fiche de travail", ft, "projet").then(r => frappe.model.set_value("Timesheet Detail", cdn, "project", r.message.projet))
        }
    
    }
    
});

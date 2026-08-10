// Converti depuis le Client Script ERP 'Prix de forme' (VT Prix De Forme / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('VT Prix De Forme', {
	refresh(frm) {
		frm.add_custom_button(__('Autres prix'), function(){
		    window.location.href = "/app/query-report/" + "Prix des formes aide?prix_de_forme=" + frm.doc.name;

		    //window.location.href = "google.com"
		    //window.location.href = window.location.hostname + "/app/query-report/" + "Prix des formes aide?forme=" + frm.doc.name
        });
	}
})

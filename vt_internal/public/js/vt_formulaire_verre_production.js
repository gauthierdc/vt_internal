// Converti depuis le Client Script ERP 'VT Formulaire Verre Production' (VT Formulaire Verre Production / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('VT Formulaire Verre Production', {
	refresh(frm) {
	    console.log("HEYYY")
		verre: () => {
		    frm.add_child('operations', {
                forme: 'Forme A',
            });
            console.log("HEYYY")
		    frm.refresh_field('operations');
		}
	}
})

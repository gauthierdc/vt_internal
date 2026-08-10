// Converti depuis le Client Script ERP 'Paramètres BMV' (BMV settings / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('BMV settings', {
	refresh(frm) {
		frm.add_custom_button('Mettre à jour les prix', function(){
		    frappe.call({
                method: "update_bmv_prices",
                args: {
                    prix_du_m_13_mm: frm.doc.prix_du_m_13_mm,
                    prix_du_m_16_mm: frm.doc.prix_du_m_16_mm,
                    prix_du_m_99_mm: frm.doc.prix_du_m_99_mm,
                }
            }).then(() => {
                frappe.show_alert({
                message:__('Prix mis à jour'),
                indicator:'green'
            }, 5);
            })
        });
	}
})

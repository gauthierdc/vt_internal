// Converti depuis le Client Script ERP 'Objectif VT' (VT Objective / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('VT Objective', {
    refresh(frm) {
        frm.add_custom_button(__('Compléter le tableau'), function() {
            let details_table = frm.doc.details;
            
            if (details_table.length === 0) {
                frappe.msgprint(__('Le tableau est vide, impossible de dupliquer une ligne.'));
                return;
            }
            
            let last_row = details_table[details_table.length - 1];
            
            while (frm.doc.details.length < 52) {
                let new_row = frm.add_child('details');
                Object.assign(new_row, last_row);
                new_row.idx = frm.doc.details.length; // Réassigner un numéro unique de ligne
                new_row.week = frm.doc.details.length; // Réassigner un numéro unique de ligne
            }
            
            frm.refresh_field('details');
        });
    }
});

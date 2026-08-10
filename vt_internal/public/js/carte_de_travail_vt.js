// Converti depuis le Client Script ERP 'Carte de travail' (Carte de travail VT / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Carte de travail VT', {
	refresh(frm) {
	    console.log(frm.doc.status)
	    if(frm.doc.status !== "Fait") {
	        frm.add_custom_button(__('🟢'), function(){
	            var status = frm.get_field('status');
                status.set_value("Fait");
                frm.save()
            });
	    } else {
	        frm.remove_custom_button('🟢');
	    }
		
	}
})
/*
frappe.ui.form.on('Carte de travail VT', {
	refresh(frm) {
	    frm.add_custom_button('Scanner', function(){
            new frappe.ui.Scanner({
          dialog: true, // open camera scanner in a dialog
          multiple: true, // stop after scanning one value
          on_scan(data) {
            console.log(data.decodedText);
            frappe.db.set_value('Carte de travail VT', data.decodedText, 'status', 'Fait')
            .then(r => {
                let doc = r.message;
                console.log(doc);
            })
            frappe.show_alert({
                message:__(data.decodedText),
                indicator:'green',
                
            }, 1);
          }
        });
        });
		
	}
})*/

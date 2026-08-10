// Converti depuis le Client Script ERP 'Facture d'achat en attente liste' (Pending Purchase Invoice / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.listview_settings['Pending Purchase Invoice'] = frappe.listview_settings['Pending Purchase Invoice'] || {};


Object.assign(frappe.listview_settings['Pending Purchase Invoice'], {
    has_indicator_for_draft: true,
/*	get_indicator: function (doc) {
	    return ["À programmer", "rouge", "status,=,À programmer"]
	    
	},*/
	onload: function (list_view) {
		list_view.columns?.push({
			type: "Field",
			df: {
                label: __("Created On"),
                fieldname: "creation",
                fieldtype: "Date",
              },
		});

		list_view.refresh(true)
	}
})

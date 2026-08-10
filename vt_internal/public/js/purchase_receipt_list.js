// Converti depuis le Client Script ERP 'Reçu d'achat liste' (Purchase Receipt / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

Object.assign(frappe.listview_settings['Purchase Receipt'], {
    add_fields: ['project'],
    	button: {
	    show: (doc) => {
	      return doc.project
	    },
		get_description: (doc) => {
			return `${doc.project}`
		},
		get_label: () => {
			return "📁"
		},
		action: (doc) => {
		    frappe.set_route('Form', "Project", doc.project)
		}
	}
})

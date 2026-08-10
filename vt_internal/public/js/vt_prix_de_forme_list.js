// Converti depuis le Client Script ERP 'Prix de forme liste' (VT Prix De Forme / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.listview_settings['VT Prix De Forme'] = {
    add_fields: ['customer', 'territory', 'price_list'],
    	button: {
	    show: (doc) => {
	      return !doc.customer && (doc.territory === "PARTICULIER - A" || !doc.territory) && (doc.price_list === "Vente Standard" || doc.price_list === "Achat Standard")
	    },
		get_description: (doc) => {
			return "🔗"
		},
		get_label: () => {
			return "🔗"
		},
		action: (doc) => {
		    window.location.href = "/app/query-report/" + "Prix des formes aide?prix_de_forme=" + doc.name;
		}
	},
    
}

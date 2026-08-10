// Converti depuis le Client Script ERP 'Bon pour accord liste' (Quotation Approval / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.listview_settings['Quotation Approval'] = {
	hide_name_column: true, // this part
	get_indicator: function (doc) {
	    if(doc.refusal_reason) return ["Refusé", "red", "refusal_reason,is,set"]
	    else return ["Accepté", "green", "refusal_reason,is,not set"]
	    
	    
	},
}

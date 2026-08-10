// Converti depuis le Client Script ERP 'Fiche de travail liste' (Fiche de travail / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.listview_settings['Fiche de travail'] = {
	hide_name_column: true, // this part
	add_fields: ['calendar_description', 'work_completion_receipt_signed'],
	has_indicator_for_draft: true,
	get_indicator: function (doc) {
	    if(doc.work_completion_receipt_signed) return ["Réceptionné", "green", "work_completion_receipt_signed,=,1"]
	    if(doc.status === "Fait") return ["Fait", "blue", "status,=,Fait"]
	    if(doc.status === "À faire") return ["À faire", "orange", "status,=,À faire"]
	    if(doc.status === "En cours") return ["En cours", "purple", "status,=,En cours"]
	    if(doc.status === "À planifier") return ["À planifier", "yellow", "status,=,À planifier"]
	    if(doc.status === "En attente de fabrication") return ["En attente de fabrication", "gray", "status,=,En attente de fabrication"]
	    if(doc.status === "À programmer") return ["À programmer", "rouge", "status,=,À programmer"]
	    
	},
}

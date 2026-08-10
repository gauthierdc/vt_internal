// Converti depuis le Client Script ERP 'Client liste' (Customer / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.


Object.assign(frappe.listview_settings['Customer'], {
    add_fields: ["custom_internal_status"],
    has_indicator_for_draft: true,
    get_indicator(doc) {
        if(doc.custom_internal_status === "En compte") {
            return ["En compte", "purple", "custom_internal_status,=,En compte"]
        }
        if(doc.custom_internal_status === "Ponctuel") {
            return ["Ponctuel", "gray", "custom_internal_status,=,Ponctuel"]
        }
        if(doc.custom_internal_status === "Récurrent") {
            return ["Récurrent", "blue", "custom_internal_status,=,Récurrent"]
        }
        if(doc.custom_internal_status === "Prescripteur") {
            return ["Prescripteur", "yellow", "custom_internal_status,=,Prescripteur"]
        }
        if(doc.custom_internal_status === "Prospect") {
            return ["Prospect", "orange", "custom_internal_status,=,Prospect"]
        }
        if(doc.custom_internal_status === "Bloqué") {
            return ["Bloqué", "darkgray", "custom_internal_status,=,Bloqué"]
        }
        if(doc.custom_internal_status === "Désactivé") {
            return ["Désactivé", "darkgray", "custom_internal_status,=,Désactivé"]
        }
}
})

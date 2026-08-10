// Converti depuis le Client Script ERP 'Ticket liste' (Issue / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

 const standard_indicator = frappe.listview_settings['Issue'].get_indicator 

 Object.assign(frappe.listview_settings['Issue'], {
    add_fields: ['custom_inactive'],

     get_indicator(doc) {
        if(doc.custom_inactive) {
            return [__("Inactif"), "gray", "custom_inactive,=,1"]
        } else if(doc.status === "Open") {
            return [__("Open"), "red", "status,=,Open|custom_inactive,=,0"]
        }
        return standard_indicator(doc)
    },
 })

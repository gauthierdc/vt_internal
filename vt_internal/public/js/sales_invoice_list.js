// Converti depuis le Client Script ERP 'Facture de vente liste' (Sales Invoice / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

 const standard_indicator = frappe.listview_settings['Sales Invoice'].get_indicator 

 Object.assign(frappe.listview_settings['Sales Invoice'], {
    add_fields: ['custom_disputed', "custom_déposé_sur_chorus", "custom_rg"],

     get_indicator(doc) {
        if(doc.status === "Paid") {
            return standard_indicator(doc)
        }
        if (doc.custom_disputed) {
            return [__("En litige"), "purple", "custom_disputed,=,1|status,!=,Paid|docstatus,=,1"]
        }
        if (doc.custom_déposé_sur_chorus) {
            return [__("Déposé sur chorus"), "yellow", "custom_déposé_sur_chorus,=,1|status,!=,Paid|docstatus,=,1"]
        }
        if (doc.custom_rg) {
            return [__("RG"), "yellow", "custom_rg,=,1|status,!=,Paid|docstatus,=,1"]
        }
        return standard_indicator(doc)
    },
 })

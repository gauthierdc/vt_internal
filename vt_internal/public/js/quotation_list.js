const original_indicator = frappe.listview_settings['Quotation'].get_indicator
const original_onload = frappe.listview_settings['Quotation'].onload

Object.assign(frappe.listview_settings['Quotation'], {
    add_fields: ["custom_visite_technique_status", "custom_signature", "custom_dernier_statut_de_suivi", "status"],
    has_indicator_for_draft: true,
    get_indicator(doc) {
        const oi = original_indicator(doc)
        if (doc.status?.includes("dered")) return oi
        if(doc.status === "Lost") {
            return [__("Lost"), "darkgrey", `status,=,Lost`];
        }
        if(doc.custom_dernier_statut_de_suivi === "Curieux (ne pas relancer)") {
            return [__("Curieux"), "darkgrey", "custom_dernier_statut_de_suivi,=,Curieux (ne pas relancer)|status,not in,Ordered,Lost,Partially Ordered,Cancelled"];
        }
        if(doc.custom_dernier_statut_de_suivi === "Variante") {
            return [__("Variant"), "yellow", "custom_dernier_statut_de_suivi,=,Variante"];
        }
        if(doc.custom_visite_technique_status === "À faire") {
            return [__("VT à faire"), "blue", "custom_visite_technique_status,=,À faire|status,not in,Ordered,Lost,Partially Ordered,Cancelled|docstatus,!=,2"];
        }
        if(doc.custom_signature) {
            return [__("Bon pour accord"), "purple", "custom_quotation_approval_description,is,set|status,not in,Ordered,Lost,Partially Ordered,Cancelled|docstatus,!=,2"];
        }
        if(doc.custom_dernier_statut_de_suivi === "Relance automatique") {
            return [__("🕘 Relance automatique"), "yellow", "custom_dernier_statut_de_suivi,=,Relance automatique|status,not in,Ordered,Lost,Partially Ordered,Cancelled|docstatus,!=,2"];
        }

        if(doc.custom_dernier_statut_de_suivi === "Commande à venir") {
            return [__("Commande à venir"), "cyan", "custom_dernier_statut_de_suivi,=,Commande à venir|status,not in,Ordered,Lost,Partially Ordered,Cancelled|docstatus,!=,2"];
        }
        
        if(doc.custom_dernier_statut_de_suivi) {
            return [doc.custom_dernier_statut_de_suivi, "orange", `custom_dernier_statut_de_suivi,=,${doc.custom_dernier_statut_de_suivi}|status,not in,Ordered,Lost,Partially Ordered,Cancelled|docstatus,!=,2`];
        }

/*        if(doc.docstatus === 0) {
            return [__("Draft"), "orange", `docstatus,=,0`]
        }*/
        
        if(!doc.custom_dernier_statut_de_suivi) {
            return [__("Draft"), "grey", `custom_dernier_statut_de_suivi,is,not set|status,not in,Ordered,Lost,Partially Ordered,Cancelled|custom_quotation_approval_description,is,not set|custom_visite_technique_status,is,not set`];
        }
        return oi

    },
    onload: function (list_view) {
        original_onload(list_view)
        //list_view.page.fields_dict.quotation_to.set_value("Customer")

	},
	refresh: function (list_view) {
		//list_view.page.fields_dict.quotation_to.set_value("Customer")
	},
})
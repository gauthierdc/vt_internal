// Converti depuis le Client Script ERP 'Commande client liste' (Sales Order / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

const standard_indicator = frappe.listview_settings['Sales Order'].get_indicator 
Object.assign(frappe.listview_settings['Sales Order'], {
    add_fields: ['custom_statut_fiche_de_travail', 'advance_paid', 'per_billed', 'customer_name', 'custom_per_received', 'created_by', 'per_delivered', 'per_billed', 'customer_name', 'contact_mobile', 'custom_payment_request_status'],
    //hide_name_column: true, 
    // hide the last column which shows the `name` 
    //hide_name_filter: true, 
    formatters: {
/*        custom_responsable_du_devis(val) {
            console.log(`${window.location.host}?custom_responsable_du_devis=${val}`) 
            if (val === frappe.session.user) {
                return `<span style="background-color: lavender">${val}</span>`
            } else return `<span>${val}</span>`
        },*/
    },
    get_indicator(doc) {
        if (doc.per_billed === 100) {
            return [__("Terminé"), "green", "per_billed,=,100"]
        }
        if (doc.status === "On Hold" || doc.status === "Closed" || doc.per_billed === 100) {
            return standard_indicator(doc)
        }
        if (doc.custom_payment_request_status === "Requested") {
            return [__("🕦 Acompte"), "gray", "custom_payment_request_status,=,Requested"]
        }
        if (doc.per_delivered > 0 && doc.per_billed < 100 && !doc.custom_statut_fiche_de_travail) {
            return [__("En BL"), "red", "per_delivered,>,0|custom_statut_fiche_de_travail,is,not set|per_billed,<,100|docstatus,=,1"];
        }
        if (doc.custom_statut_fiche_de_travail === "À faire" && doc.per_billed < 100) {
            return [__("Chantier à faire"), "orange", "custom_statut_fiche_de_travail,=,À faire|per_billed,<,100"];
        }
        if (doc.custom_statut_fiche_de_travail === "En cours" && doc.per_billed < 100) {
            return [__("Chantier en cours"), "purple", "custom_statut_fiche_de_travail,=,En cours|per_billed,<,100"];
        }
        if (doc.custom_statut_fiche_de_travail === "À planifier" && doc.per_billed < 100) {
            return [__("Chantier à planifier"), "pink", "custom_statut_fiche_de_travail,=,À planifier|per_billed,<,100"];
        }
        if (doc.custom_per_received > 0 && doc.custom_per_received < 100) {
            return [__("En fabrication"), "yellow", "custom_per_received,>,1|custom_per_received,<,100|docstatus,=,1|status,!=,In Hold|per_delivered,=,0|per_billed,=,0"];
        }
        if (doc.custom_per_received === 100 && doc.per_delivered === 0 && doc.per_delivered === 0 && !doc.custom_statut_fiche_de_travail) {
            return [__("À livrer"), "blue", "custom_per_received,=,100|per_delivered,=,0|per_billed,=,0|custom_statut_fiche_de_travail,is,not set|docstatus,=,1"];
        }
        if (doc.per_delivered < 100 && doc.per_billed < 100 && doc.custom_statut_fiche_de_travail === "Fait" ) {
            return [__("CH fait à facturer"), "red", "per_delivered,<,100|per_billed,<,100|custom_statut_fiche_de_travail,=,Fait|docstatus,=,1"];
        }
        if (doc.custom_per_received === 0) {
            return [__("À fabriquer"), "green", "custom_per_received,<,1|per_delivered,<,1|per_billed,<,1|docstatus,=,1|status,!=,On Hold|custom_statut_fiche_de_travail,!=,À faire|custom_statut_fiche_de_travail,!=,Fait"];
        }
        if (doc.per_delivered > 0) {
            return standard_indicator(doc)
        }
        return standard_indicator(doc)
    },
    
    button: {
        show: (doc) => {
            return (doc.custom_per_received === 100 || doc.custom_statut_fiche_de_travail  === "Fait") && doc.per_delivered === 0
        },
        get_description: (doc) => {
            return "Créer un BL et envoyer un SMS"
        },
        get_label: (doc) => {
            return "🚐"
        },
        action: (doc) => {
            frappe.call({
                    method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
                    args: {
                        source_name: doc.name
                    },
                    callback: function(r) {
                        frappe.call({
                            method: 'frappe.client.submit',
                            args: {
                                doc: r.message,
                            },
                            callback: function(r_bl) {
                                console.log(r_bl.message)
                                cur_list.refresh()
                                
                        
                            }
                        });
                    }
                });
        }
    },
})

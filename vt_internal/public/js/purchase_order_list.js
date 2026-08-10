// Converti depuis le Client Script ERP 'Commande fournisseur liste' (Purchase Order / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

const standard_indicator = frappe.listview_settings['Purchase Order'].get_indicator 
Object.assign(frappe.listview_settings['Purchase Order'], {
    

    add_fields: ['custom_ar_validé', 'per_received', 'per_billed', 'custom_acheteur', 'ocr_request'],
    get_indicator(doc) {
        if(doc.status === "Closed") return standard_indicator(doc) 
        if (doc.ocr_request && doc.per_billed === 0 && doc.custom_acheteur && !doc.custom_ar_validé) {
            return [__("OCRisé à valider"), "purple", "ocr_request,is,set|per_billed,=,0|custom_acheteur,is,set|custom_ar_validé,=,0|docstatus,!=,2|status,!=,Closed"]
        }
        if (!doc.custom_ar_validé && doc.per_received === 0 && doc.per_billed === 0) {
            return [__("AR à valider"), "yellow", "custom_ar_validé,=,0"]
        }
        if (doc.ocr_request && doc.per_received === 100 && doc.per_billed === 0) {
            return [__("OCRisé à facturer"), "purple", "ocr_request,is,set|per_received,=,100|per_billed,=,0|status,!=,Closed"]
        }
        if (doc.ocr_request && doc.per_received === 0 && doc.per_billed === 0) {
            return [__("OCRisé à receptionner"), "purple", "ocr_request,is,set|per_received,=,0|per_billed,=,0|status,!=,Closed|docstatus,!=,2|custom_ar_validé,=,1"]
        }
        return standard_indicator(doc)
    },
    button: {
        show: (doc) => {
            return (doc.per_received === 0 || doc.per_billed === 0) && doc.docstatus === 1 && doc.custom_ar_validé
        },
        get_description: (doc) => {
            return doc.per_received === 0 && "Tout réceptionner" || "Facturer"
        },
        get_label: (doc) => {
            return doc.per_received === 0 && "📥" || "🛒"
        },
        action: (doc) => {
            if (doc.per_received === 0) {
                frappe.call({
                    method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
                    args: {
                        source_name: doc.name
                    },
                    callback: function(r) {
                        frappe.call({
                            method: 'frappe.client.submit',
                            args: {
                                doc: r.message,
                            },
                            callback: function(r) {
                                cur_list.refresh()
                            }
                        });
                    }
                });
            } else {
                frappe.call({
                    method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
                    args: {
                        source_name: doc.name
                    },
                    callback: function(r) {
                        frappe.call({
                            method: 'frappe.client.submit',
                            args: {
                                doc: r.message,
                            },
                            callback: function(r) {
                                cur_list.refresh()
                            }
                        });
                    }
                });
            }
        }
    }
})

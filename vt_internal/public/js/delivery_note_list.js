// Converti depuis le Client Script ERP 'Bon de livraison liste' (Delivery Note / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

const standard_indicator = frappe.listview_settings['Delivery Note'].get_indicator


Object.assign(frappe.listview_settings['Delivery Note'], {
    add_fields: ['project', 'contact_mobile', 'company', 'custom_livré', 'customer_name', 'per_billed', 'custom_sms_sent', 'reference_piece', 'custom_signed'],
/*    hide_name_column: true, // hide the last column which shows the `name`
    hide_name_filter: true,*/
    
    formatters: {
        custom_imprimé(val, t, doc) {
            return val && doc.custom_signed && "🖨 ✍️" || val && "🖨" || doc.custom_signed && "✍️" || ""
        },
    },
    
    button: {
	    show: (doc) => {
	      return (doc.custom_sms_sent === 0 || doc.custom_signed === 0) && !doc.custom_livré && doc.docstatus != 2
	    },
		get_description: (doc) => {
			return doc.custom_sms_sent === 0 ? "SMS" : "✍️"
		},
		get_label: (doc) => {
			return doc.custom_sms_sent === 0 ? "SMS" : "✍️"
		},
		action: (doc) => {
		    if(!doc.custom_sms_sent) {
		        frappe.call({
                    method: "sms_delivery_note",
                    args: {
                        doc_name: doc.name
                    }
                }).then(() => cur_list.refresh())
		    } else {
		        frappe.prompt({
                label: 'Signature',
                fieldname: 'signature',
                fieldtype: 'Signature',
            }, (values) => {
                frappe.db.set_value("Delivery Note", doc.name, {
                    custom_signature_client: values.signature,
                    custom_signed: 1,
                    custom_livré: 1,
                    delivery_date: frappe.datetime.get_today()
                }).then(() => {
                    cur_list.refresh()
                    frappe.show_alert({message: 'Signature ajoutée', indicator: 'green'}, 5)
                })
            })
		    }
		  
		}
	},
	
	get_indicator(doc) {
	    if(doc.status === "Closed") {
	        return standard_indicator(doc)
	    }
        if(!doc.custom_livré) {
            return [__("À livrer"), "purple", "custom_livré,=,0|status,!=,Closed|docstatus,=,1"]
        }
        
        if(doc.custom_livré && doc.customer_name?.includes("*") && doc.per_billed < 90 && doc.status != "Closed") {
            return [__("EC À facturer"), "green", "customer_name,like,*|custom_livré,=,1|per_billed,<,90|docstatus,=,1|status,!=,Closed"]
        }
        
        if(doc.per_billed < 90) {
            return [__("À Facturer"), "orange", "status,!=,Closed|docstatus,=,1|custom_livré,=,1|per_billed,<,90|customer_name,not like,*"]
        }
        
        return standard_indicator(doc)
    },
    
})

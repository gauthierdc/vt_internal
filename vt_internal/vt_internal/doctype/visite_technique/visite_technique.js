// Copyright (c) 2025, Verre & Transparence and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Visite Technique", {
// 	refresh(frm) {

// 	},
// });

const timer_api = (args, message) => {
    return frappe.call({
        method: "timesheet_post_api",
        args
    }).then(() => {
        frappe.show_alert({message: message, indicator: 'green'}, 5)
        location.reload()
    })
}

frappe.ui.form.on('Visite Technique', {
    refresh: function(frm) {
        if(frm.doc.quotation) {
            frappe.db.get_value('Quotation', frm.doc.quotation, 'custom_quotation_approval_link').then(r => {
                frm.add_web_link(r.message.custom_quotation_approval_link, 'Voir le lien du BPA')
            })
        }
        frappe.call({
            method: "timesheet_html_block",
        }).then((r) => {
            console.log(r.message)
            const m = r.message
            
            if(r.message.current_task !== "Atelier" && r.message.current_task !== "Day finished") {
                frm.add_custom_button(__("🏠 Démarrer le chronomètre de l'atelier"), function(){
                    timer_api({
                        action: "start_construction",
                        activity_type: 'Atelier'
                    }, 'Tâche commencée')
                }, '⏱️');
            }
            if(r.message.current_task !== "Visite technique" && r.message.current_task !== "Day finished") {
                frm.add_custom_button(__("📋 Commencer une visite technique"), () => {
                    timer_api({
                        action: "start_construction",
                        activity_type: 'Visite technique'
                    }, 'Pause commencée')
                }, '⏱️')
            }
            if(r.message.current_task !== "Pause" && r.message.current_task !== "Day finished" && r.message.current_task !== "Day not started") {
                frm.add_custom_button(__("⏸️ Faire une pause"), () => {
                    timer_api({
                        action: "start_break",
                        fiche_de_travail: frm.doc.name,
                    }, 'Pause commencée')
                }, '⏱️')
            }
            if(r.message.current_task !== "Day not started" && r.message.current_task !== "Day finished") {
                frm.add_custom_button("⏹️ Terminer la journée",() => {
                    timer_api({
                        action: "stop_day",
                    }, 'Journée terminée')
                }, '⏱️');
            }
            
        })
        if(frm.doc.projet) {
            frm.add_custom_button(__('📁'), function(){
                const dialog = new frappe.ui.Dialog({
                    size: "extra-large",
            		title: __("Details du projet"),
            		fields: [
            			{
            				fieldname: "content",
            				fieldtype: "HTML",
            			},
            		],
            		primary_action: function () {
            			frappe.set_route('Form', "Project", frm.doc.projet);
            		},
            		primary_action_label: __("Projet"),
            	});
            	
            	frappe.call({
                    method: "project_details",
                    args: {project: frm.doc.projet}
                }).then((r) => dialog.fields_dict.content.$wrapper.html(r.message.html))
                dialog.show()
            });
        }
        frm.fields_dict['informations_section'].wrapper.css('background-color', 'antiquewhite');
        frm.fields_dict['section_break_woyn'].wrapper.css('background-color', 'cadetblue');
        frm.fields_dict['section_break_puil'].wrapper.css('background-color', 'cadetblue');
        
        frm.set_query("contact", function(){
        if(frm.doc.client) {
            return {
                //query: "frappe.email.doctype.contact.contact.contact_query",
                filters: { link_doctype: "Customer", link_name: frm.doc.client }
            };
       }
    });
  },
  address:function(frm) {
      frappe.contacts.get_address_display(frm)
  },
  client: function(frm) {
    frm.set_query("contact", function(){
        if(frm.doc.client) {
            return {
                query: "frappe.email.doctype.contact.contact.contact_query",
                filters: { link_doctype: "Customer", link_name: frm.doc.client }
            };
       }
    });
/*    frappe.call('erpnext.accounts.party.get_party_details', {
        party_type:"Customer",
        party: frm.doc.client,
    }).then(r => {
        console.log()
        frm.set_value({
            phone: r.message.contact_phone,
            email: r.message.contact_email,
        })
    })
*/
  }
});

Object.assign(frappe.listview_settings['Visite Technique'] = {
    hide_name_column: true,
    add_fields: ['projet'],
    
    
    	button: {
	    show: (doc) => {
	      return doc.projet
	    },
		get_description: (doc) => {
			return doc.project
		},
		get_label: () => {
			return "📁"
		},
		action: (doc) => {
		    frappe.set_route('Form', "Project", doc.projet)
		}
	}
})
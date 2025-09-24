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
                    method: "vt_internal.vt_internal.api.project_details.project_details",
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

        // Ajout : remplacer le texte du bouton "open_in_google_maps" par l'adresse et appliquer un fond bleu
        const enhanceOpenInMapsButton = () => {
            try {
                const applyStyles = (displayAddress) => {
                    const field = frm.fields_dict && frm.fields_dict.open_in_google_maps;
                    if (!field || !field.wrapper) return;
                    const $btn = $(field.wrapper).find('.btn, button').first();
                    if (!$btn || !$btn.length) return;

                    // Texte avec adresse (ou fallback)
                    const label = displayAddress ? `📍 ${displayAddress}` : '📍 Ouvrir dans Google Maps';
                    $btn.text(label);

                    // Styles : fond bleu, texte blanc, plein largeur, tactile
                    $btn.css({
                        'background-color': '#1E88E5',
                        'color': '#ffffff',
                        'width': '100%',
                        'font-size': '16px',
                        'padding': '12px 14px',
                        'border-radius': '8px',
                        'box-shadow': '0 2px 6px rgba(0,0,0,0.12)',
                        'display': 'flex',
                        'align-items': 'center',
                        'justify-content': 'center',
                        'gap': '8px',
                        'white-space': 'normal',
                        'text-align': 'left'
                    });

                    // Ajuster pour très petits écrans
                    if (window.matchMedia && window.matchMedia('(max-width: 480px)').matches) {
                        $btn.css({'font-size': '18px', 'padding': '14px 16px'});
                    }
                };

                // Si on a un lien Address, récupérer les champs détaillés pour composer l'adresse
                if (frm.doc.address) {
                    frappe.db.get_value("Address", frm.doc.address, ["address_line1", "address_line2", "city", "pincode"])
                        .then((r) => {
                            const a = (r && r.message) || {};
                            const parts = [];
                            if (a.address_line1) parts.push(a.address_line1);
                            if (a.address_line2) parts.push(a.address_line2);
                            if (a.city) parts.push(a.city);
                            if (a.pincode) parts.push(a.pincode);
                            const display = parts.join(", ") || frm.doc.address_display || frm.doc.address;
                            applyStyles(display);
                        }).catch(() => {
                            applyStyles(frm.doc.address_display || frm.doc.address);
                        });
                } else {
                    // Fallback : address_display ou valeur brute
                    applyStyles(frm.doc.address_display || frm.doc.address);
                }
            } catch (e) {
                console.warn('Enhance Open In Maps button failed', e);
            }
        };

        // Exécuter après un court délai pour s'assurer que le champ a été rendu
        setTimeout(enhanceOpenInMapsButton, 50);

        // ...existing code...
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
  },
    // Ajout : ouvrir l'adresse dans Google Maps quand on clique sur le bouton "open_in_google_maps"
    open_in_google_maps: function(frm) {
        // Si un enregistrement Address est lié, récupérer les champs individuels
        if (frm.doc.address) {
            frappe.db
                .get_value("Address", frm.doc.address, ["address_line1", "address_line2", "city", "pincode"])
                .then((r) => {
                    const a = r.message || {};
                    const parts = [];
                    if (a.address_line1) parts.push(a.address_line1);
                    if (a.address_line2) parts.push(a.address_line2);
                    if (a.city) parts.push(a.city);
                    if (a.pincode) parts.push(a.pincode);
                    const query = parts.join(", ") || frm.doc.address_display || frm.doc.address;
                    if (query) {
                        const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
                        window.open(url, "_blank");
                    } else {
                        frappe.msgprint(__('Adresse non renseignée'));
                    }
                });
        } else {
            // Fallback sur address_display ou valeur brute
            const query = frm.doc.address_display || frm.doc.address;
            if (query) {
                const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
                window.open(url, "_blank");
            } else {
                frappe.msgprint(__('Adresse non renseignée'));
            }
        }
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
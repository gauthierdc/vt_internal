// Converti depuis le Client Script ERP 'Commande client' (Sales Order / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.


frappe.ui.form.on('Sales Order', {
    delivery_date(frm) {
        const day_index = (new Date(cur_frm.doc.delivery_date)).getDay()
        if(frm.doc.company === "Vitrerie Stéphanoise" && day_index !=4 && frm.doc.custom_type_de_projet === "Livraison") {
            frappe.msgprint('⚠️ Vous ne livrez que le jeudi');
        }
        
    },
    
    customer(frm) {
        if(frm.doc.customer) {
            frappe.db.get_value('Customer', frm.doc.customer, 'custom_default_cost_center')
            .then(r => {
                frm.set_value("cost_center", r.message.custom_default_cost_center)
            })
        }
        
    },
    
	refresh(frm) {
	    // If there is only one empty line, remove it
/*	    if(frm.doc.items.length === 1 && !frm.doc.items[0].item_code) {
	        console.log("HEYY")
	        frm.set_value('items', []);
            frm.refresh_field('items');
	    }*/
	    frm.add_custom_button(__('Visite technique'), function(){
            frappe.route_options = {
                projet: frm.doc.project, 
                address: frm.doc.shipping_address_name,
                sales_order: frm.doc.name,
                client: frm.doc.customer,
                référence_pièce: frm.doc.reference_piece,
                contact: frm.doc.contact_person,
                cost_center: frm.doc.cost_center,
                company: frm.doc.company,
            }
            frappe.ui.form.make_quick_entry("Visite Technique", () => frm.reload_doc())
        
        }, "Créer");
	    if(frm.doc.project) {
		    frappe.db.get_list("Quality Incident", {
                fields: ["name", "object"],
                filters: {
                    project: frm.doc.project
                }
            }).then(results => {
                if (results && results.length > 0) {
                    const links = results.map(incident => 
                        `<a href="/app/quality-incident/${incident.name}" target="_blank">${incident.object}</a>`
                    ).join(", ");
                    frm.set_intro(`<b>🛑 Ce projet fait l'objet de ${results.length} incident(s) qualité :</b>${links}`, 'red');
                }
            });
	    }
	    if(frm.doc.drive_url) {
	        frm.add_web_link(frm.doc.drive_url, 'Lien du drive')
	    }
	    if(frm.doc.customer) {
            frappe.db.get_value("Customer", frm.doc.customer, "custom_customer_alert").then(r => {
                
                if (r.message.custom_customer_alert) {
                    frm.set_intro(`<b>Alerte client:</b> <br/> ${r.message.custom_customer_alert}`, 'yellow');
                }
            })
        }
        
        if(frm.doc.custom_insurance_client) {
            frappe.db.get_value("Customer", frm.doc.custom_insurance_client, "custom_customer_alert").then(r => {
                
                if (r.message.custom_customer_alert) {
                    frm.set_intro(`<b>Alerte assurance:</b> <br/> ${r.message.custom_customer_alert}`, 'yellow');
                }
            })
        }
	    
	   if(frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Modèle de devis'), function(){
              frappe.prompt({
                    label: 'Modèle de devis',
                    fieldname: 'devis',
                    fieldtype: 'Link',
                    options: 'Quotation',
                    get_query: () => ({
						filters: {
							custom_est_un_modèle_:1
						},
					}),
                }, (values) => {
                    frappe.db.get_doc('Quotation', values.devis)
                    .then(doc => {
                        frm.set_value("custom_type_de_projet", doc.custom_type_de_projet)
                        frm.set_value("secteur_vt", doc.secteur_vt)
                        doc.items.forEach(t => frm.add_child('items', t))
                    frm.refresh_field('items');
                    frm.refresh()
                    })
                    
                    
                })}, __("Get Items From"));
        }
	    
	    
	    setTimeout(() => {
            frm.remove_custom_button('Pick List', 'Create');
            frm.remove_custom_button('Work Order', 'Create');
            //frm.remove_custom_button('Material Request', 'Create');
            //frm.remove_custom_button('Request for Raw Materials', 'Create');
            //frm.remove_custom_button('Demande de paiement', 'Create');
            frm.remove_custom_button('Paiement', 'Create');
        }, 10);
        
        frm.add_custom_button(__('Fiche de travail'), function(){
            frappe.call({
                method: "new_visite_technique_from_quotation",
                args: {
                    sales_order_name: frm.doc.name,
                    customer: frm.doc.party,
                    company: frm.doc.company,
                    contact_email: frm.doc.contact_email,
                    address: frm.doc.shipping_address_name,
                    project: frm.doc.project,
                    project_type: frm.doc.custom_type_de_projet
                }
            }).then(res => {
                frm.reload_doc();
                frappe.new_doc("Fiche de travail", {
                    projet: res.message.project, 
                    address: frm.doc.shipping_address_name,
                    sales_order: frm.doc.name,
                    description: frm.doc.custom_environnement_du_chantier,
                    customer: frm.doc.customer,
                }, (doc) => {
                    frm.doc.items.forEach(i => {
                        let row = frappe.model.add_child(doc, "items")
                        row.quantité=i.row_type !== "" ? 0 : i.qty,
                        row.description = i.description || i.item_name,
                        row.status = i.custom_statut_interne,
                        row.weight_per_unit = i.weight_per_unit,
                        row.row_item_code = i.name,
                        row.item_code = i.item_code
                    })
                })
                
            })
            
            
        }, "Créer");
        
	   if(frm.doc.docstatus != 2) {
            
            frm.add_custom_button(__('Fabrication'), function() {
                open_item_selection_dialog(frm);
            }, __("Create"));
        }
        
        if(frm.doc.custom_per_received < 100 && !["À faire", "Fait", "En cours"].includes(frm.doc.custom_statut_fiche_de_travail)) {
            
            frm.add_custom_button(__('Chantier en cours'), function() {
                open_fiche_de_travail_dialog(frm)
            }, __("Status"));
        }
        
	   
	   

        if(frm.doc.project) {
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
            			frappe.set_route('Form', "Project", frm.doc.project);
            		},
            		primary_action_label: __("Projet"),
            	});
            	
            	frappe.call({
                    method: "vt_internal.vt_internal.api.project_details.project_details",
                    args: {project: frm.doc.project}
                }).then((r) => dialog.fields_dict.content.$wrapper.html(r.message.html))
                dialog.show()
            });
            frm.add_custom_button(__('Incident qualité'), function(){
                frappe.new_doc("Quality Incident", {project: frm.doc.project})
            }, __("Create"));
            
            frm.add_custom_button(__('Réception de travaux'), function(){
                frappe.new_doc("Work Completion Receipt", {sales_order: frm.doc.name, contact_email: frm.doc.contact_email})
            }, __("Create"));
        }
        
        const groups = ["Créer"];
        const compare = (a, b) => a.textContent.localeCompare(b.textContent);
        for (const groupLabel of groups) {
          const menu = frm.page.get_inner_group_button(groupLabel)?.find("[role=menu]").get(0);
          if (menu) {
            Array.from(menu.children).sort(compare).forEach((x) => menu.appendChild(x));
          }
        }
	}
})


function open_item_selection_dialog(frm) {
    // Créer une nouvelle boîte de dialogue pour sélectionner les articles
    let dialog = new frappe.ui.Dialog({
        title: __('Fabrication'),
        fields: [
            {
                label: 'Date de fin de production prévue',
                fieldname: 'delivery_date',
                description: frm.doc.custom_per_received > 0 && '<span style="color: red">Des verres sont déjà en fabrication</span>',
                fieldtype: 'Date',
                default: new Date(new Date(cur_frm.doc.delivery_date) - 86400000)
            },
            {
                label: 'Exclure les verres avec un fournisseur externe',
                fieldname: 'exclude_external_supplier',
                fieldtype: 'Check',
                default: 1
            },
            {
                fieldname: 'items',
                fieldtype: 'Table',
                read_only: 1,
                label: 'Items',
                fields: [
                    {
                        fieldname: 'line_number',
                        label: 'line_number',
                        fieldtype: 'Number',
                        read_only: 1,
                    },
                    {
                        fieldname: 'description',
                        label: 'Description',
                        fieldtype: 'Text Editor',
                        read_only: 1,
                        in_list_view: 1,
                    }
                ],
                data: [], // Initialiser la table
            }
        ],
        primary_action_label: 'Créer',
        primary_action(values) {
            // Filtrer les articles cochés
            frappe.call({
                method: "new_fabrication",
                args: {sales_order: frm.doc.name, items: values.items.map(i => i.line_number).join(','), delivery_date: values.delivery_date}
            })
            frappe.show_alert({
                message: "Les fabrications ont été créées",
                indicator: "green"
            }, 5);
            dialog.hide();
        }
    });

    // Fonction pour filtrer les articles en fonction de la case "external_supplier"
    function filter_items() {
        let existing_items = frm.doc.items.filter(i => 
            i.bom_no && 
            (!dialog.fields_dict.exclude_external_supplier.get_value() || (i.supplier && i.supplier.includes("INTERNE")))
        ) || [];

        // Ajouter les articles filtrés à la table
        let table_data = existing_items.map(item => ({
            description: item.description,
            line_number: item.idx - 1,
        }));

        // Mettre à jour la table avec les nouveaux articles filtrés
        dialog.fields_dict.items.df.data = table_data;
        dialog.fields_dict.items.grid.refresh();
    }

    // Ajouter un événement pour rafraîchir la table quand la case "external_supplier" est cochée/décochée
    dialog.fields_dict.exclude_external_supplier.$input.on('change', function() {
        filter_items();
    });

    // Initialiser la table avec les articles filtrés dès le départ
    filter_items();

    // Afficher la boîte de dialogue
    dialog.show();
}

function open_fiche_de_travail_dialog(frm) {
              frappe.confirm(
            __("Vos fiches de travail liées à cette commande vont passer au statut 'À faire'."),
            () => {
              // Ici tu peux appeler ton API serveur si tu veux vraiment lancer l’action
              // Exemple :
              frappe.call({
                method: "sales_order_to_chantier_a_faire",
                args: { sales_order: frm.doc.name },
                callback: (r) => {
                  frm.reload_doc();
                }
              });
            },
            () => {}
          );
}

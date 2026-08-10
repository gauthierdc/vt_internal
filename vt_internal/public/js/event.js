// Converti depuis le Client Script ERP 'Évenement' (Event / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Event', {
    refresh(frm) {
        frm.dashboard.links_area.hide();
        frm.events.setup_custom_html(frm);
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
                    frm.set_intro(`<b>🛑 Ce projet fait l'objet de ${results.length} incident(s) qualité : </b>${links}`, 'red');
                }
            });
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
                frappe.new_doc("Quality Incident", {project: frm.doc.project, fiche_de_travail: frm.doc.name})
            }, __("Create"));
        }
        
        frm.set_query("custom_fiche_de_travail", () => {
			return {
				filters: {
					status: ["not in", ["Fait", "Annulé"]],
				},
			};
		});
        
    },

    setup_custom_html(frm) {
        if (!frm.fields_dict.custom_html) {
            return;
        }

        if (frm.doc.custom_fiche_de_travail) {
            setup_from_fiche_de_travail(frm);
        } else if (frm.doc.custom_visite_technique) {
            setup_from_visite_technique(frm);
        } else {
            // Pas de fiche de travail ni visite technique (ex: véhicule seul)
            // Afficher quand même les boutons de duplication
            render_custom_html(frm, {
                doctype: null,
                docname: null,
                address_display: '',
                address_name: '',
                description: '',
                reference: '',
                phone: ''
            });
        }
    },

custom_fiche_de_travail(frm) {
    if (!frm.doc.custom_fiche_de_travail) {
        frm.events.setup_custom_html(frm);
        return;
    }
    
    frappe.db.get_value('Fiche de travail', frm.doc.custom_fiche_de_travail, ['customer', 'address', 'projet'])
        .then(r => {
            const customer = r?.message?.customer || frm.doc.custom_fiche_de_travail;
            const address = r?.message?.address;
            const project = r?.message?.projet;

            if (project) {
                frm.set_value('project', project);
            }

            if (address) {
                frappe.db.get_value('Address', address, 
                    ['address_line1', 'address_line2', 'city', 'pincode'])
                    .then(addr_r => {
                        const addr = addr_r?.message || {};
                        const address_parts = [
                            addr.address_line1,
                            addr.address_line2,
                            addr.pincode && addr.city ? `${addr.pincode} ${addr.city}` : (addr.city || addr.pincode)
                        ].filter(Boolean);
                        
                        const address_text = address_parts.join(', ');
                        frm.set_value('subject', `🏗️ ${customer} \n ${address_text}`);
                        frm.events.setup_custom_html(frm);
                    })
                    .catch(() => {
                        frm.set_value('subject', `🏗️ ${customer}`);
                        frm.events.setup_custom_html(frm);
                    });
            } else {
                frm.set_value('subject', customer);
                frm.events.setup_custom_html(frm);
            }
        })
        .catch(err => {
            console.error('Erreur lors de la récupération de la fiche de travail:', err);
            frm.events.setup_custom_html(frm);
        });
},

custom_visite_technique(frm) {
    if (!frm.doc.custom_visite_technique) {
        frm.events.setup_custom_html(frm);
        return;
    }
    
    frappe.db.get_value('Visite Technique', frm.doc.custom_visite_technique, ['client', 'address', 'projet'])
        .then(r => {
            const client = r?.message?.client || frm.doc.custom_visite_technique;
            const address = r?.message?.address;
            const projet = r?.message?.projet;

            if (projet) {
                frm.set_value('project', projet);
            }

            if (address) {
                frappe.db.get_value('Address', address, 
                    ['address_line1', 'address_line2', 'city', 'pincode'])
                    .then(addr_r => {
                        const addr = addr_r?.message || {};
                        const address_parts = [
                            addr.address_line1,
                            addr.address_line2,
                            addr.pincode && addr.city ? `${addr.pincode} ${addr.city}` : (addr.city || addr.pincode)
                        ].filter(Boolean);
                        
                        const address_text = address_parts.join(', ');
                        frm.set_value('subject', `🔍 ${client} - ${address_text}`);
                        frm.events.setup_custom_html(frm);
                    })
                    .catch(() => {
                        frm.set_value('subject', `🔍 ${client}`);
                        frm.events.setup_custom_html(frm);
                    });
            } else {
                frm.set_value('subject', `🔍 ${client}`);
                frm.events.setup_custom_html(frm);
            }
        })
        .catch(err => {
            console.error('Erreur lors de la récupération de la visite technique:', err);
            frm.events.setup_custom_html(frm);
        });
},
});

function setup_from_fiche_de_travail(frm) {
    frappe.db.get_value('Fiche de travail', frm.doc.custom_fiche_de_travail, ['address', 'description', 'référence_pièce', 'phone'])
        .then(r => {
            const data = r?.message || {};
            if (data.address) {
                // Récupérer les champs de l'adresse directement
                frappe.db.get_value('Address', data.address, 
                    ['address_line1', 'address_line2', 'city', 'pincode', 'country'])
                    .then(addr_r => {
                        const addr = addr_r?.message || {};
                        // Formater l'adresse manuellement
                        const address_parts = [
                            addr.address_line1,
                            addr.address_line2,
                            addr.pincode && addr.city ? `${addr.pincode} ${addr.city}` : (addr.city || addr.pincode),
                            addr.country
                        ].filter(Boolean);
                        
                        const address_display = address_parts.join(', ');
                        
                        render_custom_html(frm, {
                            doctype: 'Fiche de travail',
                            docname: frm.doc.custom_fiche_de_travail,
                            address_display: address_display,
                            address_name: data.address,
                            description: data.description,
                            reference: data.référence_pièce,
                            phone: data.phone
                        });
                    });
            } else {
                render_custom_html(frm, {
                    doctype: 'Fiche de travail',
                    docname: frm.doc.custom_fiche_de_travail,
                    address_display: '',
                    address_name: '',
                    description: data.description,
                    reference: data.référence_pièce,
                    phone: data.phone
                });
            }
        });
}

function setup_from_visite_technique(frm) {
    frappe.db.get_value('Visite Technique', frm.doc.custom_visite_technique, ['address', 'description', 'référence_pièce'])
        .then(r => {
            const data = r?.message || {};
            if (data.address) {
                // Récupérer les champs de l'adresse directement
                frappe.db.get_value('Address', data.address, 
                    ['address_line1', 'address_line2', 'city', 'pincode', 'country'])
                    .then(addr_r => {
                        const addr = addr_r?.message || {};
                        // Formater l'adresse manuellement
                        const address_parts = [
                            addr.address_line1,
                            addr.address_line2,
                            addr.pincode && addr.city ? `${addr.pincode} ${addr.city}` : (addr.city || addr.pincode),
                            addr.country
                        ].filter(Boolean);
                        
                        const address_display = address_parts.join(', ');
                        
                        render_custom_html(frm, {
                            doctype: 'Visite Technique',
                            docname: frm.doc.custom_visite_technique,
                            address_display: address_display,
                            address_name: data.address,
                            description: data.description,
                            reference: data.référence_pièce
                        });
                    });
            } else {
                render_custom_html(frm, {
                    doctype: 'Visite Technique',
                    docname: frm.doc.custom_visite_technique,
                    address_display: '',
                    address_name: '',
                    description: data.description,
                    reference: data.référence_pièce
                });
            }
        });
}

function render_custom_html(frm, options) {
    const { doctype, docname, address_display, address_name, description, reference, phone } = options;
    const $wrapper = frm.fields_dict.custom_html.$wrapper;

    let html = '<div style="display: flex; flex-direction: column; gap: 10px;">';

    const btn_style = 'display: flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 16px; border: none; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s ease; width: 100%;';

    // Ligne de boutons : Maps + Dupliquer Employé + Dupliquer Véhicule + Multi-jours + Supprimer
    html += '<div style="display: flex; gap: 8px;">';
    
    if (address_display) {
        html += `
            <div style="display: flex; flex: 1; border-radius: 8px; overflow: hidden;">
                <button class="btn btn-maps" style="${btn_style} flex: 1; background-color: #1976D2; color: #ffffff; border-radius: 8px 0 0 8px;">
                    📍 ${address_display}
                </button>
                ${address_name ? `
                    <button class="btn btn-edit-address" style="padding: 8px 12px; border: none; background-color: #1565C0; color: #ffffff; cursor: pointer; display: flex; align-items: center; border-radius: 0 8px 8px 0;" title="Modifier l'adresse">
                        ✏️
                    </button>
                ` : ''}
            </div>
        `;
    }
    
    // Deux boutons de duplication : employé ET véhicule
    html += `
        <button class="btn btn-duplicate-employee" style="${btn_style} width: 48px; flex: none; background-color: #7B1FA2; color: #ffffff;" title="Dupliquer pour un employé">
            👷
        </button>
        <button class="btn btn-duplicate-vehicle" style="${btn_style} width: 48px; flex: none; background-color: #00796B; color: #ffffff;" title="Dupliquer pour un véhicule">
            🚐
        </button>
        <button class="btn btn-duplicate-multiday" style="${btn_style} width: 48px; flex: none; background-color: #FF8F00; color: #ffffff;" title="Dupliquer sur plusieurs jours">
            📅
        </button>
        <button class="btn btn-delete" style="${btn_style} width: 48px; flex: none; background-color: #c0392b; color: #ffffff;" title="Supprimer">
            🗑️
        </button>
    `;
    html += '</div>';

    // Bouton ouvrir le document (seulement si on a un doctype)
    if (doctype && docname) {
        const icon = doctype === 'Fiche de travail' ? '🔧' : '📋';
        html += `
            <button class="btn btn-open-doc" style="${btn_style} background-color: #43A047; color: #ffffff;">
                ${icon} Ouvrir la ${doctype}
            </button>
        `;
    }

    // Bloc d'infos (seulement si on a des infos à afficher)
    let infos = '';
    if (reference) {
        infos += `<div><strong>Référence :</strong> ${reference}</div>`;
    }
    if (phone) {
        infos += `<div style="margin-top: 8px;"><strong>Téléphone :</strong> <a href="tel:${phone}" style="color: #1976D2;">${phone}</a></div>`;
    }
    if (description) {
        infos += `<div style="margin-top: 8px;"><strong>Description :</strong><br>${description}</div>`;
    }

    if (infos) {
        html += `
            <div style="background-color: #f5f5f5; padding: 12px; border-radius: 8px; margin-top: 5px;">
                ${infos}
            </div>
        `;
    }

    html += '</div>';

    $wrapper.html(html);

    // Events
    $wrapper.find('.btn-duplicate-employee').on('click', () => {
        show_duplicate_employee_dialog(frm);
    });

    $wrapper.find('.btn-duplicate-vehicle').on('click', () => {
        show_duplicate_vehicle_dialog(frm);
    });

    $wrapper.find('.btn-duplicate-multiday').on('click', () => {
        show_duplicate_multiday_dialog(frm);
    });

    $wrapper.find('.btn-delete').on('click', () => {
        show_delete_dialog(frm);
    });

    if (address_display) {
        $wrapper.find('.btn-maps').on('click', () => {
            const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address_display)}`;
            window.open(url, "_blank");
        });
        
        if (address_name) {
            $wrapper.find('.btn-edit-address').on('click', () => {
                frappe.set_route('Form', 'Address', address_name);
            });
        }
    }

    if (doctype && docname) {
        $wrapper.find('.btn-open-doc').on('click', () => {
            frappe.set_route('Form', doctype, docname);
        });
    }
}

// === DIALOG: Dupliquer pour un employé ===
function show_duplicate_employee_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: 'Dupliquer pour un employé',
        fields: [{
            label: 'Employé',
            fieldname: 'employee',
            fieldtype: 'Link',
            options: 'Employee',
            reqd: 1,
            get_query: function() {
                return {
                    filters: {
                        designation: 'Poseur'
                    }
                };
            }
        }],
        primary_action_label: 'Dupliquer',
        primary_action(values) {
            d.hide();
            duplicate_event(frm, { employee: values.employee });
        }
    });
    d.show();
}

// === DIALOG: Dupliquer pour un véhicule ===
function show_duplicate_vehicle_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: 'Dupliquer pour un véhicule',
        fields: [{
            label: 'Véhicule',
            fieldname: 'vehicle',
            fieldtype: 'Link',
            options: 'Vehicle',
            reqd: 1
        }],
        primary_action_label: 'Dupliquer',
        primary_action(values) {
            d.hide();
            duplicate_event(frm, { vehicle: values.vehicle });
        }
    });
    d.show();
}

// === DIALOG: Dupliquer sur plusieurs jours (même employé/véhicule) ===
function show_duplicate_multiday_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: 'Dupliquer sur plusieurs jours',
        fields: [{
            label: 'Nombre de jours',
            fieldname: 'nb_days',
            fieldtype: 'Int',
            reqd: 1,
            default: 5,
            description: "Crée un événement par jour ouvré (lundi-vendredi) à partir du lendemain de l'événement"
        }],
        primary_action_label: 'Dupliquer',
        primary_action(values) {
            d.hide();
            duplicate_event_multiday(frm, values.nb_days);
        }
    });
    d.show();
}

// === DIALOG: Supprimer ===
function show_delete_dialog(frm) {
    frappe.confirm(
        `Êtes-vous sûr de vouloir supprimer cet événement ?`,
        () => {
            frappe.call({
                method: 'frappe.client.delete',
                args: {
                    doctype: 'Event',
                    name: frm.doc.name
                },
                callback: function(r) {
                    frappe.show_alert({
                        message: 'Événement supprimé',
                        indicator: 'green'
                    });
                    frappe.set_route('List', 'Event');
                }
            });
        }
    );
}

// === FONCTION: Dupliquer un événement ===
function duplicate_event(frm, options = {}) {
    const doc = frm.doc;
    
    const new_doc = {
        doctype: 'Event',
        subject: doc.subject,
        starts_on: doc.starts_on,
        ends_on: doc.ends_on,
        all_day: doc.all_day,
        status: doc.status,
        description: doc.description,
        event_category: doc.event_category,
        event_type: doc.event_type,
        custom_fiche_de_travail: doc.custom_fiche_de_travail,
        custom_visite_technique: doc.custom_visite_technique
    };

    // Si on duplique pour un employé → mettre l'employé (pas de véhicule)
    // Si on duplique pour un véhicule → mettre le véhicule (pas d'employé)
    if (options.employee) {
        new_doc.custom_employé = options.employee;
        // Pas de véhicule
    } else if (options.vehicle) {
        new_doc.custom_vehicle = options.vehicle;
        // Pas d'employé
    }

    frappe.call({
        method: 'frappe.client.insert',
        args: { doc: new_doc },
        callback: function(r) {
            if (r.message) {
                frappe.show_alert({
                    message: `Événement dupliqué : ${r.message.name}`,
                    indicator: 'green'
                });
                frappe.set_route('Form', 'Event', r.message.name);
            }
        }
    });
}

// === FONCTION: Dupliquer sur plusieurs jours ouvrés (même employé/véhicule) ===
function duplicate_event_multiday(frm, nb_days) {
    const doc = frm.doc;
    
    // Calculer l'heure de début et de fin depuis l'événement original
    const original_starts = frappe.datetime.str_to_obj(doc.starts_on);
    const original_ends = doc.ends_on ? frappe.datetime.str_to_obj(doc.ends_on) : null;
    
    const start_time = original_starts.toTimeString().slice(0, 8);
    const end_time = original_ends ? original_ends.toTimeString().slice(0, 8) : null;

    // Collecter les dates (jours ouvrés uniquement), à partir du lendemain de l'événement
    const dates_to_create = [];
    let cursor_date = new Date(original_starts);
    cursor_date.setDate(cursor_date.getDate() + 1); // Commencer le lendemain de l'événement
    
    while (dates_to_create.length < nb_days) {
        const day_of_week = cursor_date.getDay();
        // 0 = Dimanche, 6 = Samedi → on les saute
        if (day_of_week !== 0 && day_of_week !== 6) {
            dates_to_create.push(new Date(cursor_date));
        }
        cursor_date.setDate(cursor_date.getDate() + 1);
    }

    // Créer les événements
    let created = 0;
    let errors = 0;

    frappe.show_progress('Duplication', 0, dates_to_create.length, 'Création des événements...');

    const createNext = (index) => {
        if (index >= dates_to_create.length) {
            frappe.hide_progress();
            if (errors > 0) {
                frappe.msgprint(`${created} événement(s) créé(s), ${errors} erreur(s)`);
            } else {
                frappe.show_alert({
                    message: `${created} événement(s) créé(s)`,
                    indicator: 'green'
                });
            }
            frm.reload_doc();
            return;
        }

        const date = dates_to_create[index];
        const date_str = frappe.datetime.obj_to_str(date).slice(0, 10);
        
        const new_doc = {
            doctype: 'Event',
            subject: doc.subject,
            starts_on: `${date_str} ${start_time}`,
            ends_on: end_time ? `${date_str} ${end_time}` : null,
            all_day: doc.all_day,
            status: doc.status,
            description: doc.description,
            event_category: doc.event_category,
            event_type: doc.event_type,
            custom_fiche_de_travail: doc.custom_fiche_de_travail,
            custom_visite_technique: doc.custom_visite_technique,
            // Garder le même employé/véhicule que l'original
            custom_employé: doc.custom_employé,
            custom_vehicle: doc.custom_vehicle
        };

        frappe.call({
            method: 'frappe.client.insert',
            args: { doc: new_doc },
            async: false,
            callback: function(r) {
                if (r.message) {
                    created++;
                } else {
                    errors++;
                }
                frappe.show_progress('Duplication', index + 1, dates_to_create.length, `${index + 1}/${dates_to_create.length}`);
                createNext(index + 1);
            },
            error: function() {
                errors++;
                createNext(index + 1);
            }
        });
    };

    createNext(0);
}

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

// === PHOTO GALLERY FUNCTIONS ===

function is_image(url) {
    if (!url) return false;
    return /\.(jpg|jpeg|png|gif|webp|bmp|heic|heif)$/i.test(url);
}

function render_photos_section(frm) {
    if (!frm.fields_dict.photos_section) return;

    if (!frm.doc.name || frm.is_new()) {
        frm.fields_dict.photos_section.$wrapper.html(`
            <div style="padding: 20px; text-align: center; background: #f5f5f5; border-radius: 8px; margin: 10px 0;">
                <p class="text-muted" style="margin: 0;">Enregistrez le document pour ajouter des photos</p>
            </div>
        `);
        return;
    }

    // Charger les fichiers attachés
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'File',
            filters: {
                attached_to_doctype: 'Visite Technique',
                attached_to_name: frm.doc.name,
                is_folder: 0
            },
            fields: ['name', 'file_url', 'file_name'],
            order_by: 'creation desc',
            limit_page_length: 0
        },
        callback: function(r) {
            const files = (r.message || []).filter(f => is_image(f.file_url));

            let html = `
                <div style="margin: 10px 0; display: flex; gap: 10px;">
                    <button class="btn btn-primary btn-lg photos-camera-btn" style="flex:1; font-size:16px; padding:15px; border-radius:8px;">
                        <i class="fa fa-camera" style="margin-right: 8px;"></i> Prendre une photo
                    </button>
                    <button class="btn btn-default btn-lg photos-gallery-btn" style="flex:1; font-size:16px; padding:15px; border-radius:8px; border: 2px solid #ddd;">
                        <i class="fa fa-image" style="margin-right: 8px;"></i> Galerie
                    </button>
                </div>
            `;

            if (files.length > 0) {
                html += `
                    <div class="photos-gallery" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin-top: 15px;">
                `;

                files.forEach(file => {
                    html += `
                        <div class="photo-item" style="position: relative; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            <a href="${file.file_url}" target="_blank" style="display: block;">
                                <img src="${file.file_url}" alt="${file.file_name}"
                                    style="width:100%; height:150px; object-fit:cover; cursor:pointer; transition: transform 0.2s;"
                                    onmouseover="this.style.transform='scale(1.05)'"
                                    onmouseout="this.style.transform='scale(1)'">
                            </a>
                            <button class="btn btn-danger btn-xs delete-photo-btn" data-file="${file.name}"
                                style="position:absolute; top:5px; right:5px; border-radius:50%; width:28px; height:28px; padding:0; display:flex; align-items:center; justify-content:center; opacity:0.9;">
                                <i class="fa fa-times"></i>
                            </button>
                        </div>
                    `;
                });

                html += '</div>';
            } else {
                html += `
                    <div style="padding: 30px; text-align: center; background: #fafafa; border-radius: 8px; margin-top: 15px; border: 2px dashed #ddd;">
                        <i class="fa fa-image" style="font-size: 48px; color: #ccc; margin-bottom: 10px;"></i>
                        <p class="text-muted" style="margin: 0;">Aucune photo pour le moment</p>
                    </div>
                `;
            }

            frm.fields_dict.photos_section.$wrapper.html(html);

            // Bind events
            frm.fields_dict.photos_section.$wrapper.find('.photos-camera-btn').click(() => open_photo_dialog(frm, true));
            frm.fields_dict.photos_section.$wrapper.find('.photos-gallery-btn').click(() => open_photo_dialog(frm, false));
            frm.fields_dict.photos_section.$wrapper.find('.delete-photo-btn').click(function(e) {
                e.preventDefault();
                e.stopPropagation();
                delete_photo(frm, $(this).data('file'));
            });
        }
    });
}

function open_photo_dialog(frm, useCamera = false) {
    // Créer input file caché
    // useCamera=true : ouvre la caméra directement (capture="environment")
    // useCamera=false : ouvre le sélecteur de fichiers/galerie (multiple)
    let $input;
    if (useCamera) {
        $input = $('<input type="file" accept="image/*" capture="environment" style="display:none;">');
    } else {
        $input = $('<input type="file" multiple accept="image/*" style="display:none;">');
    }
    $('body').append($input);

    $input.on('change', function() {
        let files = this.files;
        if (files.length > 0) {
            upload_photos(frm, files);
        }
        $input.remove();
    });

    $input.click();
}

function upload_photos(frm, files) {
    const total = files.length;
    let uploaded = 0;
    let errors = 0;

    frappe.show_progress('Upload', 0, total, 'Upload en cours...');

    const uploadNext = (index) => {
        if (index >= total) {
            frappe.hide_progress();
            if (errors > 0) {
                frappe.msgprint(__(`${uploaded} photo(s) uploadée(s), ${errors} erreur(s)`));
            } else {
                frappe.show_alert({message: __(`${uploaded} photo(s) ajoutée(s)`), indicator: 'green'});
            }
            render_photos_section(frm);
            return;
        }

        const file = files[index];
        const formData = new FormData();
        formData.append('file', file, file.name);
        formData.append('doctype', frm.doctype);
        formData.append('docname', frm.doc.name);
        formData.append('is_private', 0);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/method/upload_file', true);
        xhr.setRequestHeader('X-Frappe-CSRF-Token', frappe.csrf_token);

        xhr.onload = function() {
            if (xhr.status === 200) {
                uploaded++;
                frappe.show_progress('Upload', uploaded, total, `${uploaded}/${total} photos...`);
            } else {
                console.error('Upload error:', xhr.responseText);
                errors++;
            }
            uploadNext(index + 1);
        };

        xhr.onerror = function() {
            console.error('Upload error');
            errors++;
            uploadNext(index + 1);
        };

        xhr.send(formData);
    };

    uploadNext(0);
}

function delete_photo(frm, file_name) {
    frappe.confirm(
        __('Supprimer cette photo ?'),
        () => {
            frappe.call({
                method: 'frappe.client.delete',
                args: { doctype: 'File', name: file_name },
                callback: () => {
                    frappe.show_alert({message: __('Photo supprimée'), indicator: 'green'});
                    render_photos_section(frm);
                },
                error: () => {
                    frappe.msgprint(__('Erreur lors de la suppression'));
                }
            });
        }
    );
}

// === END PHOTO GALLERY FUNCTIONS ===

frappe.ui.form.on('Visite Technique', {
    refresh: function(frm) {
        // Rendre la galerie photos
        render_photos_section(frm);

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
            frm.add_custom_button(__('Événement'), function(){
                frappe.new_doc("Event", { project: frm.doc.projet, custom_visite_technique: frm.doc.name });
            }, __("Create"));
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
                            const display = parts.join(", ") || frm.doc.address;
                            applyStyles(display);
                        }).catch(() => {
                            applyStyles(frm.doc.address);
                        });
                } else {
                    applyStyles(frm.doc.address);
                }
            } catch (e) {
                console.warn('Enhance Open In Maps button failed', e);
            }
        };

        // Exécuter après un court délai pour s'assurer que le champ a été rendu
        setTimeout(enhanceOpenInMapsButton, 50);

        // ...existing code...
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
                    const query = parts.join(", ") || frm.doc.address;
                    if (query) {
                        const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
                        window.open(url, "_blank");
                    } else {
                        frappe.msgprint(__('Adresse non renseignée'));
                    }
                });
        } else {
            // Fallback sur address_display ou valeur brute
            const query = frm.doc.address;
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
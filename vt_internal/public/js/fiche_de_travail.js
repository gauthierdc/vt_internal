// Converti depuis le Client Script ERP 'Fiche de travaux' (Fiche de travail / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

const timer_api = (args, message) => {
    return frappe.call({
        method: "timesheet_post_api",
        args
    }).then(() => {
        frappe.show_alert({message: message, indicator: 'green'}, 5)
        location.reload()
    })
}

function startActivity(frm) {
    frappe.prompt([{
            label: "Type d'activité",
            fieldname: 'activity_type',
            fieldtype: 'Link',
            options: 'Activity Type',
            default: 'Chantier'
        },
        {
            label: 'Fiche de travail',
            fieldname: 'fiche_de_travail',
            fieldtype: 'Link',
            options: 'Fiche de travail',
            default: frm.doc.name
        },
        {
            label: 'SAV',
            fieldname: 'sav',
            fieldtype: 'Check',
        }], (values) => {
            timer_api({
                action: "start_construction",
                fiche_de_travail: values.fiche_de_travail,
                activity_type: values.activity_type,
                sav: values.sav,
            }, 'Tâche commencée')
        })
}

// === PHOTO GALLERY FUNCTIONS ===

function is_image(url) {
    if (!url) return false;
    return /\.(jpg|jpeg|png|gif|webp|bmp|heic|heif)$/i.test(url);
}

function render_photos_section(frm) {
    if (!frm.fields_dict.photos) return;

    if (!frm.doc.name || frm.is_new()) {
        frm.fields_dict.photos.$wrapper.html(`
            <div style="padding: 20px; text-align: center; background: #f5f5f5; border-radius: 8px; margin: 10px 0;">
                <p class="text-muted" style="margin: 0;">Enregistrez le document pour ajouter des photos</p>
            </div>
        `);
        return;
    }

    let html = '';

    // Fonction pour générer le HTML d'une galerie
    const generateGalleryHtml = (files, canDelete) => {
        if (files.length === 0) {
            return `
                <div style="padding: 20px; text-align: center; background: #fafafa; border-radius: 8px; border: 2px dashed #ddd;">
                    <i class="fa fa-image" style="font-size: 32px; color: #ccc; margin-bottom: 8px;"></i>
                    <p class="text-muted" style="margin: 0; font-size: 13px;">Aucune photo</p>
                </div>
            `;
        }
        
        let galleryHtml = `<div class="photos-gallery" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px;">`;
        
        files.forEach(file => {
            galleryHtml += `
                <div class="photo-item" style="position: relative; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <a href="${file.file_url}" target="_blank" style="display: block;">
                        <img src="${file.file_url}" alt="${file.file_name}"
                            style="width:100%; height:250px; object-fit:cover; cursor:pointer; transition: transform 0.2s;"
                            onmouseover="this.style.transform='scale(1.05)'"
                            onmouseout="this.style.transform='scale(1)'">
                    </a>
                    ${canDelete ? `
                        <button class="btn btn-danger btn-xs delete-photo-btn" data-file="${file.name}"
                            style="position:absolute; top:5px; right:5px; border-radius:50%; width:28px; height:28px; padding:0; display:flex; align-items:center; justify-content:center; opacity:0.9;">
                            <i class="fa fa-times"></i>
                        </button>
                    ` : ''}
                </div>
            `;
        });
        
        galleryHtml += '</div>';
        return galleryHtml;
    };

    // Charger les photos des deux sources en parallèle
    const promises = [];

    // 1. Photos de la Visite Technique (si liée)
    if (frm.doc.visite_technique) {
        promises.push(
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'File',
                    filters: {
                        attached_to_doctype: 'Visite Technique',
                        attached_to_name: frm.doc.visite_technique,
                        is_folder: 0
                    },
                    fields: ['name', 'file_url', 'file_name'],
                    order_by: 'creation desc',
                    limit_page_length: 0
                }
            }).then(r => ({ type: 'vt', files: (r.message || []).filter(f => is_image(f.file_url)) }))
        );
    } else {
        promises.push(Promise.resolve({ type: 'vt', files: [] }));
    }

    // 2. Photos de la Fiche de travail
    promises.push(
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'File',
                filters: {
                    attached_to_doctype: 'Fiche de travail',
                    attached_to_name: frm.doc.name,
                    is_folder: 0
                },
                fields: ['name', 'file_url', 'file_name'],
                order_by: 'creation desc',
                limit_page_length: 0
            }
        }).then(r => ({ type: 'ft', files: (r.message || []).filter(f => is_image(f.file_url)) }))
    );

    Promise.all(promises).then(results => {
        const vtResult = results.find(r => r.type === 'vt');
        const ftResult = results.find(r => r.type === 'ft');

        let html = '';

        // Section 1: Photos de la Visite Technique
        if (frm.doc.visite_technique) {
            html += `
                <div style="margin-bottom: 20px;">
                    <h6 style="margin-bottom: 10px; color: #333; font-weight: 600;">
                        <i class="fa fa-clipboard" style="margin-right: 6px;"></i>
                        Photos de la Visite Technique
                        <a href="/app/visite-technique/${frm.doc.visite_technique}" target="_blank" style="font-size: 12px; margin-left: 8px;">(Voir)</a>
                    </h6>
                    ${generateGalleryHtml(vtResult.files, false)}
                </div>
            `;
        }

        // Section 2: Photos de la Fiche de travail
        html += `
            <div>
                <h6 style="margin-bottom: 10px; color: #333; font-weight: 600;">
                    <i class="fa fa-wrench" style="margin-right: 6px;"></i>
                    Photos de cette Fiche de travail
                </h6>
                <div style="margin-bottom: 10px; display: flex; gap: 10px;">
                    <button class="btn btn-primary btn-sm photos-camera-btn" style="flex:1; padding:10px; border-radius:6px;">
                        <i class="fa fa-camera" style="margin-right: 6px;"></i> Prendre une photo
                    </button>
                    <button class="btn btn-default btn-sm photos-gallery-btn" style="flex:1; padding:10px; border-radius:6px; border: 2px solid #ddd;">
                        <i class="fa fa-image" style="margin-right: 6px;"></i> Galerie
                    </button>
                </div>
                ${generateGalleryHtml(ftResult.files, true)}
            </div>
        `;

        frm.fields_dict.photos.$wrapper.html(html);

        // Bind events
        frm.fields_dict.photos.$wrapper.find('.photos-camera-btn').click(() => open_photo_dialog_ft(frm, true));
        frm.fields_dict.photos.$wrapper.find('.photos-gallery-btn').click(() => open_photo_dialog_ft(frm, false));
        frm.fields_dict.photos.$wrapper.find('.delete-photo-btn').click(function(e) {
            e.preventDefault();
            e.stopPropagation();
            delete_photo_ft(frm, $(this).data('file'));
        });
    });
}

function open_photo_dialog_ft(frm, useCamera = false) {
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
            upload_photos_ft(frm, files);
        }
        $input.remove();
    });

    $input.click();
}

function upload_photos_ft(frm, files) {
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

function delete_photo_ft(frm, file_name) {
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


frappe.ui.form.on('Fiche de travail', {
    timeline_refresh: (frm) => {
        frappe.call({
            method: "ft_timer_html",
            args: {ft: frm.doc.name}
        }).then((r) => {
            var timer_html = frm.get_field('timer_html');
            timer_html.set_value(r.message.html);
        })
    },
    address:function(frm) {
          frappe.contacts.get_address_display(frm)
     },
    refresh: function(frm) {
        // Rendre la galerie photos
        render_photos_section(frm);
        
        if(frm.doc.projet) {
            frm.add_custom_button(__('Événement'), function(){
                frappe.new_doc("Event", { project: frm.doc.project, custom_fiche_de_travail: frm.doc.name });
            }, __("Create"));
		    frappe.db.get_list("Quality Incident", {
                fields: ["name", "object"],
                filters: {
                    project: frm.doc.projet
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
            frm.add_custom_button(__('Incident qualité'), function(){
                frappe.new_doc("Quality Incident", {project: frm.doc.projet, fiche_de_travail: frm.doc.name})
            }, __("Create"));
        }
        
        if(!frappe.is_mobile()) {
            
            frm.add_custom_button(__('Commande fournisseur'), function(){
                frappe.new_doc("Purchase Order", {project: frm.doc.projet, cost_center:frm.doc.cost_center})
            }, __("Create"));

        }
        frm.fields_dict['section_break_1'].wrapper.css('background-color', 'antiquewhite');
        frm.fields_dict['section_break_odzh'].wrapper.css('background-color', 'antiquewhite');
        frm.fields_dict['photos_avant_section'].wrapper.css('background-color', 'antiquewhite');
        frm.fields_dict['travaux_section'].wrapper.css('background-color', 'cadetblue');
        frm.fields_dict['section_break_qjpd'].wrapper.css('background-color', 'cadetblue');
    
        
        
        frm.set_query("team", function(){
            return {
                "filters": [
                    ["Employee", "designation", "in", ["Poseur", "Opérateur atelier"]],
                    ["Employee", "status", "=", "active"],
                    ["Employee", "company", "=", frm.doc.company],
                ]
            }
        });
        
        frm.set_query("visite_technique", function(){
            return {
                "filters": [
                    ["Visite Technique", "projet", "=", frm.doc.projet],
                ]
            }
        });
        
        frappe.db.get_value("Work Completion Receipt", {project: frm.doc.projet, docstatus: 1}, "name").then(r => {
            if(!r.message.name) {
                frm.add_custom_button("✍️",() => {
                    let d = new frappe.ui.Dialog({
                        title: 'Réception de travaux',
                        fields: [
                            {
                                label: 'Client absent',
                                fieldname: 'absent_customer',
                                fieldtype: 'Check',
                            },
                            {
                                label: 'Nom du signataire',
                                fieldname: 'signatory',
                                fieldtype: 'Data',
                                reqd: true,
                            },
                            {
                                label: 'Fait à',
                                fieldname: 'place',
                                fieldtype: 'Data',
                                reqd: true,
                            },
                            {
                                label: 'Signature de la réception des travaux sans réserves',
                                fieldname: 'signature',
                                fieldtype: 'Signature',
                                reqd: true,
                            },
                            {
                                label: 'Notifier par mail',
                                fieldname: 'notify_customer',
                                fieldtype: 'Check',
                                default: 1,
                            },
                        ],
                        size: 'small', // small, large, extra-large 
                        primary_action_label: 'Valider',
                        secondary_action(values) {
                            frappe.new_doc("Work Completion Receipt", {
                                sales_order: frm.doc.sales_order,
                                absent_customer: frm.doc.absent_customer,
                                signature_du_client: values.signature,
                                notify_customer_on_validation: values.notify_customer,
                                fait_à: values.place
                            })
                        },
                        secondary_action_label: "Plus d'options",
                        primary_action(values) {
                            frappe.call({
                                method: 'frappe.client.submit',
                                args: {
                                    doc: {
                                        doctype: "Work Completion Receipt",
                                        absent_customer: values.absent_customer,
                                        fait_à: values.place,
                                        project: frm.doc.projet,
                                        sales_order: frm.doc.sales_order,
                                        customer: frm.doc.customer,
                                        accepted: 1,
                                        signature_du_client: values.signature,
                                        notify_customer_on_validation: values.notify_customer,
                                        signatory: values.signatory
                                    },
                                }}).then(() => {
                                    frappe.show_alert({message: 'Réception de travaux signé', indicator: 'green'}, 5)
                                    frm.set_value("work_completion_receipt_signed", 1);
                                    frm.set_value("status", "Fait");
                                    frm.save()
                                    frm.remove_custom_button('✍️');
                                })
                                
                            d.hide();
                        }
                    });
                    
                    // Ajout de l'événement pour mettre à jour le champ 'signatory'
                    d.fields_dict.absent_customer.$input.on('change', function() {
                        if (d.get_value('absent_customer')) {
                            // Remplacer 'frappe.session.user_fullname' par l'attribut correct pour obtenir le nom de l'employé
                            d.set_value('signatory', frappe.session.user_fullname);
                        } else {
                            d.set_value('signatory', ''); // Efface le champ si la case est décochée
                        }
                    });
                    
                    d.show();
                });
                
            }
            
        })
        
        
        
        frappe.call({
            method: "timesheet_html_block",
        }).then((r) => {
            const m = r.message
            console.log(r.message)
            if(r.message.current_task !== "Day finished") {
                frm.add_custom_button(__('🎯 Démarrer le chronomètre de cette tâche'), function(){
                    startActivity(frm)
                }, '⏱️');
            }
            
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
    
  },
 

});

// Converti depuis le Client Script ERP 'Dépense' (Expense / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Expense', {
    refresh(frm) {
        const wrapper = frm.get_field('receipt_html').$wrapper;
        wrapper.empty();

        const html = `
            <div style="display: flex; flex-direction: column; gap: 16px; align-items: center;">
                <div id="drop-upload" style="border: 2px dashed #aaa; padding: 20px; text-align: center; border-radius: 8px; width: 100%; cursor: pointer;">
                    <input type="file" id="fileInput" style="display: none;" accept="image/*,application/pdf"/>
                    <strong>📁 Déposez un fichier ici ou cliquez pour en choisir un</strong>
                </div>
                <button id="cameraBtn" class="btn btn-primary">
                    📷 Prendre une photo
                </button>
                <input type="file" id="cameraInput" accept="image/*" capture="environment" style="display: none;"/>
            </div>
        `;

        wrapper.html(html);

        const dropZone = wrapper.find('#drop-upload');
        const fileInput = wrapper.find('#fileInput');
        const cameraInput = wrapper.find('#cameraInput');

        dropZone.on('click', () => fileInput[0].click());
        fileInput.on('change', (e) => handleUpload(e.target.files[0]));

        dropZone.on('dragover', (e) => {
            e.preventDefault();
            dropZone.css('background-color', '#f0f0f0');
        });
        dropZone.on('dragleave', () => {
            dropZone.css('background-color', '');
        });
        dropZone.on('drop', (e) => {
            e.preventDefault();
            dropZone.css('background-color', '');
            handleUpload(e.originalEvent.dataTransfer.files[0]);
        });

        wrapper.find('#cameraBtn').on('click', () => cameraInput[0].click());
        cameraInput.on('change', (e) => handleUpload(e.target.files[0]));

        async function handleUpload(file) {
            if (!file) return;

            const formData = new FormData();
            formData.append("file", file, file.name);
            formData.append("is_private", "1");
            formData.append("doctype", frm.doctype);
            formData.append("docname", frm.doc.name);

            try {
                const response = await fetch("/api/method/upload_file", {
                    method: "POST",
                    headers: {
                        "X-Frappe-CSRF-Token": frappe.csrf_token
                    },
                    body: formData
                });

                const data = await response.json();
                const file_doc = data.message;

                frm.set_value("receipt", file_doc.file_url);
                frm.trigger("show_file_preview");

                const has_expense_type = frm.doc.expense_details?.[0]?.expense_type;
                const has_description = frm.doc.expense_details?.[0]?.description;

                const employee = frm.doc.employee;
                let default_cost_center = frm.doc.cost_center || "";
                let cost_center_description = "";

                if (employee) {
                    const r = await frappe.db.get_value("Employee", employee, "payroll_cost_center");
                    if (r.message?.payroll_cost_center) {
                        default_cost_center = r.message.payroll_cost_center;
                        cost_center_description = "👤 Prérempli à partir de la fiche employé";
                    }
                }

                let default_expense_type = has_expense_type || "";

                if (!default_expense_type || !default_cost_center || !has_description) {
                    const dialog = new frappe.ui.Dialog({
                        title: "Informations complémentaires",
                        fields: [
                            {
                                fieldname: "cost_center",
                                label: "Centre de coût",
                                fieldtype: "Link",
                                options: "Cost Center",
                                get_query: () => ({ filters: { is_group: 0 } }),
                                default: default_cost_center,
                                description: cost_center_description
                            },
                            {
                                fieldname: "expense_type",
                                label: "Type de dépense",
                                fieldtype: "Link",
                                options: "Expense Claim Type",
                                reqd: 1,
                                default: default_expense_type
                            },
                            {
                                fieldname: "description",
                                label: "Description",
                                fieldtype: "Small Text"
                            },
                            {
                                fieldname: "project",
                                label: "Projet",
                                fieldtype: "Link",
                                options: "Project"
                            }
                        ],
                        primary_action_label: "Enregistrer",
                        primary_action: async (values) => {
                            if (!values.project && !values.cost_center) {
                                frappe.msgprint("Merci de renseigner un centre de coût.");
                                return;
                            }
                            await frm.set_value("project", values.project);
                            await frm.set_value("cost_center", values.cost_center);

                            if (frm.doc.expense_details.length === 1) {
                                const first_item = frm.doc.expense_details[0];
                                first_item.expense_type = values.expense_type;
                                first_item.description = values.description;
                            }

                            await frm.save();
                            dialog.hide();
                        }
                    });

                    dialog.fields_dict.project.df.onchange = async function () {
                        const project = dialog.get_value("project");
                        if (project) {
                            const r = await frappe.db.get_value("Project", project, "cost_center");
                            if (r?.message?.cost_center) {
                                dialog.set_value("cost_center", r.message.cost_center);
                                dialog.set_df_property("cost_center", "read_only", true);
                                dialog.set_df_property("cost_center", "description", "📁 Centre de coût hérité du projet");
                                dialog.refresh();
                            } else {
                                dialog.set_df_property("cost_center", "read_only", false);
                                dialog.set_df_property("cost_center", "description", "");
                                dialog.refresh();
                            }
                        } else {
                            dialog.set_df_property("cost_center", "read_only", false);
                            dialog.set_df_property("cost_center", "description", "");
                            dialog.refresh();
                        }
                    };

                    dialog.show();
                } else {
                    await frm.save();
                }

            } catch (err) {
                console.error("❌ Erreur upload fichier :", err);
            }
        }
    }
});

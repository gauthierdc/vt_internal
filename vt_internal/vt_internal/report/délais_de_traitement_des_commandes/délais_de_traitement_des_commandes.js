frappe.query_reports["Délais de traitement des commandes"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("Date de début"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -6)
        },
        {
            "fieldname": "to_date",
            "label": __("Date de fin"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "company",
            "label": __("Société"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "cost_center",
            "label": __("Centre de coût"),
            "fieldtype": "Link",
            "options": "Cost Center"
        },
        {
            "fieldname": "project_manager",
            "label": __("Responsable du devis"),
            "fieldtype": "Link",
            "options": "User"
        },
        {
            "fieldname": "secteur_vt",
            "label": __("Secteur"),
            "fieldtype": "Link",
            "options": "Secteur VT"
        },
        {
            "fieldname": "customer_group",
            "label": __("Groupe client"),
            "fieldtype": "Link",
            "options": "Customer Group"
        },
        {
            "fieldname": "construction_manager",
            "label": __("Responsable chantier"),
            "fieldtype": "Link",
            "options": "User"
        },
        {
            "fieldname": "project_type",
            "label": __("Type de projet"),
            "fieldtype": "Link",
            "options": "Project Type"
        }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        let fieldname = column.fieldname;
        let raw_value = data[fieldname];

        if (fieldname === "project_name" && data && data.project) {
            return `<a href="#" onclick="openProjectDetails('${data.project}'); return false;">${data.project_name || data.project}</a>`;
        }

        value = default_formatter(value, row, column, data);

        const duration_fields = [
            "j_devis_commande", "j_commande_reception",
            "j_reception_facture", "j_facture_paiement", "j_total"
        ];

        const thresholds = {
            "j_devis_commande": { warn: 7, alert: 14 },
            "j_commande_reception": { warn: 14, alert: 21 },
            "j_reception_facture": { warn: 7, alert: 14 },
            "j_facture_paiement": { warn: 14, alert: 30 },
            "j_total": { warn: 30, alert: 45 }
        };

        if (duration_fields.includes(fieldname) && typeof raw_value === "number" && raw_value !== null) {
            let t = thresholds[fieldname];
            let color = "#27ae60";
            if (raw_value >= t.alert) {
                color = "#e74c3c";
            } else if (raw_value >= t.warn) {
                color = "#f39c12";
            }
            value = `<span style="color: ${color}; font-weight: bold;">${raw_value}</span>`;
        }

        return value;
    }
};

window.openProjectDetails = function(project) {
    const dialog = new frappe.ui.Dialog({
        size: "extra-large",
        title: __("Détails du projet"),
        fields: [{ fieldname: "content", fieldtype: "HTML" }],
        primary_action: function() {
            frappe.set_route("Form", "Project", project);
        },
        primary_action_label: __("Ouvrir le projet"),
    });

    frappe.call({
        method: "vt_internal.vt_internal.api.project_details.project_details",
        args: { project: project }
    }).then((r) => dialog.fields_dict.content.$wrapper.html(r.message.html));

    dialog.show();
};

frappe.query_reports["VT Margin Report"] = {
    "filters": [
        {
            "fieldname": "grouped_by",
            "label": __("Groupé par"),
            "fieldtype": "Select",
            "options": ["Project", "Company", "Cost Center", "Assurance", "Type de projet", "Secteur VT"],
            "default": "Project",
            "reqd": 1
        },
        {
            "fieldname": "analysis_axis",
            "label": __("Axe d'analyse"),
            "fieldtype": "Select",
            "options": ["Marge globale", "Temps passé", "Achats"],
            "default": "Marge globale",
            "reqd": 1
        },
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "project",
            "label": __("Project"),
            "fieldtype": "Link",
            "options": "Project"
        },
        {
            "fieldname": "cost_center",
            "label": __("Cost Center"),
            "fieldtype": "Link",
            "options": "Cost Center"
        },
        {
            "fieldname": "insurance",
            "label": __("Assurance"),
            "fieldtype": "Link",
            "options": "Customer",
            "filters": {
                "customer_group": "Assurance"
            }
        },
        {
            "fieldname": "project_type",
            "label": __("Type de projet"),
            "fieldtype": "Link",
            "options": "Project Type"
        },
        {
            "fieldname": "secteur_vt",
            "label": __("Secteur VT"),
            "fieldtype": "Link",
            "options": "Secteur VT"
        },
        {
            "fieldname": "quotation_owner",
            "label": __("Responsable du devis"),
            "fieldtype": "Link",
            "options": "User"
        },
        {
            "fieldname": "from_date",
            "label": __("Date de début"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("Date de fin"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "range",
            "label": __("Plage"),
            "fieldtype": "Select",
            "options": ["Mensuel", "Trimestriel", "Annuel"],
            "default": "Mensuel"
        },
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        let fieldname = column.fieldname;
        let raw_value = data[fieldname];

        if ((fieldname.endsWith('_diff') || fieldname === 'total_diff') && typeof raw_value === 'number') {
            if (!window.vt_margin_computed) {
                window.vt_margin_computed = true;
                window.column_min_neg = {};
                window.column_max_pos = {};
                frappe.query_report.columns.forEach(function(col) {
                    let fn = col.fieldname;
                    if (fn.endsWith('_diff') || fn === 'total_diff') {
                        let values = frappe.query_report.data
                            .map(row => row[fn])
                            .filter(v => typeof v === 'number' && !isNaN(v));
                        if (values.length > 0) {
                            let negs = values.filter(v => v < 0);
                            let poss = values.filter(v => v > 0);
                            window.column_min_neg[fn] = negs.length > 0 ? Math.min(...negs) : 0;
                            window.column_max_pos[fn] = poss.length > 0 ? Math.max(...poss) : 0;
                        }
                    }
                });
            }

            let color = 'black';
            if (raw_value !== 0) {
                let intensity = 0;
                let hue = 0;
                let lightness = 50; // Default

                if (raw_value < 0) {
                    let min_neg = window.column_min_neg[fieldname];
                    intensity = (min_neg < 0) ? Math.abs(raw_value / min_neg) : 1;
                    hue = 0; // Red
                } else if (raw_value > 0) {
                    let max_pos = window.column_max_pos[fieldname];
                    intensity = (max_pos > 0) ? (raw_value / max_pos) : 1;
                    hue = 120; // Green
                }

                intensity = Math.min(1, Math.max(0, intensity));
                lightness = 25 + 25 * intensity; // From 25% (dark near 0) to 50% (lighter for large magnitudes)
                color = `hsl(${hue}, 100%, ${lightness}%)`;
            }

            value = `<span style="color: ${color};">${value}</span>`;
        }

        return value;
    },
    "refresh": function(report) {
        // Reset the computation flag and clear caches when filters are changed
        window.vt_margin_computed = false;
        window.column_min_neg = {};
        window.column_max_pos = {};
    }
};
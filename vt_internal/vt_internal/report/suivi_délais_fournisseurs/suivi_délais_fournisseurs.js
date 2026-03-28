frappe.query_reports["Suivi délais fournisseurs"] = {
    "filters": [
        {
            "fieldname": "supplier",
            "label": __("Fournisseur"),
            "fieldtype": "Link",
            "options": "Supplier"
        },
        {
            "fieldname": "from_date",
            "label": __("Date de début"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -3)
        },
        {
            "fieldname": "to_date",
            "label": __("Date de fin"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        },
        {
            "fieldname": "status",
            "label": __("Statut"),
            "fieldtype": "Select",
            "options": "\nTo Receive and Bill\nTo Bill\nCompleted\nClosed"
        },
        {
            "fieldname": "company",
            "label": __("Société"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
        }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (data && data[column.fieldname] !== null && data[column.fieldname] !== undefined) {
            let raw = data[column.fieldname];
            let color;

            if (column.fieldname === "delta_confirmation_schedule") {
                // positif = engagement APRÈS la date demandée = mauvais
                if (raw <= 0) {
                    color = "#27ae60";
                } else if (raw <= 7) {
                    color = "#f39c12";
                } else {
                    color = "#e74c3c";
                }
            } else if (column.fieldname === "delta_confirmation_receipt") {
                // positif = reçu APRÈS la date confirmée = retard
                if (raw <= 0) {
                    color = "#27ae60";
                } else if (raw <= 7) {
                    color = "#f39c12";
                } else {
                    color = "#e74c3c";
                }
            } else {
                return value;
            }

            value = `<span style="color: ${color}; font-weight: bold;">${raw > 0 ? "+" : ""}${raw}j</span>`;
        }

        return value;
    }
};

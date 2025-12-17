// Copyright (c) 2025, Verre & Transparence and contributors
// For license information, please see license.txt

frappe.query_reports["Objectifs commerciaux VT"] = {
	onload: function(report) {
		// Set current user as default
		report.set_filter_value("user", [frappe.session.user]);
	},
	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		// Color realized amounts based on objective comparison
		if (column.fieldname === "quotation_amount") {
			const objective = data.quotation_objective || 0;
			const realized = data.quotation_amount || 0;
			if (objective > 0) {
				const color = realized >= objective ? "#2e7d32" : "#c62828";
				value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
			}
		}
		else if (column.fieldname === "order_amount") {
			const objective = data.order_objective || 0;
			const realized = data.order_amount || 0;
			if (objective > 0) {
				const color = realized >= objective ? "#2e7d32" : "#c62828";
				value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
			}
		}
		else if (column.fieldname === "invoice_amount") {
			const objective = data.invoice_objective || 0;
			const realized = data.invoice_amount || 0;
			if (objective > 0) {
				const color = realized >= objective ? "#2e7d32" : "#c62828";
				value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
			}
		}

		return value;
	},
	filters: [
		{
			"fieldname": "user",
			"label": __("Utilisateur"),
			"fieldtype": "MultiSelectList",
			"reqd": 1,
			"get_data": function(txt) {
				return frappe.db.get_link_options("User", txt);
			},
		},
		{
			"fieldname": "fiscal_year",
			"label": __("Année fiscale"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("fiscal_year"),
		},
		{
			"fieldname": "range",
			"label": __("Grouper par"),
			"fieldtype": "Select",
			"options": "Semaine\nMois\nTrimestre",
			"default": "Mois",
		},
		{
			"fieldname": "cumulative",
			"label": __("Valeurs accumulées"),
			"fieldtype": "Check",
			"default": 1,
		},
	],
};

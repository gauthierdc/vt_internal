// Copyright (c) 2025, Verre & Transparence and contributors
// For license information, please see license.txt

frappe.query_reports["Performance Commerciale"] = {
	filters: [
		{
			fieldname: "fiscal_year",
			label: __("Année"),
			fieldtype: "Link",
			options: "Fiscal Year",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[0],
			reqd: 1,
			on_change: function(report) {
				report.refresh();
			}
		},
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
			on_change: function(report) {
				// Reset cost_center when company changes
				report.set_filter_value("cost_center", "");
				report.refresh();
			}
		},
		{
			fieldname: "cost_center",
			label: __("Centre de coût"),
			fieldtype: "Link",
			options: "Cost Center",
			get_query: function() {
				const company = frappe.query_report.get_filter_value("company");
				return {
					filters: {
						company: company
					}
				};
			},
			on_change: function(report) {
				report.refresh();
			}
		},
		{
			fieldname: "view_type",
			label: __("Vue"),
			fieldtype: "Select",
			options: [
				"Secteur / Centre de coût",
				"Centre de coût / Secteur",
				"Groupe de client"
			],
			default: "Secteur / Centre de coût",
			reqd: 1,
			on_change: function(report) {
				report.refresh();
			}
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		// Coloration du taux de transformation
		if (column.fieldname === "taux_transfo") {
			const raw_value = data.taux_transfo;
			if (typeof raw_value === "number") {
				let color;
				if (raw_value >= 50) {
					color = "green";
				} else if (raw_value >= 25) {
					color = "orange";
				} else {
					color = "red";
				}
				value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
			}
		}

		// Coloration de la marge
		if (column.fieldname === "marge_pct") {
			const raw_value = data.marge_pct;
			if (typeof raw_value === "number") {
				let color;
				if (raw_value >= 30) {
					color = "green";
				} else if (raw_value >= 15) {
					color = "orange";
				} else {
					color = "red";
				}
				value = `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
			}
		}

		// Style pour les lignes parentes (indent = 0)
		if (data.indent === 0 && data.entity !== "TOTAL") {
			value = `<strong>${value}</strong>`;
		}

		// Style pour la ligne TOTAL
		if (data.entity === "TOTAL") {
			value = `<strong style="font-size: 1.1em;">${value}</strong>`;
		}

		return value;
	},

	tree: true,
	name_field: "entity",
	parent_field: "parent_entity",
	initial_depth: 0
};

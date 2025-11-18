// Copyright (c) 2025, Verre & Transparence and contributors
// For license information, please see license.txt

frappe.query_reports["👷Chantiers"] = {

	filters: [
		{
			"fieldname": "date",
			"label": __("Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
		},
	],
};

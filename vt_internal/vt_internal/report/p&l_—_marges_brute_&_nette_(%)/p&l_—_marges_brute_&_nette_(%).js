// Copyright (c) 2025, Verre & Transparence and contributors
// For license information, please see license.txt


frappe.query_reports["P&L — Marges brute & nette (%)"] = $.extend(
	{},
	erpnext.financial_statements
);

frappe.query_reports["P&L — Marges brute & nette (%)"]["filters"].push(
	{
		"fieldname": "accumulated_values",
		"label": __("Accumulated Values"),
		"fieldtype": "Check"
	}
);



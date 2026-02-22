// Copyright (c) 2025, Verre & Transparence and contributors
// For license information, please see license.txt

frappe.query_reports["Previsionnel Chantier"] = {
	filters: [
		{
			fieldname: "start_date",
			label: __("Date de début"),
			fieldtype: "Date",
			default: get_next_week_start(),
			reqd: 1
		},
		{
			fieldname: "end_date",
			label: __("Date de fin"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(get_next_week_start(), 4),
			reqd: 1
		},
		{
			fieldname: "grouped_by",
			label: __("Groupé par"),
			fieldtype: "Select",
			options: ["Projet", "Employé"],
			default: "Projet",
			reqd: 1
		},
		{
			fieldname: "project_type",
			label: __("Type de projet"),
			fieldtype: "Link",
			options: "Project Type"
		},
		{
			fieldname: "employee",
			label: __("Employé"),
			fieldtype: "Link",
			options: "Employee"
		},
		{
			fieldname: "construction_manager",
			label: __("Conducteur de travaux"),
			fieldtype: "Link",
			options: "User"
		}
	],

	formatter: function(value, row, column, data, default_formatter) {
		let html = default_formatter(value, row, column, data);

		if (column.fieldname === "heures_prevues" && value) {
			const hours = parseFloat(value);
			if (hours > 40) {
				html = `<span style="color: #c62828; font-weight: bold;">${value}h</span>`;
			} else if (hours > 20) {
				html = `<span style="color: #f57c00;">${value}h</span>`;
			} else {
				html = `<span style="color: #2e7d32;">${value}h</span>`;
			}
		}

		return html;
	}
};

function get_next_week_start() {
	const today = frappe.datetime.get_today();
	const date = new Date(today);
	const dayOfWeek = date.getDay();
	const daysUntilMonday = dayOfWeek === 0 ? 1 : 8 - dayOfWeek;
	return frappe.datetime.add_days(today, daysUntilMonday);
}

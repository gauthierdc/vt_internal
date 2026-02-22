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
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company"
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

		// Rendre le projet cliquable pour ouvrir la modale
		if (column.fieldname === "project" && value && data) {
			html = `<a href="#" onclick="openProjectDetails('${data.project}'); return false;">${value}</a>`;
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

// Fonction globale pour ouvrir la modale des détails du projet
window.openProjectDetails = function(project) {
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
			frappe.set_route('Form', "Project", project);
		},
		primary_action_label: __("Projet"),
	});

	frappe.call({
		method: "vt_internal.vt_internal.api.project_details.project_details",
		args: { project: project }
	}).then((r) => dialog.fields_dict.content.$wrapper.html(r.message.html));

	dialog.show();
};

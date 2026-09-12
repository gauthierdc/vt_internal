// Copyright (c) 2025, Dokos SAS and contributors
// For license information, please see license.txt

const ORDER_BOOK_STANDARD_EXCLUDE = new Set([
	"status",
	"transaction_date",
	"per_billed",
	"cost_center",
	"company",
	"custom_construction_manager",
]);

frappe.query_reports["Order book"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Société"),
			fieldtype: "Link",
			options: "Company",
		},
		{
			fieldname: "cost_center",
			label: __("Centre de coût"),
			fieldtype: "Link",
			options: "Cost Center",
		},
		{
			fieldname: "construction_managers",
			label: __("Responsables de chantiers"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("User", txt);
			},
		},
		// Standard Sales Order filters planners already rely on
		// (status / per_billed handled server-side; manager is the multi-select above).
		...frappe.get_meta("Sales Order").fields
			.filter((df) => df.in_standard_filter && !ORDER_BOOK_STANDARD_EXCLUDE.has(df.fieldname))
			.map((df) => ({
				fieldname: df.fieldname,
				label: __(df.label),
				fieldtype: df.fieldtype,
				options: df.options,
				default: df.default,
			})),
	],
	formatter: function (value, row, column, data, default_formatter) {
		let html = default_formatter(value, row, column, data);
		if (column.fieldname === "name" && value && data && data.project) {
			html = `<a href="#" onclick="openProjectDetails('${data.project}'); return false;">${value}</a>`;
		}
		if (column.fieldname === "age" && value != null) {
			let color = value < 30 ? "green" : value < 100 ? "orange" : "red";
			html = `<span style="color:${color}">${value}</span>`;
		}
		if (column.fieldname === "hours_solde" && value != null && data) {
			const color = value < 0 ? "#c62828" : value === 0 ? "#2e7d32" : "#333";
			html = `<span style="color:${color}; font-weight:${value < 0 ? "bold" : "normal"}">${value}</span>`;
		}
		if (column.fieldname === "status" && data) {
			const get_indicator = frappe.listview_settings["Sales Order"]?.get_indicator;
			if (get_indicator) {
				const indicator = get_indicator(data);
				if (indicator) {
					const [label, color] = indicator;
					html = `<span class="indicator-pill ${color}">${label}</span>`;
				}
			}
		}
		if (column.fieldname === "custom_construction_status" && data) {
			const display = value
				? value.replace(/\n/g, "<br>")
				: '<em style="color:#888">Cliquer pour modifier</em>';
			html = `<div class="editable-construction-status" data-name="${data.name}" style="cursor:pointer; min-height:20px;">${display}</div>`;
		}
		// Server already built clickable HTML; do not escape.
		if (column.fieldname === "pending_arcs" || column.fieldname === "evenements") {
			return value || "";
		}
		return html;
	},
	onload: function (report) {
		report.page.add_inner_button(__("Ouvrir la page Carnet de commande"), () => {
			frappe.set_route("carnet-de-commande");
		});
		report.$report.on("click", ".editable-construction-status", function () {
			const name = $(this).data("name");
			const current_value =
				$(this).text() === "Cliquer pour modifier" ? "" : $(this).html().replace(/<br>/g, "\n");

			const d = new frappe.ui.Dialog({
				title: __("Modifier le statut construction"),
				fields: [
					{
						fieldname: "status",
						fieldtype: "Small Text",
						label: __("Statut construction"),
						default: current_value,
					},
				],
				primary_action_label: __("Enregistrer"),
				primary_action(values) {
					frappe.call({
						method: "frappe.client.set_value",
						args: {
							doctype: "Sales Order",
							name: name,
							fieldname: "custom_construction_status",
							value: values.status,
						},
						callback: () => {
							frappe.show_alert({ message: __("Statut mis à jour"), indicator: "green" });
							report.refresh();
						},
					});
					d.hide();
				},
			});
			d.show();
		});
	},
};

if (!window.openProjectDetails) {
	window.openProjectDetails = function (project) {
		const dialog = new frappe.ui.Dialog({
			size: "extra-large",
			title: __("Details du projet"),
			fields: [{ fieldname: "content", fieldtype: "HTML" }],
			primary_action: function () {
				frappe.set_route("Form", "Project", project);
			},
			primary_action_label: __("Projet"),
		});

		frappe
			.call({
				method: "vt_internal.vt_internal.api.project_details.project_details",
				args: { project: project },
			})
			.then((r) => dialog.fields_dict.content.$wrapper.html(r.message.html));

		dialog.show();
	};
}

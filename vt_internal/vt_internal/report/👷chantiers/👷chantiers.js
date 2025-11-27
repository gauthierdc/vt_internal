// Copyright (c) 2025, Verre & Transparence and contributors
// For license information, please see license.txt

frappe.query_reports["👷Chantiers"] = {

	filters: [
		{
			"fieldname": "start_date",
			"label": __("Date de début"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -7),
			"reqd": 1,
		},
		{
			"fieldname": "end_date",
			"label": __("Date de fin"),
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
		{
			"fieldname": "only_completed",
			"label": __("Facturé uniquement"),
			"fieldtype": "Check",
			"default": 0,
		},
		{
			"fieldname": "project_type",
			"label": __("Type de projet"),
			"fieldtype": "MultiSelectList",
			"get_data": function(txt) {
				return frappe.db.get_link_options("Project Type", txt);
			},
		},
	],

	formatter: function(value, row, column, data, default_formatter) {
		const originalValue = value;

		// Colonne Marge % combinée (prévu|réel|écart)
		if (column.label === "Marge %" && originalValue && originalValue.includes("|")) {
			const parts = originalValue.split("|");
			const prev = parseInt(parts[0]) || 0;
			const reel = parseInt(parts[1]) || 0;
			const ecart = parseInt(parts[2]) || 0;
			let arrow, arrowColor;
			if (ecart === 0) {
				arrow = "=";
				arrowColor = "#666";
			} else if (ecart > 0) {
				arrow = "↗";
				arrowColor = "#2e7d32";
			} else {
				arrow = "↘";
				arrowColor = "#c62828";
			}
			const ecartBg = ecart >= 0 ? "#c8e6c9" : "#ffcdd2";
			const ecartSign = ecart > 0 ? "+" : "";
			return `<div style="display: flex; align-items: center; gap: 6px;">
				<span style="color: #666; font-size: 11px;">${prev}%</span>
				<span style="color: ${arrowColor}; font-weight: bold;">${arrow}</span>
				<span style="font-weight: bold;">${reel}%</span>
				<span style="background: ${ecartBg}; padding: 1px 5px; border-radius: 3px; font-size: 11px; font-weight: bold;">${ecartSign}${ecart}</span>
			</div>`;
		}

		// Colonne Heures combinée (réel|prévu|écart)
		if (column.label === "Heures" && originalValue && originalValue.includes("|")) {
			const parts = originalValue.split("|");
			const reel = parseInt(parts[0]) || 0;
			const prev = parseInt(parts[1]) || 0;
			const ecart = parseInt(parts[2]) || 0;
			let arrow, arrowColor;
			if (ecart === 0) {
				arrow = "=";
				arrowColor = "#666";
			} else if (ecart < 0) {
				arrow = "↘";
				arrowColor = "#2e7d32";
			} else {
				arrow = "↗";
				arrowColor = "#c62828";
			}
			const ecartBg = ecart <= 0 ? "#c8e6c9" : "#ffcdd2";
			const ecartSign = ecart > 0 ? "+" : "";
			return `<div style="display: flex; align-items: center; gap: 6px;">
				<span style="color: #666; font-size: 11px;">${prev}h</span>
				<span style="color: ${arrowColor}; font-weight: bold;">${arrow}</span>
				<span style="font-weight: bold;">${reel}h</span>
				<span style="background: ${ecartBg}; padding: 1px 5px; border-radius: 3px; font-size: 11px; font-weight: bold;">${ecartSign}${ecart}</span>
			</div>`;
		}

		return default_formatter(value, row, column, data);
	},
};

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

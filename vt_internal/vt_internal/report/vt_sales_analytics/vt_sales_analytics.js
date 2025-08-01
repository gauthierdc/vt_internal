// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


frappe.query_reports["VT Sales Analytics"] = {
	"filters": [
		{
			fieldname: "tree_type",
			label: __("Tree Type"),
			fieldtype: "Select",
			options: ["Customer Group", "Customer", "Secteur VT", "Item Group", "Item", "Territory", "Order Type", "Project", "Par verre", "Assurance", "Origine", "Responsable du devis"],
			default: "Customer",
			reqd: 1,
			on_change: function(report) {
				var tree_type = this.value;
				var vq_filter = report.get_filter("value_quantity");
				if (tree_type === "Par verre") {
					vq_filter.df.options = [
						{ "value": "Value", "label": __("Value") },
						{ "value": "Quantity", "label": "m²" },
					];
				} else {
					vq_filter.df.options = [
						{ "value": "Value", "label": __("Value") },
						{ "value": "Quantity", "label": __("Quantity") },
					];
				}
				vq_filter.refresh();
				vq_filter.set_input(vq_filter.value);
				report.refresh(); // Ajout : recharge le rapport quand tree_type change
			}
		},
		{
			fieldname: "secteur",
			label: __("Secteur"),
			fieldtype: "Link",
			options: "Secteur VT"
		},
		{
			fieldname: "cost_center",
			label: __("Centre de coût"),
			fieldtype: "Link",
			options: "Cost Center"
		},
		{
			fieldname: "value_quantity",
			label: __("Value Or Qty"),
			fieldtype: "Select",
			options: [
				{ "value": "Value", "label": __("Value") },
				{ "value": "Quantity", "label": __("Quantity") },
			],
			default: "Value",
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			reqd: 1
		},
		{
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
			reqd: 1
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
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
			fieldname: "range",
			label: __("Range"),
			fieldtype: "Select",
			options: [
				{ "value": "Weekly", "label": __("Weekly") },
				{ "value": "Monthly", "label": __("Monthly") },
				{ "value": "Quarterly", "label": __("Quarterly") },
				{ "value": "Yearly", "label": __("Yearly") }
			],
			default: "Monthly",
			reqd: 1
		},
		{
			fieldname: "custom_responsable_du_devis",
			label: __("Responsable du devis"),
			fieldtype: "Link",
			options: "User"
		}
	],
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
			events: {
				onCheckRow: function (data) {
					if (!data) return;
					const data_doctype = $(
						data[2].html
					)[0].attributes.getNamedItem("data-doctype").value;
					const tree_type = frappe.query_report.filters[0].value;
					if (data_doctype != tree_type && tree_type != "Par verre" && tree_type != "Responsable du devis") return;

					const row_name = data[2].content;
					const raw_data = frappe.query_report.chart.data;
					const new_datasets = raw_data.datasets;
					const element_found = new_datasets.some(
						(element, index, array) => {
							if (element.name == row_name) {
								array.splice(index, 1);
								return true;
							}
							return false;
						}
					);
					const slice_at = { Customer: 4, Item: 5 }[tree_type] || 3;

					if (!element_found) {
						new_datasets.push({
							name: row_name,
							values: data
								.slice(slice_at, data.length - 1)
								.map(column => column.content),
						});
					}

					const new_data = {
						labels: raw_data.labels,
						datasets: new_datasets,
					};
					const new_options = Object.assign({}, frappe.query_report.chart_options, {data: new_data});
					frappe.query_report.render_chart(new_options);

					frappe.query_report.raw_chart_data = new_data;
				},
			},
		});
	},
};
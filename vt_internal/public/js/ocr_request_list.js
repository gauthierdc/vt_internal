// Converti depuis le Client Script ERP 'OCR Request list' (OCR Request / List).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.listview_settings["OCR Request"] = {
    onload : function(listview) {
	    
	    cur_list.columns.push({
				type: "Field",
				df: {
					label: __("Créé le"),
					fieldname: "creation",
				},
			});
		cur_list.refresh(true)
	},
    
	hide_name_column: 1,
	button: {
		show(doc) {
			return (doc.transaction_type && (doc.status === "Completed" || doc.status === "Purchase Order Created"));
		},
		get_label() {
			return frappe.utils.icon("link-url", "sm");
		},
		get_description(doc) {
			return __("View {0}", [__(doc.transaction_type)]);
		},
		action(doc) {
			frappe.db.get_value("Purchase Order", {"ocr_request": doc.name}, "name", r => {
				if (r.name) {
					frappe.set_route("Form", "Purchase Order", r.name);
				} else {
					frappe.show_alert({
						indicator: "red",
						message: __("Transaction could not be found")
					})
				}
			})
		},
	},
};

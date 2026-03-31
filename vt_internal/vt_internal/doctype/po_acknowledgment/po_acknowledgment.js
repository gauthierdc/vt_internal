// Copyright (c) 2026, Verre & Transparence and contributors
// For license information, please see license.txt

frappe.ui.form.on("PO Acknowledgment", {
	refresh: function (frm) {
		if (frm.doc.communication && !frm.is_new()) {
			frm.add_custom_button(__("Voir l'email source"), function () {
				frappe.set_route("Form", "Communication", frm.doc.communication);
			}, __("Actions"));
		}

		if (frm.doc.purchase_order && !frm.is_new()) {
			frm.add_custom_button(__("Voir le bon de commande"), function () {
				frappe.set_route("Form", "Purchase Order", frm.doc.purchase_order);
			}, __("Actions"));
		}
	},

	purchase_order: function (frm) {
		if (["Ignored", "Not found"].includes(frm.doc.status)) return;
		if (frm.doc.purchase_order && frm.doc.status === "New") {
			frm.set_value("status", "Matched");
		}
		if (!frm.doc.purchase_order && frm.doc.status === "Matched") {
			frm.set_value("status", "New");
		}
	},
});

frappe.listview_settings["PO Acknowledgment"] = {
	add_fields: ["status", "supplier", "purchase_order", "sender_email"],

	get_indicator: function (doc) {
		const map = {
			New: [__("Nouveau"), "blue", "status,=,New"],
			Matched: [__("Lié"), "green", "status,=,Matched"],
			Ignored: [__("Ignoré"), "grey", "status,=,Ignored"],
			"Not found": [__("Introuvable"), "red", "status,=,Not found"],
		};
		return map[doc.status] || [doc.status, "grey", `status,=,${doc.status}`];
	},

	button: {
		show: function (doc) {
			return !!doc.purchase_order;
		},
		get_label: function () {
			return __("BC");
		},
		get_description: function (doc) {
			return doc.purchase_order;
		},
		action: function (doc) {
			frappe.set_route("Form", "Purchase Order", doc.purchase_order);
		},
	},
};

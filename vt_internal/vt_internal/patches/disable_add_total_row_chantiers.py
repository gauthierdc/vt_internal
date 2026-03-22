import frappe


def execute():
	frappe.db.set_value("Report", "👷Chantiers", "add_total_row", 0, update_modified=False)

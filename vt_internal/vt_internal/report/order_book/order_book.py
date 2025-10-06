# Copyright (c) 2025, Dokos SAS and contributors
# For license information, please see license.txt

# Import frappe for database operations
import frappe
from frappe import _
from frappe.utils import getdate, nowdate


def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	This is the main entry point for the report. It accepts the filters as a
	dictionary and should return columns and data. It is called by the framework
	every time the report is refreshed or a filter is updated.
	"""
	columns = get_columns()
	data = get_data(filters)
	# Compute total HT for report summary
	total_ht = sum(row[7] for row in data)
	report_summary = [
		{ "value": len(data), "label": _("Nombre de commande"), "datatype": "Int" },
		{ "value": total_ht, "label": _("Total HT"), "datatype": "Currency" }
	]
	return columns, data, None, None, report_summary


def get_columns() -> list[dict]:
	"""Return columns for the report."""
	return [
		{"label": _("Désignation"),            "fieldname": "name",               "fieldtype": "Link",     "options": "Sales Order", "width": 150},
		{"label": _("Statut"),                 "fieldname": "status",             "fieldtype": "Data",     "width": 120},
		{"label": _("Date"),                   "fieldname": "transaction_date",   "fieldtype": "Date",     "width": 100},
		{"label": _("Age"),                    "fieldname": "age",                "fieldtype": "Int",      "width": 80},
		{"label": _("Date de livraison"),      "fieldname": "delivery_date",      "fieldtype": "Date",     "width": 100},
		{"label": _("Référence pièce"),        "fieldname": "reference_piece",              "fieldtype": "Data",     "width": 120},
		{"label": _("Responsable du devis"),   "fieldname": "custom_responsable_du_devis", "fieldtype": "Link", "options": "User", "width": 150},
		{"label": _("Total (HT)"),             "fieldname": "total",              "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Pourcentage facturé"),    "fieldname": "per_billed",         "fieldtype": "Percent",  "width": 100},
		{"label": _("Montant restant (HT)"),   "fieldname": "remaining_amount",   "fieldtype": "Currency", "options": "currency","width": 150},
	]


def get_data(filters: dict | None = None) -> list[list]:
	"""Return data for the report, applying the selected filters and computing age and remaining amount."""
	filters = filters or {}
	# Always exclude closed orders and orders fully billed
	filters.update({"status": ["!=" , "Closed"], "per_billed": ["<", 100]})
	orders = frappe.get_all(
		"Sales Order",
		fields=["name", "status", "transaction_date", "delivery_date",
				"reference_piece", "custom_responsable_du_devis", "total", "per_billed"],
		filters=filters,
		order_by="transaction_date desc"
	)
	today = getdate(nowdate())
	data = []
	for order in orders:
		txn_date = order.get("transaction_date")
		age = (today - getdate(txn_date)).days if txn_date else None
		total = order.get("total") or 0
		per_billed = order.get("per_billed") or 0
		remaining = total - (total * per_billed / 100)
		data.append([
			order.get("name"),
			_(order.get("status")),
			txn_date,
			age,
			order.get("delivery_date"),
			order.get("reference_piece"),
			order.get("custom_responsable_du_devis"),
			total,
			per_billed,
			remaining
		])
	return data

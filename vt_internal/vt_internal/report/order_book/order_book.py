# Copyright (c) 2025, Dokos SAS and contributors
# For license information, please see license.txt

# Import frappe for database operations
import json
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import escape_html, format_date, getdate, nowdate


def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	This is the main entry point for the report. It accepts the filters as a
	dictionary and should return columns and data. It is called by the framework
	every time the report is refreshed or a filter is updated.
	"""
	columns = get_columns()
	data = get_data(filters)
	# Compute remaining amount (HT) and total hours for report summary
	remaining_ht = sum((row.get("remaining_amount") or 0) for row in data)
	total_hours = sum((row.get("custom_labour_hours") or 0) for row in data)
	report_summary = [
		{"value": len(data), "label": _("Nombre de commande"), "datatype": "Int"},
		{"value": total_hours, "label": _("Heures"), "datatype": "Float"},
		{"value": remaining_ht, "label": _("Reste à facturer (HT)"), "datatype": "Currency"},
	]
	return columns, data, None, None, report_summary


def get_columns() -> list[dict]:
	"""Return columns for the report."""
	return [
		{"label": _("Désignation"), "fieldname": "name", "fieldtype": "Link", "options": "Sales Order", "width": 150},
		# Client = Customer.customer_name (UI label « Désignation »), not Sales Order.customer (ID).
		{"label": _("Client"), "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
		{"label": _("Statut"), "fieldname": "status", "fieldtype": "Data", "width": 150},
		{"label": _("Statut du chantier"), "fieldname": "custom_construction_status", "fieldtype": "Small Text", "width": 200},
		{"label": _("Date"), "fieldname": "transaction_date", "fieldtype": "Date", "width": 100},
		{"label": _("Age (J)"), "fieldname": "age", "fieldtype": "Int", "width": 80},
		{"label": _("Date de livraison"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Purchase Orders"),
			"fieldname": "purchase_orders",
			"fieldtype": "HTML",
			"width": 240,
		},
		{"label": _("Référence pièce"), "fieldname": "reference_piece", "fieldtype": "Data", "width": 120},
		{"label": _("Responsable du devis"), "fieldname": "custom_responsable_du_devis", "fieldtype": "Link", "options": "User", "width": 150},
		{"label": _("Nombre d'heures"), "fieldname": "custom_labour_hours", "fieldtype": "Float", "width": 120},
		{"label": _("Total (HT)"), "fieldname": "total", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Pourcentage facturé"), "fieldname": "per_billed", "fieldtype": "Percent", "width": 100},
		{"label": _("Reste à facturer (HT)"), "fieldname": "remaining_amount", "fieldtype": "Currency", "options": "currency", "width": 150},
		{"label": _("Événements"), "fieldname": "evenements", "fieldtype": "HTML", "width": 300},
		# Hidden columns for get_indicator
		{"fieldname": "per_delivered", "fieldtype": "Percent", "hidden": 1},
		{"fieldname": "skip_delivery_note", "fieldtype": "Check", "hidden": 1},
		{"fieldname": "grand_total", "fieldtype": "Currency", "hidden": 1},
		{"fieldname": "custom_statut_fiche_de_travail", "fieldtype": "Data", "hidden": 1},
		{"fieldname": "custom_per_received", "fieldtype": "Percent", "hidden": 1},
		{"fieldname": "custom_payment_request_status", "fieldtype": "Data", "hidden": 1},
		{"fieldname": "project", "fieldtype": "Link", "options": "Project", "hidden": 1},
	]


def get_data(filters: dict | None = None) -> list[dict]:
	"""Return data for the report, applying the selected filters and computing age and remaining amount."""
	query_filters = filters or {}

	# Handle cost_center filter with descendants operator
	if query_filters.get("cost_center"):
		query_filters["cost_center"] = ["descendants of (inclusive)", query_filters["cost_center"]]

	# Always exclude closed orders, cancelled orders, fully billed orders and excluded from statistics
	query_filters.update({
		"status": ["!=", "Closed"],
		"per_billed": ["<", 100],
		"docstatus": ["!=", 2],
		"custom_exclude_from_statistics": ["!=", 1]
	})
	orders = frappe.get_list(
		"Sales Order",
		fields=["name", "customer", "customer_name", "status", "transaction_date", "delivery_date",
				"reference_piece", "custom_responsable_du_devis", "custom_labour_hours", "total", "per_billed",
				"custom_construction_status",
				"per_delivered", "skip_delivery_note", "grand_total",
				"custom_statut_fiche_de_travail", "custom_per_received", "custom_payment_request_status",
				"project"],
		filters=query_filters,
		order_by="transaction_date desc"
	)
	project_names = list({o.get("project") for o in orders if o.get("project")})
	events_by_project = get_events_by_project(project_names) if project_names else {}
	designations = get_customer_designations([o.get("customer") for o in orders if o.get("customer")])
	pos_by_order = get_purchase_orders_by_sales_order(orders)
	today = getdate(nowdate())
	data = []
	for order in orders:
		txn_date = order.get("transaction_date")
		age = (today - getdate(txn_date)).days if txn_date else None
		total = order.get("total") or 0
		per_billed = order.get("per_billed") or 0
		remaining = total - (total * per_billed / 100)
		project = order.get("project")
		events_html = format_events_badges(events_by_project.get(project, [])) if project else ""
		so_name = order.get("name")
		# Désignation client : Customer.customer_name (fiche client), pas l'ID Sales Order.customer.
		customer_designation = (
			designations.get(order.get("customer"))
			or order.get("customer_name")
			or order.get("customer")
		)
		data.append({
			"name": so_name,
			"customer_name": customer_designation,
			"status": order.get("status"),
			"custom_construction_status": order.get("custom_construction_status"),
			"transaction_date": txn_date,
			"age": age,
			"delivery_date": order.get("delivery_date"),
			"purchase_orders": format_purchase_orders_html(pos_by_order.get(so_name, [])),
			"reference_piece": order.get("reference_piece"),
			"custom_responsable_du_devis": order.get("custom_responsable_du_devis"),
			"custom_labour_hours": order.get("custom_labour_hours"),
			"total": total,
			"per_billed": per_billed,
			"remaining_amount": remaining,
			"evenements": events_html,
			# Hidden fields for get_indicator
			"per_delivered": order.get("per_delivered"),
			"skip_delivery_note": order.get("skip_delivery_note"),
			"grand_total": order.get("grand_total"),
			"custom_statut_fiche_de_travail": order.get("custom_statut_fiche_de_travail"),
			"custom_per_received": order.get("custom_per_received"),
			"custom_payment_request_status": order.get("custom_payment_request_status"),
			"project": project,
		})
	return data


def get_customer_designations(customer_ids: list[str]) -> dict[str, str]:
	"""Map Customer.name → Customer.customer_name (désignation on the Customer form)."""
	ids = list(dict.fromkeys([c for c in customer_ids if c]))
	if not ids:
		return {}
	rows = frappe.get_list(
		"Customer",
		filters={"name": ["in", ids]},
		fields=["name", "customer_name"],
	)
	return {r.get("name"): r.get("customer_name") for r in rows if r.get("name") and r.get("customer_name")}


def get_purchase_orders_by_sales_order(orders: list[dict]) -> dict[str, list[dict]]:
	"""Return {sales_order: [purchase order info, ...]} for linked POs.

	A PO is linked when Purchase Order Item.sales_order points at the sales order.
	POs attached only to the chantier (item.project set, sales_order empty) are
	also shown on every sales order of that project — the same association used
	by Planning Chantiers and the project details dialog.
	"""
	so_names = [o.get("name") for o in orders if o.get("name")]
	if not so_names:
		return {}

	project_to_sos: dict[str, list[str]] = {}
	for order in orders:
		project = order.get("project")
		name = order.get("name")
		if project and name:
			project_to_sos.setdefault(project, []).append(name)

	rows = []
	placeholders = ", ".join(["%s"] * len(so_names))
	rows.extend(frappe.db.sql(
		f"""
		SELECT
			poi.sales_order AS sales_order,
			poi.project AS project,
			po.name AS purchase_order,
			po.supplier_name AS supplier_name,
			po.supplier AS supplier,
			po.schedule_date AS schedule_date,
			MIN(poi.schedule_date) AS item_schedule_date
		FROM `tabPurchase Order` po
		INNER JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
		WHERE po.docstatus < 2
		  AND poi.sales_order IN ({placeholders})
		GROUP BY po.name, poi.sales_order, poi.project,
		         po.supplier_name, po.supplier, po.schedule_date
		""",
		tuple(so_names),
		as_dict=True,
	))

	projects = list(project_to_sos.keys())
	if projects:
		placeholders = ", ".join(["%s"] * len(projects))
		rows.extend(frappe.db.sql(
			f"""
			SELECT
				poi.sales_order AS sales_order,
				poi.project AS project,
				po.name AS purchase_order,
				po.supplier_name AS supplier_name,
				po.supplier AS supplier,
				po.schedule_date AS schedule_date,
				MIN(poi.schedule_date) AS item_schedule_date
			FROM `tabPurchase Order` po
			INNER JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
			WHERE po.docstatus < 2
			  AND poi.project IN ({placeholders})
			  AND IFNULL(poi.sales_order, '') = ''
			GROUP BY po.name, poi.sales_order, poi.project,
			         po.supplier_name, po.supplier, po.schedule_date
			""",
			tuple(projects),
			as_dict=True,
		))

	return index_purchase_orders(rows, so_names, project_to_sos)


def index_purchase_orders(
	rows: list[dict],
	so_names: list[str],
	project_to_sos: dict[str, list[str]],
) -> dict[str, list[dict]]:
	"""Group PO query rows onto sales orders and drop duplicates."""
	by_so: dict[str, list[dict]] = {name: [] for name in so_names}
	seen: dict[str, set[str]] = {name: set() for name in so_names}

	def add(so_name: str, row: dict):
		po_name = row.get("purchase_order")
		if not so_name or not po_name or so_name not in seen or po_name in seen[so_name]:
			return
		seen[so_name].add(po_name)
		by_so[so_name].append({
			"name": po_name,
			"supplier_name": row.get("supplier_name") or row.get("supplier") or po_name,
			"schedule_date": row.get("schedule_date") or row.get("item_schedule_date"),
		})

	for row in rows:
		sales_order = (row.get("sales_order") or "").strip() if row.get("sales_order") else ""
		if sales_order:
			add(sales_order, row)
			continue
		project = row.get("project")
		if project:
			for so_name in project_to_sos.get(project, []):
				add(so_name, row)

	for so_name, pos in by_so.items():
		pos.sort(key=lambda po: (po.get("schedule_date") is None, po.get("schedule_date"), po.get("supplier_name") or ""))

	return by_so


def format_purchase_orders_html(purchase_orders: list[dict]) -> str:
	"""Stacked supplier-name links + planned delivery date; click opens the PO."""
	if not purchase_orders:
		return ""
	lines = []
	for po in purchase_orders:
		name = po.get("name") or ""
		supplier = escape_html(po.get("supplier_name") or name)
		schedule = po.get("schedule_date")
		date_label = format_date(schedule, "dd/MM/yyyy") if schedule else ""
		href = escape_html(f"/app/purchase-order/{quote(name, safe='')}")
		title = escape_html(name)
		name_js = json.dumps(name)
		date_bit = f" — {escape_html(date_label)}" if date_label else ""
		lines.append(
			"<div>"
			f'<a href="{href}" title="{title}" '
			f"onclick=\"frappe.set_route('Form', 'Purchase Order', {name_js}); return false;\">"
			f"{supplier}</a>{date_bit}"
			"</div>"
		)
	return f'<div class="order-book-purchase-orders">{"".join(lines)}</div>'


def get_events_by_project(project_names):
	events = frappe.get_list(
		"Event",
		filters={
			"project": ["in", project_names],
		},
		fields=["name", "project", "starts_on", "ends_on", "color", "subject"],
		order_by="starts_on",
	)
	by_project = {}
	for event in events:
		project = event.get("project")
		if project not in by_project:
			by_project[project] = []
		by_project[project].append({
			"name": event.get("name"),
			"starts_on": event.get("starts_on"),
			"color": event.get("color"),
			"subject": event.get("subject"),
		})
	return by_project


def format_events_badges(events_list):
	if not events_list:
		return ""
	badges = []
	for event in events_list:
		color = event.get("color") or "#6c757d"
		starts_on = event.get("starts_on")
		name = event.get("name")
		subject = event.get("subject") or ""
		label = frappe.utils.format_date(starts_on, "dd/MM") if starts_on else ""
		badge = f'<a href="#" onclick="frappe.set_route(\'Form\', \'Event\', \'{name}\'); return false;" title="{subject}"><span class="badge" style="background-color: {color}; color: white; cursor: pointer; margin: 2px;">{label}</span></a>'
		badges.append(badge)
	return " ".join(badges)

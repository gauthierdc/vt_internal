# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, date_diff


def execute(filters=None):
	filters = frappe._dict(filters or {})

	columns = get_columns()
	data = get_data(filters)

	chart_html = generate_chart_html(data) if data else None

	return columns, data, chart_html


def get_columns():
	return [
		{
			"label": _("Commande fournisseur"),
			"fieldname": "purchase_order",
			"fieldtype": "Link",
			"options": "Purchase Order",
			"width": 170,
		},
		{
			"label": _("Fournisseur"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 160,
		},
		{
			"label": _("Article"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": _("Description"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Date commande"),
			"fieldname": "transaction_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Demandé pour le"),
			"fieldname": "schedule_date",
			"fieldtype": "Date",
			"width": 130,
		},
		{
			"label": _("Engagement fournisseur"),
			"fieldname": "order_confirmation_date",
			"fieldtype": "Date",
			"width": 150,
		},
		{
			"label": _("Date réception réelle"),
			"fieldname": "receipt_date",
			"fieldtype": "Date",
			"width": 140,
		},
		{
			"label": _("Qté commandée"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 110,
		},
		{
			"label": _("Qté reçue"),
			"fieldname": "received_qty",
			"fieldtype": "Float",
			"width": 90,
		},
		{
			"label": _("Statut"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Demandé → Engagement (j)"),
			"fieldname": "delta_confirmation_schedule",
			"fieldtype": "Int",
			"width": 150,
		},
		{
			"label": _("Engagement → Réception (j)"),
			"fieldname": "delta_confirmation_receipt",
			"fieldtype": "Int",
			"width": 150,
		},
	]


def get_data(filters):
	conditions, params = build_conditions(filters)

	rows = frappe.db.sql(f"""
		SELECT
			po.name AS purchase_order,
			po.supplier,
			po.transaction_date,
			po.order_confirmation_date,
			po.status,
			poi.item_code,
			poi.item_name,
			poi.schedule_date,
			poi.qty,
			poi.received_qty,
			MIN(pr.posting_date) AS receipt_date
		FROM `tabPurchase Order` po
		INNER JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
		LEFT JOIN `tabPurchase Receipt Item` pri
			ON pri.purchase_order_item = poi.name
		LEFT JOIN `tabPurchase Receipt` pr
			ON pr.name = pri.parent AND pr.docstatus = 1
		WHERE po.docstatus = 1
		  AND po.status NOT IN ('Stopped', 'On Hold')
		{conditions}
		GROUP BY poi.name
		ORDER BY po.transaction_date DESC, po.name, poi.idx
	""", params, as_dict=True)

	data = []
	for row in rows:
		delta_confirmation_schedule = safe_date_diff(row.order_confirmation_date, row.schedule_date)
		delta_confirmation_receipt = safe_date_diff(row.receipt_date, row.order_confirmation_date)

		data.append({
			"purchase_order": row.purchase_order,
			"supplier": row.supplier,
			"item_code": row.item_code,
			"item_name": row.item_name,
			"transaction_date": row.transaction_date,
			"order_confirmation_date": row.order_confirmation_date,
			"schedule_date": row.schedule_date,
			"receipt_date": row.receipt_date,
			"qty": flt(row.qty),
			"received_qty": flt(row.received_qty),
			"status": row.status,
			"delta_confirmation_schedule": delta_confirmation_schedule,
			"delta_confirmation_receipt": delta_confirmation_receipt,
		})

	return data


def build_conditions(filters):
	conditions = []
	params = {}

	if filters.get("supplier"):
		conditions.append("po.supplier = %(supplier)s")
		params["supplier"] = filters.supplier

	if filters.get("from_date"):
		conditions.append("po.transaction_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("po.transaction_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	if filters.get("status"):
		conditions.append("po.status = %(status)s")
		params["status"] = filters.status

	if filters.get("company"):
		conditions.append("po.company = %(company)s")
		params["company"] = filters.company

	cond_str = ("AND " + " AND ".join(conditions)) if conditions else ""
	return cond_str, params


def safe_date_diff(date1, date2):
	"""Return date_diff(date1, date2) in days, or None if either date is missing."""
	if not date1 or not date2:
		return None
	try:
		return date_diff(getdate(date1), getdate(date2))
	except Exception:
		return None


def generate_chart_html(data):
	# Moyennes
	metrics = [
		("delta_confirmation_schedule", "Demandé → Engagement", "#5e64ff"),
		("delta_confirmation_receipt", "Engagement → Réception", "#ff5858"),
	]

	cards = ""
	for fieldname, label, color in metrics:
		vals = [r[fieldname] for r in data if r.get(fieldname) is not None]
		avg = round(sum(vals) / len(vals), 1) if vals else None
		display = f"{'+' if avg and avg > 0 else ''}{avg}j" if avg is not None else "—"
		cards += f"""
		<div style="background:#fff; border-radius:8px; padding:16px 24px; box-shadow:0 1px 4px rgba(0,0,0,0.07); text-align:center;">
			<div style="font-size:12px; color:#888; margin-bottom:4px;">{label}</div>
			<div style="font-size:28px; font-weight:bold; color:{color};">{display}</div>
			<div style="font-size:11px; color:#bbb; margin-top:2px;">moyenne</div>
		</div>"""

	# Articles arrivés après la date d'engagement
	late = sum(1 for r in data if r.get("delta_confirmation_receipt") is not None and r["delta_confirmation_receipt"] > 0)
	total_received = sum(1 for r in data if r.get("delta_confirmation_receipt") is not None)
	pct = round(late / total_received * 100) if total_received else 0
	late_color = "#e74c3c" if pct > 20 else "#f39c12" if pct > 0 else "#27ae60"
	cards += f"""
	<div style="background:#fff; border-radius:8px; padding:16px 24px; box-shadow:0 1px 4px rgba(0,0,0,0.07); text-align:center;">
		<div style="font-size:12px; color:#888; margin-bottom:4px;">Arrivés après l'engagement</div>
		<div style="font-size:28px; font-weight:bold; color:{late_color};">{late}</div>
		<div style="font-size:11px; color:#bbb; margin-top:2px;">sur {total_received} reçus ({pct}%)</div>
	</div>"""

	return f'<div style="display:flex; gap:16px; margin-bottom:20px; flex-wrap:wrap;">{cards}</div>'

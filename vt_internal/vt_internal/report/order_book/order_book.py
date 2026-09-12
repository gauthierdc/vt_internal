# Copyright (c) 2025, Dokos SAS and contributors
# For license information, please see license.txt
"""Carnet de commande — rapport de planification.

Colonnes (demande Étienne / équipe chantier) :
désignation | client | statut | statut du chantier | ARC en cours + date de
réception | événements (VT vs pose) | référence | Reste à facturer | Total HT |
date de livraison | nombre d'h total | nombre d'h solde | age | responsable
du chantier.
"""

from __future__ import annotations

import json
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import escape_html, format_date, getdate, nowdate

# Aligné sur public/js/planning_chantiers/helpers.js (MILESTONE_TYPES).
# Fiche de travail = pose sur le terrain.
EVENT_KIND_META = {
	"vt": {"label": "VT", "icon": "🔍", "color": "#00838f", "bg": "rgba(0,131,143,.14)"},
	"ft": {"label": "Pose", "icon": "📋", "color": "#4f5bd5", "bg": "rgba(92,107,192,.16)"},
	"event": {"label": "Évt", "icon": "📅", "color": "#546e7a", "bg": "rgba(84,110,122,.14)"},
}

def execute(filters: dict | None = None):
	"""Return columns, data, HTML summary cards and report_summary."""
	columns = get_columns()
	data = get_data(filters)
	message, report_summary = build_summary(data)
	return columns, data, message, None, report_summary


def get_columns() -> list[dict]:
	"""Planning-oriented column order (Frappe fieldname constraints apply)."""
	return [
		{"label": _("Désignation"), "fieldname": "name", "fieldtype": "Link", "options": "Sales Order", "width": 150},
		# Client = Customer.customer_name, jamais l'ID / nom comptable.
		{"label": _("Client"), "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
		{"label": _("Statut"), "fieldname": "status", "fieldtype": "Data", "width": 150},
		{"label": _("Statut du chantier"), "fieldname": "custom_construction_status", "fieldtype": "Small Text", "width": 200},
		{
			"label": _("ARC en cours et date de réception"),
			"fieldname": "pending_arcs",
			"fieldtype": "HTML",
			"width": 240,
		},
		{"label": _("Événements"), "fieldname": "evenements", "fieldtype": "HTML", "width": 280},
		{"label": _("Référence"), "fieldname": "reference_piece", "fieldtype": "Data", "width": 120},
		{"label": _("Reste à Facturer"), "fieldname": "remaining_amount", "fieldtype": "Currency", "options": "currency", "width": 140},
		{"label": _("Total HT"), "fieldname": "total", "fieldtype": "Currency", "options": "currency", "width": 120},
		{"label": _("Date de livraison"), "fieldname": "delivery_date", "fieldtype": "Date", "width": 110},
		{"label": _("Nombre d'h total"), "fieldname": "hours_total", "fieldtype": "Float", "width": 110},
		{"label": _("Nombre d'h solde"), "fieldname": "hours_solde", "fieldtype": "Float", "width": 110},
		{"label": _("Age"), "fieldname": "age", "fieldtype": "Int", "width": 70},
		{
			"label": _("Responsable du chantier"),
			"fieldname": "construction_manager",
			"fieldtype": "Link",
			"options": "User",
			"width": 170,
		},
		# Hidden columns for Sales Order get_indicator (listview_settings).
		{"fieldname": "per_delivered", "fieldtype": "Percent", "hidden": 1},
		{"fieldname": "skip_delivery_note", "fieldtype": "Check", "hidden": 1},
		{"fieldname": "grand_total", "fieldtype": "Currency", "hidden": 1},
		{"fieldname": "custom_statut_fiche_de_travail", "fieldtype": "Data", "hidden": 1},
		{"fieldname": "custom_per_received", "fieldtype": "Percent", "hidden": 1},
		{"fieldname": "custom_payment_request_status", "fieldtype": "Data", "hidden": 1},
		{"fieldname": "project", "fieldtype": "Link", "options": "Project", "hidden": 1},
		{"fieldname": "per_billed", "fieldtype": "Percent", "hidden": 1},
	]


def get_data(filters: dict | None = None) -> list[dict]:
	"""Return rows (dicts) after applying planner filters."""
	query_filters = dict(filters or {})
	managers = parse_manager_filter(query_filters)

	if query_filters.get("cost_center"):
		query_filters["cost_center"] = ["descendants of (inclusive)", query_filters["cost_center"]]

	# Always exclude closed / cancelled / fully billed / stats-excluded orders.
	query_filters.update({
		"status": ["!=", "Closed"],
		"per_billed": ["<", 100],
		"docstatus": ["!=", 2],
		"custom_exclude_from_statistics": ["!=", 1],
	})

	list_kwargs = {
		"filters": query_filters,
		"order_by": "transaction_date desc",
	}
	if managers:
		matching_projects = get_projects_for_managers(managers)
		or_filters = [["custom_construction_manager", "in", managers]]
		if matching_projects:
			or_filters.append(["project", "in", matching_projects])
		list_kwargs["or_filters"] = or_filters

	orders = frappe.get_list(
		"Sales Order",
		fields=[
			"name",
			"customer",
			"customer_name",
			"status",
			"transaction_date",
			"delivery_date",
			"reference_piece",
			"custom_construction_manager",
			"custom_labour_hours",
			"total",
			"per_billed",
			"custom_construction_status",
			"per_delivered",
			"skip_delivery_note",
			"grand_total",
			"custom_statut_fiche_de_travail",
			"custom_per_received",
			"custom_payment_request_status",
			"project",
		],
		**list_kwargs,
	)

	if managers:
		project_managers = get_project_managers([o.get("project") for o in orders if o.get("project")])
		orders = [o for o in orders if order_matches_managers(o, project_managers, managers)]
	else:
		project_managers = get_project_managers([o.get("project") for o in orders if o.get("project")])

	project_names = list({o.get("project") for o in orders if o.get("project")})
	events_by_project = get_events_by_project(project_names) if project_names else {}
	designations = get_customer_designations([o.get("customer") for o in orders if o.get("customer")])
	arcs_by_order = get_pending_arcs_by_sales_order(orders)
	hours_by_project = get_labour_hours_by_project(project_names) if project_names else {}
	today = getdate(nowdate())
	data = []
	for order in orders:
		txn_date = order.get("transaction_date")
		age = (today - getdate(txn_date)).days if txn_date else None
		total = order.get("total") or 0
		per_billed = order.get("per_billed") or 0
		remaining = total - (total * per_billed / 100)
		project = order.get("project")
		events_html = format_events_badges(events_by_project.get(project, []), today) if project else ""
		so_name = order.get("name")
		customer_designation = resolve_customer_display_name(
			order.get("customer"),
			order.get("customer_name"),
			designations,
		)
		hours_total = order.get("custom_labour_hours") or 0
		project_hours = hours_by_project.get(project) or {}
		if not hours_total and project_hours.get("expected"):
			hours_total = project_hours["expected"]
		actual = project_hours.get("actual") or 0
		hours_solde = (hours_total or 0) - actual
		construction_manager = (
			(project_managers.get(project) if project else None)
			or order.get("custom_construction_manager")
			or ""
		)
		data.append({
			"name": so_name,
			"customer_name": customer_designation,
			"status": order.get("status"),
			"custom_construction_status": order.get("custom_construction_status"),
			"pending_arcs": format_pending_arcs_html(arcs_by_order.get(so_name, []), today),
			"evenements": events_html,
			"reference_piece": order.get("reference_piece"),
			"remaining_amount": remaining,
			"total": total,
			"delivery_date": order.get("delivery_date"),
			"hours_total": hours_total,
			"hours_solde": hours_solde,
			"age": age,
			"construction_manager": construction_manager,
			# Hidden fields for get_indicator
			"per_delivered": order.get("per_delivered"),
			"skip_delivery_note": order.get("skip_delivery_note"),
			"grand_total": order.get("grand_total"),
			"custom_statut_fiche_de_travail": order.get("custom_statut_fiche_de_travail"),
			"custom_per_received": order.get("custom_per_received"),
			"custom_payment_request_status": order.get("custom_payment_request_status"),
			"project": project,
			"per_billed": per_billed,
		})
	return data


def parse_manager_filter(query_filters: dict) -> list[str]:
	"""Pop report-only manager filters and return a unique list of User names."""
	raw = query_filters.pop("construction_managers", None)
	legacy = query_filters.pop("custom_construction_manager", None)
	managers = as_list(raw)
	if not managers:
		managers = as_list(legacy)
	# Dedupe, drop empties.
	seen = []
	for name in managers:
		if name and name not in seen:
			seen.append(name)
	return seen


def as_list(value) -> list:
	"""Normalise MultiSelectList / Link / JSON / comma-separated values."""
	if not value:
		return []
	if isinstance(value, str):
		text = value.strip()
		if not text:
			return []
		if text.startswith("["):
			try:
				value = json.loads(text)
			except (ValueError, TypeError):
				value = [v.strip() for v in text.split(",") if v.strip()]
		else:
			value = [v.strip() for v in text.split(",") if v.strip()]
	if isinstance(value, (list, tuple, set)):
		return [v for v in value if v]
	return [value]


def get_projects_for_managers(managers: list[str]) -> list[str]:
	if not managers:
		return []
	return frappe.get_all(
		"Project",
		filters={"custom_construction_manager": ["in", managers]},
		pluck="name",
	) or []


def get_project_managers(project_names: list[str]) -> dict[str, str]:
	"""Map Project.name → custom_construction_manager (conducteur de travaux)."""
	names = list({p for p in project_names if p})
	if not names:
		return {}
	rows = frappe.get_all(
		"Project",
		filters={"name": ["in", names]},
		fields=["name", "custom_construction_manager"],
	)
	return {
		r.get("name"): r.get("custom_construction_manager")
		for r in rows
		if r.get("name") and r.get("custom_construction_manager")
	}


def order_matches_managers(order: dict, project_managers: dict[str, str], managers: list[str]) -> bool:
	"""True if the Project construction manager matches (SO field is fallback only)."""
	if not managers:
		return True
	wanted = set(managers)
	project = order.get("project")
	project_cm = project_managers.get(project) if project else None
	if project_cm:
		return project_cm in wanted
	return order.get("custom_construction_manager") in wanted


def looks_like_accounting_code(name) -> bool:
	"""Accounting / billing-looking labels start with a digit (ex. 411…, 04…)."""
	if not name:
		return False
	text = str(name).strip()
	return bool(text) and text[0].isdigit()


def resolve_customer_display_name(customer_id, so_customer_name, designations: dict[str, str]) -> str:
	"""Prefer Customer.customer_name; never lead with a digit-prefixed accounting id."""
	live = designations.get(customer_id) if customer_id else None
	candidates = [live, so_customer_name, customer_id]
	# First non-accounting human name.
	for value in candidates:
		if value and not looks_like_accounting_code(value):
			return value
	# Fall back to whatever we have (including an accounting-looking label).
	for value in candidates:
		if value:
			return value
	return ""


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


def get_labour_hours_by_project(project_names: list[str]) -> dict[str, dict]:
	"""Batch expected (SO) and actual (Timesheet) hours — same sources as Chantiers."""
	names = list({p for p in project_names if p})
	if not names:
		return {}
	placeholders = ", ".join(["%s"] * len(names))
	expected_rows = frappe.db.sql(
		f"""
		SELECT project, COALESCE(SUM(custom_labour_hours), 0) AS hours
		FROM `tabSales Order`
		WHERE project IN ({placeholders})
		  AND docstatus = 1
		  AND custom_exclude_from_statistics != 1
		GROUP BY project
		""",
		tuple(names),
		as_dict=True,
	)
	actual_rows = frappe.db.sql(
		f"""
		SELECT d.project AS project, COALESCE(SUM(d.hours), 0) AS hours
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name
		WHERE d.project IN ({placeholders})
		  AND t.docstatus != 2
		GROUP BY d.project
		""",
		tuple(names),
		as_dict=True,
	)
	expected = {r.get("project"): (r.get("hours") or 0) for r in expected_rows}
	actual = {r.get("project"): (r.get("hours") or 0) for r in actual_rows}
	return {
		name: {
			"expected": expected.get(name, 0),
			"actual": actual.get(name, 0),
		}
		for name in names
	}


def get_pending_arcs_by_sales_order(orders: list[dict]) -> dict[str, list[dict]]:
	"""Pending supplier POs (ARC) linked to the sales order or its chantier.

	« ARC en attente » = Purchase Order submitted, not closed/cancelled, not
	fully received. Expected receipt = PO.schedule_date, else MIN(item.schedule_date)
	— same date Planning Chantiers uses for 🛒 réceptions fournisseur.
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
	rows.extend(
		frappe.db.sql(
			f"""
			SELECT
				poi.sales_order AS sales_order,
				poi.project AS project,
				po.name AS purchase_order,
				po.supplier_name AS supplier_name,
				po.supplier AS supplier,
				po.schedule_date AS schedule_date,
				MIN(poi.schedule_date) AS item_schedule_date,
				po.per_received AS per_received,
				po.status AS status,
				po.`custom_ar_validé` AS ar_valide,
				SUM(poi.qty) AS qty,
				SUM(poi.received_qty) AS received_qty
			FROM `tabPurchase Order` po
			INNER JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
			WHERE po.docstatus = 1
			  AND po.status NOT IN ('Closed', 'Cancelled')
			  AND IFNULL(po.per_received, 0) < 100
			  AND poi.sales_order IN ({placeholders})
			GROUP BY po.name, poi.sales_order, poi.project,
			         po.supplier_name, po.supplier, po.schedule_date,
			         po.per_received, po.status, po.`custom_ar_validé`
			""",
			tuple(so_names),
			as_dict=True,
		)
	)

	projects = list(project_to_sos.keys())
	if projects:
		placeholders = ", ".join(["%s"] * len(projects))
		rows.extend(
			frappe.db.sql(
				f"""
				SELECT
					poi.sales_order AS sales_order,
					poi.project AS project,
					po.name AS purchase_order,
					po.supplier_name AS supplier_name,
					po.supplier AS supplier,
					po.schedule_date AS schedule_date,
					MIN(poi.schedule_date) AS item_schedule_date,
					po.per_received AS per_received,
					po.status AS status,
					po.`custom_ar_validé` AS ar_valide,
					SUM(poi.qty) AS qty,
					SUM(poi.received_qty) AS received_qty
				FROM `tabPurchase Order` po
				INNER JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
				WHERE po.docstatus = 1
				  AND po.status NOT IN ('Closed', 'Cancelled')
				  AND IFNULL(po.per_received, 0) < 100
				  AND poi.project IN ({placeholders})
				  AND IFNULL(poi.sales_order, '') = ''
				GROUP BY po.name, poi.sales_order, poi.project,
				         po.supplier_name, po.supplier, po.schedule_date,
				         po.per_received, po.status, po.`custom_ar_validé`
				""",
				tuple(projects),
				as_dict=True,
			)
		)

	return index_pending_arcs(rows, so_names, project_to_sos)


def is_arc_pending(row: dict) -> bool:
	"""A PO line-group is still pending when not fully received."""
	qty = row.get("qty") or 0
	received = row.get("received_qty") or 0
	if qty and received >= qty:
		return False
	if (row.get("per_received") or 0) >= 100:
		return False
	if row.get("status") in ("Closed", "Cancelled", "Completed"):
		return False
	return True


def index_pending_arcs(
	rows: list[dict],
	so_names: list[str],
	project_to_sos: dict[str, list[str]],
) -> dict[str, list[dict]]:
	"""Group pending ARC rows onto sales orders and drop duplicates."""
	by_so: dict[str, list[dict]] = {name: [] for name in so_names}
	seen: dict[str, set[str]] = {name: set() for name in so_names}

	def add(so_name: str, row: dict):
		po_name = row.get("purchase_order")
		if not so_name or not po_name or so_name not in seen or po_name in seen[so_name]:
			return
		if not is_arc_pending(row):
			return
		seen[so_name].add(po_name)
		by_so[so_name].append({
			"name": po_name,
			"supplier_name": row.get("supplier_name") or row.get("supplier") or po_name,
			"schedule_date": row.get("schedule_date") or row.get("item_schedule_date"),
			"ar_valide": row.get("ar_valide"),
			"per_received": row.get("per_received") or 0,
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

	for pos in by_so.values():
		pos.sort(key=lambda po: (po.get("schedule_date") is None, po.get("schedule_date"), po.get("supplier_name") or ""))

	return by_so


def format_pending_arcs_html(purchase_orders: list[dict] | None, today=None) -> str:
	"""Stacked supplier links + expected receipt date; overdue dates in red."""
	if not purchase_orders:
		return ""
	if today is None:
		today = getdate(nowdate())
	lines = []
	for po in purchase_orders:
		name = po.get("name") or ""
		supplier = escape_html(po.get("supplier_name") or name)
		schedule = po.get("schedule_date")
		date_label = format_date(schedule, "dd/MM/yyyy") if schedule else ""
		href = escape_html(f"/app/purchase-order/{quote(name, safe='')}")
		title = escape_html(name)
		name_js = json.dumps(name)
		overdue = bool(schedule and getdate(schedule) < today)
		date_color = "#c62828" if overdue else "#555"
		date_bit = (
			f' <span style="color:{date_color}; white-space:nowrap;">{escape_html(date_label)}</span>'
			if date_label
			else ""
		)
		ar_bit = ""
		if not po.get("ar_valide"):
			ar_bit = (
				' <span style="background:#fff3cd; color:#8a6d3b; font-size:10px; '
				'padding:1px 5px; border-radius:3px;">AR à valider</span>'
			)
		lines.append(
			'<div style="margin:2px 0;">'
			f'<a href="{href}" title="{title}" '
			f"onclick=\"frappe.set_route('Form', 'Purchase Order', {name_js}); return false;\">"
			f"{supplier}</a>{date_bit}{ar_bit}"
			"</div>"
		)
	return f'<div class="order-book-pending-arcs">{"".join(lines)}</div>'


def event_kind(event: dict) -> str:
	"""VT (visite technique) vs pose (fiche de travail) vs other Event."""
	if event.get("custom_visite_technique") or event.get("vt"):
		return "vt"
	if event.get("custom_fiche_de_travail") or event.get("ft"):
		return "ft"
	return "event"


def get_events_by_project(project_names):
	events = frappe.get_list(
		"Event",
		filters={"project": ["in", project_names]},
		fields=[
			"name",
			"project",
			"starts_on",
			"ends_on",
			"color",
			"subject",
			"custom_visite_technique",
			"custom_fiche_de_travail",
		],
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
			"custom_visite_technique": event.get("custom_visite_technique"),
			"custom_fiche_de_travail": event.get("custom_fiche_de_travail"),
		})
	return by_project


def format_events_badges(events_list, today=None) -> str:
	"""HTML badges: 🔍 VT (teal) vs 📋 Pose (indigo) vs 📅 other."""
	if not events_list:
		return ""
	if today is None:
		today = getdate(nowdate())
	badges = []
	for event in events_list:
		kind = event_kind(event)
		meta = EVENT_KIND_META[kind]
		starts_on = event.get("starts_on")
		name = event.get("name") or ""
		subject = event.get("subject") or ""
		date_label = format_date(starts_on, "dd/MM") if starts_on else ""
		is_past = bool(starts_on and getdate(starts_on) < today)
		opacity = "0.55" if is_past else "1"
		label = f"{meta['icon']} {meta['label']} {date_label}".strip()
		title = escape_html(f"{meta['label']} — {subject}" if subject else meta["label"])
		href = escape_html(f"/app/event/{quote(name, safe='')}")
		name_js = json.dumps(name)
		badge = (
			f'<a href="{href}" title="{title}" '
			f"onclick=\"frappe.set_route('Form', 'Event', {name_js}); return false;\">"
			f'<span class="badge order-book-event order-book-event-{kind}" '
			f'style="background-color:{meta["color"]}; color:#fff; cursor:pointer; '
			f'margin:2px; opacity:{opacity};">{escape_html(label)}</span></a>'
		)
		badges.append(badge)
	return f'<div class="order-book-events" style="display:flex; flex-wrap:wrap; gap:2px;">{"".join(badges)}</div>'


def build_summary(data: list[dict]) -> tuple[str, list[dict]]:
	"""Chantiers-style cards + Frappe report_summary pills."""
	n = len(data)
	remaining_ht = sum((row.get("remaining_amount") or 0) for row in data)
	total_hours = sum((row.get("hours_total") or 0) for row in data)
	solde_hours = sum((row.get("hours_solde") or 0) for row in data)
	nb_arcs = 0
	for row in data:
		html = row.get("pending_arcs") or ""
		# Each pending PO is one stacked <div> inside the cell.
		if html:
			nb_arcs += html.count("<div style=")
	nb_events = 0
	for row in data:
		html = row.get("evenements") or ""
		if html:
			nb_events += html.count("order-book-event ")

	if remaining_ht >= 1_000_000:
		reste_display = f"{round(remaining_ht / 1_000_000, 1)} M€"
	elif remaining_ht >= 1000:
		reste_display = f"{round(remaining_ht / 1000)} k€"
	else:
		reste_display = f"{round(remaining_ht)} €"

	message = f"""
	<div style="display: flex; gap: 20px; margin-bottom: 15px; flex-wrap: wrap;">
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 130px; text-align: center;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">Commandes</div>
			<div style="font-size: 36px; font-weight: bold; color: #1976d2;">{n}</div>
			<div style="font-size: 10px; color: #999;">Carnet ouvert</div>
		</div>
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 150px; text-align: center;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">Reste à facturer</div>
			<div style="font-size: 36px; font-weight: bold; color: #2e7d32;">{reste_display}</div>
			<div style="font-size: 10px; color: #999;">HT</div>
		</div>
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 150px; text-align: center;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">Heures</div>
			<div style="font-size: 36px; font-weight: bold; color: #6a3fb0;">{round(solde_hours)}h</div>
			<div style="font-size: 10px; color: #999;">solde / {round(total_hours)}h total</div>
		</div>
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 130px; text-align: center;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">ARC en cours</div>
			<div style="font-size: 36px; font-weight: bold; color: #1565c0;">{nb_arcs}</div>
			<div style="font-size: 10px; color: #999;">réceptions attendues</div>
		</div>
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 130px; text-align: center;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">Événements</div>
			<div style="font-size: 36px; font-weight: bold; color: #00838f;">{nb_events}</div>
			<div style="font-size: 10px; color: #999;">VT / pose / autres</div>
		</div>
	</div>
	"""
	report_summary = [
		{"value": n, "label": _("Nombre de commande"), "datatype": "Int"},
		{"value": total_hours, "label": _("Heures"), "datatype": "Float"},
		{"value": remaining_ht, "label": _("Reste à facturer (HT)"), "datatype": "Currency"},
	]
	return message, report_summary

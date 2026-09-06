# Copyright (c) 2026, Verre & Transparence and contributors
# API du drawer d'événement (remplace le popover natif sur le calendrier Dokos).
#
#   - get_event_detail : détail enrichi (VT/FDT, adresse, téléphone) pour la modale
#   - get_calendar_employees : employés distincts visibles sur [start, end] (dropdown filtre)

import datetime
import json

import frappe

# Couleur de repli par type quand l'Event n'a pas de couleur propre.
TYPE_COLORS = {
	"Public": "#1E88E5",
	"Private": "#7E57C2",
}
DEFAULT_COLOR = "#1E88E5"


def _color(color, event_type):
	return color or TYPE_COLORS.get(event_type) or DEFAULT_COLOR


def _compose_address(address_name):
	"""Adresse lisible sur une ligne depuis un doc Address."""
	if not address_name:
		return None
	a = frappe.db.get_value(
		"Address",
		address_name,
		["address_line1", "address_line2", "city", "pincode"],
		as_dict=True,
	)
	if not a:
		return None
	city_zip = f"{a.pincode} {a.city}".strip() if (a.pincode and a.city) else (a.city or a.pincode)
	parts = [a.address_line1, a.address_line2, city_zip]
	return ", ".join([p for p in parts if p]) or None


@frappe.whitelist()
def get_event_detail(name):
	"""Détail enrichi d'un Event pour la modale : dates, type, description, et
	infos de la Visite Technique / Fiche de travail liée (adresse, téléphone)."""
	from vt_internal.vt_internal.utils.event_employees import event_doc_name

	name = event_doc_name(name)
	doc = frappe.get_doc("Event", name)  # applique les permissions
	doc.check_permission("read")

	vt = doc.get("custom_visite_technique")
	fdt = doc.get("custom_fiche_de_travail")

	# Adresse + description LIÉE : depuis le doc de référence (FDT prioritaire, comme
	# le custom_html de l'Event). Téléphone : uniquement depuis la VT (le champ
	# n'existe pas forcément sur Fiche de travail).
	address_display = None
	phone = None
	linked_description = None
	if fdt and frappe.db.exists("Fiche de travail", fdt):
		r = frappe.db.get_value("Fiche de travail", fdt, ["address", "description"], as_dict=True) or {}
		address_display = _compose_address(r.get("address"))
		linked_description = r.get("description")
	elif vt and frappe.db.exists("Visite Technique", vt):
		r = frappe.db.get_value("Visite Technique", vt, ["address", "description"], as_dict=True) or {}
		address_display = _compose_address(r.get("address"))
		linked_description = r.get("description")

	if vt and frappe.db.exists("Visite Technique", vt):
		phone = frappe.db.get_value("Visite Technique", vt, "phone")

	return {
		"name": doc.name,
		"subject": doc.subject,
		"starts_on": str(doc.starts_on) if doc.starts_on else None,
		"ends_on": str(doc.ends_on) if doc.ends_on else None,
		"all_day": bool(doc.all_day),
		"event_type": doc.event_type,
		"color": _color(doc.color, doc.event_type),
		"event_description": doc.description or "",
		"linked_description": linked_description or "",
		"vt": vt,
		"fdt": fdt,
		"address_display": address_display,
		"phone": phone,
	}


UNASSIGNED_EMPLOYEE = ""
UNASSIGNED_LABEL = "Sans employé"
UNASSIGNED_COLOR = "#FFEE00"


def _event_employee_id(event):
	# Après le split get_events : un item = un employé (custom_employé de l'instance).
	return (event.get("custom_employé") or "").strip()


def build_employee_rows(events, employee_details=None):
	"""Agrège les blocs calendrier en lignes de filtre : name, employee_name, color, event_count.

	`employee_details` : {employee_name_id: {employee_name, custom_couleur}}.
	Un Event Ahmed+Solène arrive déjà en 2 items : il compte pour les deux.
	Les événements sans employé sont regroupés sous « Sans employé ».
	"""
	employee_details = employee_details or {}
	counts = {}
	fallback_color = {}
	for event in events or []:
		emp = _event_employee_id(event)
		counts[emp] = counts.get(emp, 0) + 1
		if emp and emp not in fallback_color and event.get("color"):
			fallback_color[emp] = event.get("color")

	rows = []
	for emp, count in counts.items():
		if not emp:
			rows.append(
				{
					"name": UNASSIGNED_EMPLOYEE,
					"employee_name": UNASSIGNED_LABEL,
					"color": UNASSIGNED_COLOR,
					"event_count": count,
				}
			)
			continue
		detail = employee_details.get(emp) or {}
		rows.append(
			{
				"name": emp,
				"employee_name": detail.get("employee_name") or emp,
				"color": detail.get("custom_couleur") or fallback_color.get(emp) or DEFAULT_COLOR,
				"event_count": count,
			}
		)

	rows.sort(key=lambda r: (not r["name"], (r["employee_name"] or "").casefold()))
	return rows


def _employee_details(employee_ids):
	ids = [eid for eid in employee_ids if eid]
	if not ids:
		return {}
	fields = ["name", "employee_name"]
	try:
		if frappe.db.has_column("Employee", "custom_couleur"):
			fields.append("custom_couleur")
	except Exception:
		pass
	try:
		rows = frappe.get_list(
			"Employee",
			filters={"name": ["in", ids]},
			fields=fields,
			limit_page_length=500,
		)
	except Exception:
		return {}
	return {row.name: row for row in rows}


def _as_date_param(value):
	"""Normalise start/end (Date, datetime, ISO, SQL) en `YYYY-MM-DD`."""
	if value is None or value == "":
		return value
	if isinstance(value, datetime.datetime):
		return value.date().isoformat()
	if isinstance(value, datetime.date):
		return value.isoformat()
	text = str(value).strip().strip('"').strip("'")
	if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-":
		candidate = text[:10]
		try:
			datetime.date.fromisoformat(candidate)
			return candidate
		except ValueError:
			pass
	return text


def _sanitize_filters(filters):
	"""Liste de filtres Frappe, ou None si payload vide / illisible."""
	if filters in (None, "", [], {}, ()):
		return None
	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except Exception:
			return None
	if not isinstance(filters, (list, tuple)):
		return None
	cleaned = []
	for row in filters:
		if isinstance(row, (list, tuple)) and len(row) >= 3:
			cleaned.append(list(row))
		elif isinstance(row, dict) and row.get("fieldname") and row.get("operator"):
			cleaned.append(row)
	return cleaned or None


def _safe_get_events(get_events, start, end, filters):
	try:
		return get_events(start=start, end=end, filters=filters) or []
	except Exception:
		if filters:
			try:
				return get_events(start=start, end=end, filters=None) or []
			except Exception:
				return []
		return []


@frappe.whitelist()
def get_calendar_employees(start, end, filters=None):
	"""Employés distincts ayant au moins un Event visible sur [start, end].

	Réutilise `get_events` (permissions Public / Private / partages / User Permissions)
	pour que le filtre liste exactement les personnes présentes sur la vue calendrier.
	"""
	from vt_internal.vt_internal.overrides.event import get_events

	start = _as_date_param(start)
	end = _as_date_param(end)
	filters = _sanitize_filters(filters)
	events = _safe_get_events(get_events, start, end, filters)
	ids = {_event_employee_id(e) for e in events}
	return build_employee_rows(events, _employee_details(ids))

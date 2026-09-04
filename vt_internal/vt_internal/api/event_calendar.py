# Copyright (c) 2026, Verre & Transparence and contributors
# API du drawer d'événement (remplace le popover natif sur le calendrier Dokos).
#
#   - get_event_detail : détail enrichi (VT/FDT, adresse, téléphone) pour la modale
#   - get_calendar_employees : employés distincts visibles sur [start, end]

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
	return (event.get("custom_employé") or "").strip()


def build_employee_rows(events, employee_details=None):
	"""Agrège les Events en lignes sidebar : name, employee_name, color, event_count.

	`employee_details` : {employee_name_id: {employee_name, custom_couleur}}.
	Les événements sans `custom_employé` sont regroupés sous une ligne « Sans employé ».
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
	if frappe.db.has_column("Employee", "custom_couleur"):
		fields.append("custom_couleur")
	details = {}
	for row in frappe.get_list(
		"Employee",
		filters={"name": ["in", ids]},
		fields=fields,
		limit_page_length=500,
	):
		details[row.name] = row
	return details


@frappe.whitelist()
def get_calendar_employees(start, end, filters=None):
	"""Employés distincts ayant au moins un Event visible sur [start, end].

	Réutilise `get_events` (permissions Public / Private / partages / User Permissions)
	pour que la sidebar liste exactement les personnes présentes sur la vue calendrier.
	"""
	from vt_internal.vt_internal.overrides.event import get_events

	if isinstance(filters, str):
		filters = json.loads(filters)

	events = get_events(start=start, end=end, filters=filters)
	ids = {_event_employee_id(e) for e in events}
	return build_employee_rows(events, _employee_details(ids))

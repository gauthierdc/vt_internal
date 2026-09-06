"""Assignation multi-employés sur Event (Option A).

Un Event reste **un** document. Les employés sont une table enfant
(`Event Employee` / `custom_event_employees`). L'ancien Link
`custom_employé` n'est plus une source d'écriture : on le lit en repli
seulement si la table enfant est vide, puis on le vide (migrate + validate).

Règle de couleur (documentée) :
- `Event.color` canonique : véhicule gagne si `custom_vehicle` est posé ;
  sinon couleur du premier employé ; sinon jaune `#FFEE00`.
- Blocs calendrier (affichage seulement) : couleur de **cet** employé,
  même si un véhicule est rattaché.
"""

from __future__ import annotations

DEFAULT_EVENT_COLOR = "#FFEE00"
EVENT_EMPLOYEE_DOCTYPE = "Event Employee"
EVENT_EMPLOYEE_FIELD = "custom_event_employees"
LEGACY_EMPLOYEE_FIELD = "custom_employé"

# Fragment SQL : l'Event est assigné à %(employee)s (table enfant, sinon Link).
# `event_alias` = alias de `tabEvent` (ex. "e" ou "`tabEvent`").
EVENT_ASSIGNED_TO_EMPLOYEE_SQL = """(
	EXISTS (
		SELECT 1 FROM `tabEvent Employee` ee
		WHERE ee.parent = {event}.name
		  AND ee.parenttype = 'Event'
		  AND ee.employee = %(employee)s
	)
	OR (
		{event}.`custom_employé` = %(employee)s
		AND NOT EXISTS (
			SELECT 1 FROM `tabEvent Employee` ee2
			WHERE ee2.parent = {event}.name
			  AND ee2.parenttype = 'Event'
		)
	)
)"""


def child_table_ready():
	"""True si la table enfant existe (après migrate / sync DocType)."""
	try:
		import frappe

		return bool(frappe.db.table_exists(EVENT_EMPLOYEE_DOCTYPE))
	except Exception:
		return False


def _legacy_employee(obj):
	if obj is None:
		return ""
	if isinstance(obj, dict):
		return (obj.get(LEGACY_EMPLOYEE_FIELD) or "").strip()
	return (getattr(obj, LEGACY_EMPLOYEE_FIELD, None) or "").strip()


def _row_employee(row):
	if isinstance(row, dict):
		return (row.get("employee") or "").strip()
	return (getattr(row, "employee", None) or "").strip()


def employee_ids_from_rows(rows, legacy=None):
	"""IDs uniques dans l'ordre : lignes enfant, sinon Link déprécié."""
	ids = []
	seen = set()
	for row in rows or []:
		emp = _row_employee(row)
		if not emp or emp in seen:
			continue
		seen.add(emp)
		ids.append(emp)
	if ids:
		return ids
	legacy_id = (legacy or "").strip()
	return [legacy_id] if legacy_id else []


def get_event_employee_ids(doc):
	"""Employés assignés à un Event (doc Frappe ou dict)."""
	if not doc:
		return []
	rows = None
	if isinstance(doc, dict):
		rows = doc.get(EVENT_EMPLOYEE_FIELD)
	else:
		if hasattr(doc, "meta") and doc.meta.has_field(EVENT_EMPLOYEE_FIELD):
			rows = doc.get(EVENT_EMPLOYEE_FIELD)
		else:
			rows = getattr(doc, EVENT_EMPLOYEE_FIELD, None)
	return employee_ids_from_rows(rows, legacy=_legacy_employee(doc))


def _append_employee(doc, employee):
	row = {"employee": employee}
	if hasattr(doc, "append"):
		doc.append(EVENT_EMPLOYEE_FIELD, row)
		return
	rows = list(doc.get(EVENT_EMPLOYEE_FIELD) or [])
	rows.append(row)
	if isinstance(doc, dict):
		doc[EVENT_EMPLOYEE_FIELD] = rows


def _clear_legacy_employee(doc):
	"""Vide le Link déprécié : la table enfant est seule source de vérité."""
	if not doc:
		return
	if isinstance(doc, dict):
		doc[LEGACY_EMPLOYEE_FIELD] = None
		return
	if hasattr(doc, "meta") and not doc.meta.has_field(LEGACY_EMPLOYEE_FIELD):
		return
	if hasattr(doc, "set"):
		doc.set(LEGACY_EMPLOYEE_FIELD, None)
	else:
		setattr(doc, LEGACY_EMPLOYEE_FIELD, None)


def absorb_legacy_employee(doc):
	"""Repli old-client : n'absorbe `custom_employé` que si la table est vide.

	Dès qu'il y a au moins une ligne enfant, on ne réinjecte jamais le Link
	(sinon on ne peut plus retirer l'employé d'origine ni passer « Sans employé »).
	Dans tous les cas on vide le Link après traitement.
	"""
	if not doc:
		return
	if hasattr(doc, "meta") and not doc.meta.has_field(EVENT_EMPLOYEE_FIELD):
		return
	ids = employee_ids_from_rows(doc.get(EVENT_EMPLOYEE_FIELD))
	if ids:
		_clear_legacy_employee(doc)
		return
	legacy = _legacy_employee(doc)
	if legacy:
		_append_employee(doc, legacy)
	_clear_legacy_employee(doc)


def dedupe_employee_rows(doc):
	"""Supprime les lignes vides / doublons (premier idx conservé)."""
	if not doc:
		return
	if hasattr(doc, "meta") and not doc.meta.has_field(EVENT_EMPLOYEE_FIELD):
		return
	table = doc.get(EVENT_EMPLOYEE_FIELD)
	if not table:
		return
	seen = set()
	to_remove = []
	for row in list(table):
		emp = _row_employee(row)
		if not emp or emp in seen:
			to_remove.append(row)
		else:
			seen.add(emp)
	for row in to_remove:
		if hasattr(doc, "remove"):
			doc.remove(row)
		else:
			table.remove(row)


def first_employee_id(doc):
	ids = get_event_employee_ids(doc)
	return ids[0] if ids else ""


def resolve_canonical_color(vehicle_color, employee_colors):
	"""Couleur stockée sur Event.color.

	Véhicule gagne s'il a une couleur ; sinon premier employé ; sinon jaune.
	"""
	if vehicle_color:
		return vehicle_color
	for color in employee_colors or []:
		if color:
			return color
	return DEFAULT_EVENT_COLOR


def calendar_instance_id(event_name, starts_on, employee):
	"""Id FullCalendar unique (le `name` Event reste celui du document)."""
	start = str(starts_on or "")
	emp = (employee or "").strip() or "_"
	return f"{event_name}::{start}::{emp}"


def expand_calendar_events(events, employees_by_event, employee_colors=None):
	"""Duplique chaque Event en N items d'affichage (1 par employé).

	`employees_by_event` : {event_name: [employee_id, ...]}.
	Sans employé (ni table, ni Link) → un item « Sans employé ».
	La couleur de chaque item = couleur de cet employé (pas le véhicule).
	"""
	employee_colors = employee_colors or {}
	result = []
	for event in events or []:
		if isinstance(event, dict):
			name = event.get("name")
			legacy = (event.get(LEGACY_EMPLOYEE_FIELD) or "").strip()
			starts_on = event.get("starts_on")
		else:
			name = event.get("name")
			legacy = (event.get(LEGACY_EMPLOYEE_FIELD) or "").strip()
			starts_on = event.get("starts_on")

		emps = list(employees_by_event.get(name) or [])
		if not emps and legacy:
			emps = [legacy]
		if not emps:
			emps = [""]

		for emp in emps:
			if hasattr(event, "copy"):
				item = event.copy()
			else:
				item = dict(event)
			item[LEGACY_EMPLOYEE_FIELD] = emp
			item["calendar_instance_id"] = calendar_instance_id(name, starts_on, emp)
			if emp:
				emp_color = employee_colors.get(emp)
				if emp_color:
					item["color"] = emp_color
				elif not item.get("color"):
					item["color"] = DEFAULT_EVENT_COLOR
			result.append(item)
	return result


def event_assigned_sql(event_alias="e"):
	"""Clause SQL : Event assigné à %(employee)s (enfant + repli Link)."""
	return EVENT_ASSIGNED_TO_EMPLOYEE_SQL.format(event=event_alias)

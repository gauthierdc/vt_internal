"""Ajoute la table enfant Event Employee + migre `custom_employé`.

Idempotent : ré-exécutable (create_custom_fields update=True, INSERT … NOT EXISTS).
Le champ Link `custom_employé` est conservé (lecture de repli) mais masqué
sur le formulaire ; on n'y écrit plus depuis le code de l'app.
"""

from __future__ import annotations

import frappe

from vt_internal.vt_internal.utils.event_employees import (
	EVENT_EMPLOYEE_DOCTYPE,
	EVENT_EMPLOYEE_FIELD,
	LEGACY_EMPLOYEE_FIELD,
)


def execute():
	ensure_custom_field()
	hide_legacy_employee_field()
	migrate_legacy_employees()


def ensure_custom_field():
	"""Table field sur Event (Custom Field, Event est un DocType standard)."""
	if not frappe.db.exists("DocType", "Event"):
		return
	if not frappe.db.exists("DocType", EVENT_EMPLOYEE_DOCTYPE):
		frappe.reload_doc("vt_internal", "doctype", "event_employee", force=True)

	insert_after = LEGACY_EMPLOYEE_FIELD if _has_column("Event", LEGACY_EMPLOYEE_FIELD) else "event_type"
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	fields = {
		"Event": [
			{
				"fieldname": EVENT_EMPLOYEE_FIELD,
				"label": "Employés",
				"fieldtype": "Table",
				"options": EVENT_EMPLOYEE_DOCTYPE,
				"insert_after": insert_after,
				"description": (
					"Plusieurs employés : le calendrier affiche un bloc coloré par personne "
					"(même créneau). Un seul document Event."
				),
				"translatable": 0,
			}
		]
	}
	try:
		create_custom_fields(fields, ignore_validate=True, update=True)
	except TypeError:
		create_custom_fields(fields, ignore_validate=True)


def hide_legacy_employee_field():
	"""Masque le Link unique déprécié une fois la table en place."""
	if not _has_column("Event", LEGACY_EMPLOYEE_FIELD):
		return
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for prop, value, ptype in (
		("hidden", "1", "Check"),
		("read_only", "1", "Check"),
		("label", "Employé (obsolète)", "Data"),
	):
		try:
			make_property_setter(
				"Event",
				LEGACY_EMPLOYEE_FIELD,
				prop,
				value,
				ptype,
				for_doctype=False,
				validate_fields_for_doctype=False,
			)
		except TypeError:
			make_property_setter(
				"Event",
				LEGACY_EMPLOYEE_FIELD,
				prop,
				value,
				ptype,
				for_doctype=False,
			)


def migrate_legacy_employees():
	"""Copie Event.custom_employé → tabEvent Employee (sans écraser l'existant)."""
	if not frappe.db.table_exists(EVENT_EMPLOYEE_DOCTYPE):
		return
	if not _has_column("Event", LEGACY_EMPLOYEE_FIELD):
		return

	# Insertion SQL : un row par Event encore non migré. Noms hash 10 chars.
	rows = frappe.db.sql(
		f"""
		SELECT e.name AS parent, e.`{LEGACY_EMPLOYEE_FIELD}` AS employee
		FROM `tabEvent` e
		WHERE e.`{LEGACY_EMPLOYEE_FIELD}` IS NOT NULL
		  AND e.`{LEGACY_EMPLOYEE_FIELD}` != ''
		  AND NOT EXISTS (
			SELECT 1 FROM `tabEvent Employee` ee
			WHERE ee.parent = e.name
			  AND ee.parenttype = 'Event'
			  AND ee.employee = e.`{LEGACY_EMPLOYEE_FIELD}`
		  )
		""",
		as_dict=True,
	)
	if not rows:
		return

	now = frappe.utils.now()
	user = frappe.session.user or "Administrator"
	for row in rows:
		idx = (
			frappe.db.sql(
				"""
				SELECT COALESCE(MAX(idx), 0) FROM `tabEvent Employee`
				WHERE parent = %s AND parenttype = 'Event'
				""",
				row.parent,
			)[0][0]
			+ 1
		)
		name = frappe.generate_hash(length=10)
		frappe.db.sql(
			"""
			INSERT INTO `tabEvent Employee`
				(name, creation, modified, modified_by, owner, docstatus, idx,
				 parent, parentfield, parenttype, employee)
			VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, 'Event', %s)
			""",
			(
				name,
				now,
				now,
				user,
				user,
				idx,
				row.parent,
				EVENT_EMPLOYEE_FIELD,
				row.employee,
			),
		)

	frappe.logger().info(f"add_event_employee_table: {len(rows)} Event(s) migrés")


def _has_column(doctype, column):
	try:
		return frappe.db.has_column(doctype, column)
	except Exception:
		return False

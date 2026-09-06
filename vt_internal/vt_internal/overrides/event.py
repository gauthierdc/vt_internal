# WORKAROUND TEMPORAIRE - À SUPPRIMER quand corrigé upstream
# Issue: https://github.com/frappe/erpnext/issues/49677
#
# Problème: Les User Permissions ne sont pas appliquées en mode calendrier
# car la requête SQL de get_events() dans frappe bypass build_match_conditions()
#
# Solution: Appeler build_match_conditions() directement pour générer
# les conditions de filtre basées sur les User Permissions
#
# À supprimer quand corrigé dans frappe:
# - Ce fichier (overrides/event.py)
# - La ligne override_whitelisted_methods dans hooks.py
# - Le dossier overrides/ si vide

import datetime
import json

import frappe
from frappe.desk.calendar import process_recurring_events
from frappe.model.db_query import DatabaseQuery
from frappe.utils import get_datetime, getdate


def get_match_conditions_for_event(user, ignore_permissions=False):
	"""
	Génère les conditions SQL pour les User Permissions sur Event.
	Retourne une chaîne SQL à ajouter dans la clause WHERE.
	"""
	if ignore_permissions:
		return ""

	query = DatabaseQuery("Event", user=user)
	query.tables = ["`tabEvent`"]
	match_cond = query.build_match_conditions(as_condition=True)

	if match_cond:
		return " AND " + match_cond
	return ""


@frappe.whitelist()
def get_events(
	start: str | datetime.date,
	end: str | datetime.date,
	user=None,
	for_reminder=False,
	filters=None,
	field_map=None,
	limit_start=0,
	limit_page_length=None,
	additional_condition=None,
	ignore_permissions=False,
) -> list[frappe._dict]:
	if not user:
		user = frappe.session.user

	if isinstance(filters, str):
		filters = json.loads(filters)

	additional_fields = ""
	if field_map:
		additional_fields = ", " + ", ".join(
			[f"`tabEvent`.{f}" for f in frappe.parse_json(field_map).values()]
		)

	# Construire les conditions de filtre standard
	filter_condition = ""
	if filters:
		from frappe.desk.reportview import get_filters_cond

		filter_condition = get_filters_cond("Event", filters, [], ignore_permissions=ignore_permissions)

	# FIX: Ajouter les conditions User Permissions (le coeur de la correction)
	match_conditions = get_match_conditions_for_event(user, ignore_permissions)

	tables = ["`tabEvent`"]
	if filter_condition and "`tabEvent Participants`" in filter_condition:
		tables.append("`tabEvent Participants`")

	# custom_employé : repli transition. La table enfant est jointe après coup
	# pour produire N blocs calendrier (1 par employé) sans casser les permissions.
	events = frappe.db.sql(
		"""
		SELECT `tabEvent`.name,
				`tabEvent`.subject,
				`tabEvent`.image,
				`tabEvent`.status,
				`tabEvent`.description,
				`tabEvent`.color,
				`tabEvent`.starts_on,
				`tabEvent`.ends_on,
				`tabEvent`.owner,
				`tabEvent`.all_day,
				`tabEvent`.event_type,
				`tabEvent`.repeat_this_event,
				`tabEvent`.rrule,
				`tabEvent`.repeat_till,
				`tabEvent`.`custom_employé`
				{additional_fields}
		FROM {tables}
		WHERE (
				(
					(date(`tabEvent`.starts_on) BETWEEN date(%(start)s) AND date(%(end)s))
					OR (date(`tabEvent`.ends_on) BETWEEN date(%(start)s) AND date(%(end)s))
					OR (
						date(`tabEvent`.starts_on) <= date(%(start)s)
						AND date(`tabEvent`.ends_on) >= date(%(end)s)
					)
				)
				OR (
					date(`tabEvent`.starts_on) <= date(%(start)s)
					AND `tabEvent`.repeat_this_event=1
					AND coalesce(`tabEvent`.repeat_till, '3000-01-01') > date(%(start)s)
				)
			)
		{reminder_condition}
		{filter_condition}
		{match_conditions}
		AND (
				`tabEvent`.event_type='Public'
				OR `tabEvent`.owner=%(user)s
				OR EXISTS(
					SELECT `tabDocShare`.name
					FROM `tabDocShare`
					WHERE `tabDocShare`.share_doctype='Event'
						AND `tabDocShare`.share_name=`tabEvent`.name
						AND `tabDocShare`.user=%(user)s
				)
			)
		{additional_condition}
		ORDER BY {order_by}
		{limit_condition}""".format(
			additional_fields=additional_fields,
			tables=", ".join(tables),
			filter_condition=filter_condition,
			match_conditions=match_conditions,  # <-- AJOUT CLÉ
			reminder_condition="AND coalesce(`tabEvent`.send_reminder, 0)=1" if for_reminder else "",
			limit_condition=f"LIMIT {limit_page_length} OFFSET {limit_start}" if limit_page_length else "",
			order_by="`tabEvent`.starts_on desc" if limit_page_length else "`tabEvent`.starts_on",
			additional_condition=additional_condition or "",
		),
		{
			"start": start,
			"end": end,
			"user": user,
		},
		as_dict=1,
	)

	result = []
	for event in events:
		if event.get("repeat_this_event"):
			event_start = get_datetime(start).replace(hour=0, minute=0, second=0)
			event_end = get_datetime(end).replace(hour=0, minute=0, second=0)
			if getdate(end).year < 9999:
				event_end += datetime.timedelta(days=1)

			event.doctype = "Event"
			recurring_events = list(
				process_recurring_events(event, event_start, event_end, "starts_on", "ends_on", "rrule")
			)

			if recurring_events:
				result.extend(recurring_events)
			elif event.starts_on <= event_end and (not event.ends_on or event.ends_on >= event_start):
				result.append(event)

		else:
			result.append(event)

	result = _split_events_for_calendar(result)
	return sorted(result, key=lambda d: d["starts_on"])


def _split_events_for_calendar(events):
	"""1 Event → N items FullCalendar (même name, id d'instance unique)."""
	from vt_internal.vt_internal.utils.event_employees import (
		child_table_ready,
		expand_calendar_events,
	)

	if not events:
		return events

	employees_by_event = {}
	if child_table_ready():
		names = list({e.get("name") for e in events if e.get("name")})
		if names:
			rows = frappe.db.sql(
				"""
				SELECT parent, employee
				FROM `tabEvent Employee`
				WHERE parent IN %(names)s
				  AND parenttype = 'Event'
				  AND employee IS NOT NULL
				  AND employee != ''
				ORDER BY idx ASC
				""",
				{"names": names},
				as_dict=True,
			)
			for row in rows:
				employees_by_event.setdefault(row.parent, [])
				if row.employee not in employees_by_event[row.parent]:
					employees_by_event[row.parent].append(row.employee)

	emp_ids = {emp for emps in employees_by_event.values() for emp in emps}
	for event in events:
		legacy = (event.get("custom_employé") or "").strip()
		if legacy:
			emp_ids.add(legacy)

	employee_colors = {}
	if emp_ids:
		try:
			if frappe.db.has_column("Employee", "custom_couleur"):
				for row in frappe.db.get_all(
					"Employee",
					filters={"name": ["in", list(emp_ids)]},
					fields=["name", "custom_couleur"],
				):
					if row.custom_couleur:
						employee_colors[row.name] = row.custom_couleur
		except Exception:
			employee_colors = {}

	return expand_calendar_events(events, employees_by_event, employee_colors)

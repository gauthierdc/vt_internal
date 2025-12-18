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
				`tabEvent`.repeat_till
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

	return sorted(result, key=lambda d: d["starts_on"])

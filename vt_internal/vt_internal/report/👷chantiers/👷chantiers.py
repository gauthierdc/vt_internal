# Copyright (c) 2025, Verre & Transparence and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	Filters expected: {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "company": "Company name"}
	"""
	filters = filters or {}

	end_date = filters.get('end_date') or frappe.utils.nowdate()
	start_date = filters.get('start_date') or frappe.utils.add_to_date(end_date, days=-7)
	filters['end_date'] = end_date
	filters['start_date'] = start_date

	# Build Timesheet filters
	timesheet_filters_filters = [
		['docstatus', '!=', 2],
		["Timesheet Detail", "project", "is", "set"],
	]

	not_project_timesheet_filters = [
		['docstatus', '!=', 2],
	]

	if filters.get('company'):
		timesheet_filters_filters.append(['company', '=', filters.get('company')])
		not_project_timesheet_filters.append(['company', '=', filters.get('company')])
	# cost_center filter removed - not applied server-side

	timesheet_filters_filters.append(['end_date', 'between', [start_date, end_date]])
	not_project_timesheet_filters.append(['end_date', 'between', [start_date, end_date]])

	# aggregate timesheets by project using SQL to avoid restricted subqueries
	where = ["t.docstatus != 2", "d.project IS NOT NULL"]
	params: list = []
	if filters.get('company'):
		where.append("t.company = %s")
		params.append(filters.get('company'))
	# cost_center filter removed - do not add WHERE on cost_center
	# date range on timesheet.end_date
	where.append("t.end_date BETWEEN %s AND %s")
	params.extend([start_date, end_date])

	sql = f"""
		SELECT
			d.project AS project,
			SUM(d.costing_amount) AS costing_amount,
			SUM(d.hours) AS hours,
			SUM(CASE WHEN d.custom_sav = 1 THEN d.hours ELSE 0 END) AS sav_hours
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name
		WHERE {' AND '.join(where)}
		GROUP BY d.project
	"""

	tss = frappe.db.sql(sql, tuple(params), as_dict=True)

	ch_hours = round(sum([(t.get("hours") or 0) for t in tss]))

	columns = [
		"Client::200",
		"Projet::200",
		"Montant:Currency:120",
		"Type de projet",
		"Temps",
		"dont SAV",
		"Temps prévu",
		"Date de fin (facture):Date",
		"Délai date de réf.",
		"Réception de travaux::50",
		"Incident qualité::50",
	]

	mydata = []
	mydata.append([f"<b>Heures chantiers</b>", "", "", "", ch_hours, "", "", "", "", "", ""])

	for t in tss:
		project_name = t.get('project')
		p = frappe.db.get_value("Project", project_name, ["status", 'project_type', 'expected_end_date', 'customer', 'custom_estimated_labor_hours', 'total_sales_amount'])

		reception_name = frappe.db.get_value('Work Completion Receipt', {'project': project_name}, ['name'])
		reception_link = reception_name and f"<a href={frappe.utils.get_url_to_form('Work Completion Receipt', reception_name)}>📝</a>" or ""

		incident_name = frappe.db.get_value('Quality Incident', {'project': project_name}, ['name'])
		incident_link = incident_name and f"<a href={frappe.utils.get_url_to_form('Quality Incident', incident_name)}>⚠️</a>" or ""

		date = (p and p[0] == "Completed" and p[2]) or ''
		delai = ''
		if date:
			delai = frappe.utils.date_diff(date, end_date)

		expected_hours = (p and p[4]) or 0
		montant = (p and p[5]) or 0
		hours = round(t.get('hours') or 0)
		hours_str = f"<b style='color:gray'>{hours}</b>"
		if p and p[0] == "Completed" and hours <= (expected_hours or 0):
			hours_str = f"<b style='color:green'>{hours}</b>"
		if hours > (expected_hours or 0):
			hours_str = f"<b style='color:red'>{hours}</b>"

		mydata.append([
			p and p[3] or '',
			f"<a href={frappe.utils.get_url_to_form('Project', project_name)}#documents_tab>{project_name}</a>",
			montant,
			p and p[1] or '',
			hours_str,
			t.get('sav_hours'),
			expected_hours,
			date,
			delai,
			reception_link,
			incident_link,
		])

	# Visite technique
	# Visite technique (not project)
	where_not = ["t.docstatus != 2"]
	params_not: list = []
	if filters.get('company'):
		where_not.append("t.company = %s")
		params_not.append(filters.get('company'))
	# cost_center filter removed for non-project aggregates
	where_not.append("t.end_date BETWEEN %s AND %s")
	params_not.extend([start_date, end_date])

	sql_vt = f"""
		SELECT SUM(d.hours) AS hours
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name
		WHERE {' AND '.join(where_not)} AND d.activity_type = %s
	"""
	vt_rows = frappe.db.sql(sql_vt, tuple([*params_not, 'Visite technique']), as_dict=True)
	vt_hours = round(sum([(r.get('hours') or 0) for r in vt_rows]))

	# Atelier
	# Atelier (not project)
	sql_at = f"""
		SELECT SUM(d.hours) AS hours
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name
		WHERE {' AND '.join(where_not)} AND d.activity_type = %s
	"""
	at_rows = frappe.db.sql(sql_at, tuple([*params_not, 'Atelier']), as_dict=True)
	at_hours = round(sum([(r.get('hours') or 0) for r in at_rows]))
	total_hours = max(1, at_hours + vt_hours + ch_hours)

	mydata.append([f"<b>Frais généraux</b>", "", "", "", at_hours + vt_hours, f"<u>{round(ch_hours / total_hours * 100)}%</u>", "", "", "", "", ""])
	mydata.append(["", f"<b>Visite technique</b>", "", "", vt_hours, "", "", "", "", "", ""])
	mydata.append(["", f"<b>Atelier</b>", "", "", at_hours, "", "", "", "", "", ""])

	return columns, mydata

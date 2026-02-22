# Copyright (c) 2025, Verre & Transparence and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import getdate, time_diff_in_hours


def execute(filters=None):
	"""Return columns and data for the Previsionnel Chantier report."""
	filters = filters or {}

	start_date = filters.get("start_date")
	end_date = filters.get("end_date")

	if not start_date or not end_date:
		frappe.throw(_("Les dates de début et de fin sont requises"))

	if getdate(start_date) > getdate(end_date):
		frappe.throw(_("La date de début doit être antérieure à la date de fin"))

	grouped_by = filters.get("grouped_by", "Projet")

	columns = get_columns(grouped_by)
	data = get_data(filters, grouped_by)

	total_hours = sum(row.get("heures_prevues", 0) for row in data)
	total_ca = sum(row.get("ca_projet", 0) for row in data)

	# Formater le CA
	if total_ca >= 1000000:
		ca_formatted = f"{total_ca / 1000000:.1f}M €"
	elif total_ca >= 1000:
		ca_formatted = f"{total_ca / 1000:.0f}k €"
	else:
		ca_formatted = f"{total_ca:.0f} €"

	message = f"""
	<div style="display: flex; gap: 20px;">
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; display: inline-block;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase;">Total heures prévues</div>
			<div style="font-size: 36px; font-weight: bold; color: #1976d2;">{round(total_hours)}h</div>
		</div>
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; display: inline-block;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase;">CA prévu</div>
			<div style="font-size: 36px; font-weight: bold; color: #2e7d32;">{ca_formatted}</div>
		</div>
	</div>
	"""

	return columns, data, message


def get_columns(grouped_by):
	"""Return columns based on grouping mode."""
	if grouped_by == "Projet":
		return [
			{"label": _("Projet"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 200},
			{"label": _("Client"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
			{"label": _("CA du projet (HT)"), "fieldname": "ca_projet", "fieldtype": "Currency", "width": 130},
			{"label": _("Type de projet"), "fieldname": "project_type", "fieldtype": "Link", "options": "Project Type", "width": 120},
			{"label": _("Incidents"), "fieldname": "incidents", "fieldtype": "HTML", "width": 100},
			{"label": _("Heures prévues"), "fieldname": "heures_prevues", "fieldtype": "Float", "width": 120},
		]
	else:
		return [
			{"label": _("Employé"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 200},
			{"label": _("Nom"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
			{"label": _("Heures prévues"), "fieldname": "heures_prevues", "fieldtype": "Float", "width": 120},
			{"label": _("Nombre de projets"), "fieldname": "nb_projets", "fieldtype": "Int", "width": 120},
		]


def get_data(filters, grouped_by):
	"""Fetch and aggregate event data."""
	start_date = filters.get("start_date")
	end_date = filters.get("end_date")

	conditions = ["e.project IS NOT NULL", "e.project != ''"]
	params = {"start_date": start_date, "end_date": end_date}

	conditions.append("DATE(e.starts_on) >= %(start_date)s")
	conditions.append("DATE(e.starts_on) <= %(end_date)s")

	if filters.get("project_type"):
		conditions.append("p.project_type = %(project_type)s")
		params["project_type"] = filters.get("project_type")

	if filters.get("employee"):
		conditions.append("e.custom_employé = %(employee)s")
		params["employee"] = filters.get("employee")

	if filters.get("construction_manager"):
		conditions.append("p.custom_construction_manager = %(construction_manager)s")
		params["construction_manager"] = filters.get("construction_manager")

	where_clause = " AND ".join(conditions)

	sql = f"""
		SELECT
			e.name AS event_name,
			e.project,
			e.custom_employé AS employee,
			e.starts_on,
			e.ends_on,
			p.customer,
			p.total_sales_amount AS ca_projet,
			p.project_type,
			emp.employee_name
		FROM `tabEvent` e
		LEFT JOIN `tabProject` p ON p.name = e.project
		LEFT JOIN `tabEmployee` emp ON emp.name = e.custom_employé
		WHERE {where_clause}
		ORDER BY e.starts_on
	"""

	events = frappe.db.sql(sql, params, as_dict=True)

	if grouped_by == "Projet":
		return aggregate_by_project(events)
	else:
		return aggregate_by_employee(events)


def aggregate_by_project(events):
	"""Aggregate events by project."""
	project_data = defaultdict(lambda: {
		"customer": None,
		"ca_projet": 0,
		"project_type": None,
		"heures_prevues": 0,
	})

	for event in events:
		project = event.get("project")
		if not project:
			continue

		hours = calculate_hours(event.get("starts_on"), event.get("ends_on"))

		project_data[project]["customer"] = event.get("customer")
		project_data[project]["ca_projet"] = event.get("ca_projet") or 0
		project_data[project]["project_type"] = event.get("project_type")
		project_data[project]["heures_prevues"] += hours

	data = []
	for project, info in project_data.items():
		incidents = get_quality_incidents(project)

		data.append({
			"project": project,
			"customer": info["customer"],
			"ca_projet": info["ca_projet"],
			"project_type": info["project_type"],
			"incidents": incidents,
			"heures_prevues": round(info["heures_prevues"], 2),
		})

	data.sort(key=lambda x: x["heures_prevues"], reverse=True)

	return data


def aggregate_by_employee(events):
	"""Aggregate events by employee."""
	employee_data = defaultdict(lambda: {
		"employee_name": None,
		"heures_prevues": 0,
		"projects": set(),
	})

	for event in events:
		employee = event.get("employee")
		if not employee:
			continue

		hours = calculate_hours(event.get("starts_on"), event.get("ends_on"))

		employee_data[employee]["employee_name"] = event.get("employee_name")
		employee_data[employee]["heures_prevues"] += hours
		if event.get("project"):
			employee_data[employee]["projects"].add(event.get("project"))

	data = []
	for employee, info in employee_data.items():
		data.append({
			"employee": employee,
			"employee_name": info["employee_name"],
			"heures_prevues": round(info["heures_prevues"], 2),
			"nb_projets": len(info["projects"]),
		})

	data.sort(key=lambda x: x["heures_prevues"], reverse=True)

	return data


def calculate_hours(starts_on, ends_on):
	"""Calculate hours between two datetimes."""
	if not starts_on or not ends_on:
		return 0

	try:
		hours = time_diff_in_hours(ends_on, starts_on)
		return max(0, hours)
	except Exception:
		return 0


def get_quality_incidents(project):
	"""Get quality incidents for a project as HTML links."""
	incidents = frappe.db.get_all(
		"Quality Incident",
		filters={"project": project},
		fields=["name"],
	)

	if not incidents:
		return ""

	links = []
	for incident in incidents:
		url = frappe.utils.get_url_to_form("Quality Incident", incident.name)
		links.append(f'<a href="{url}">⚠️</a>')

	return " ".join(links)

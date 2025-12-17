# Copyright (c) 2025, Verre & Transparence and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate
from collections import defaultdict
import json


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})

	if not filters.get("fiscal_year"):
		frappe.throw(_("L'année fiscale est obligatoire"))

	# Get fiscal year dates
	fy = frappe.get_doc("Fiscal Year", filters.fiscal_year)
	start_date = fy.year_start_date
	end_date = fy.year_end_date

	# Get users filter
	users = filters.get("user") or []
	if isinstance(users, str):
		users = [users]

	# Return empty if no users selected
	if not users:
		return get_columns(), [], None

	# Get range
	range_type = filters.get("range") or "Mois"

	# Get data
	quotations = get_quotations(users, start_date, end_date)
	sales_orders = get_sales_orders(users, start_date, end_date)
	invoices = get_invoices(users, start_date, end_date)
	objectives = get_objectives(users, filters.fiscal_year)

	# Aggregate by period
	data, chart_data = aggregate_data(quotations, sales_orders, invoices, objectives, range_type)

	# Apply cumulative if requested
	if filters.get("cumulative"):
		data = apply_cumulative(data)
		chart_data = apply_cumulative_chart(chart_data)

	columns = get_columns()
	message = generate_charts_html(chart_data)

	# Reverse data to show most recent first
	data.reverse()

	return columns, data, message


def get_columns():
	return [
		{"label": _("Période"), "fieldname": "period", "fieldtype": "Data", "width": 100},
		{"label": _("Nb Devis"), "fieldname": "nb_quotations", "fieldtype": "Int", "width": 80},
		{"label": _("Montant Devis"), "fieldname": "quotation_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Objectif Devis"), "fieldname": "quotation_objective", "fieldtype": "Currency", "width": 120},
		{"label": _("Nb Commandes"), "fieldname": "nb_orders", "fieldtype": "Int", "width": 80},
		{"label": _("Montant Cmd"), "fieldname": "order_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Objectif Cmd"), "fieldname": "order_objective", "fieldtype": "Currency", "width": 120},
		{"label": _("Nb Factures"), "fieldname": "nb_invoices", "fieldtype": "Int", "width": 80},
		{"label": _("Montant Fact"), "fieldname": "invoice_amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Objectif Fact"), "fieldname": "invoice_objective", "fieldtype": "Currency", "width": 120},
	]


def get_quotations(users, start_date, end_date):
	conditions = [
		"docstatus IN (0, 1)",
		"(custom_dernier_statut_de_suivi IS NULL OR custom_dernier_statut_de_suivi != 'Variante')",
		"transaction_date BETWEEN %(start_date)s AND %(end_date)s"
	]
	params = {"start_date": start_date, "end_date": end_date}

	if users:
		conditions.append("custom_responsable_du_devis IN %(users)s")
		params["users"] = users

	query = f"""
		SELECT
			transaction_date,
			total,
			1 as count
		FROM `tabQuotation`
		WHERE {' AND '.join(conditions)}
	"""

	return frappe.db.sql(query, params, as_dict=True)


def get_sales_orders(users, start_date, end_date):
	conditions = [
		"docstatus IN (0, 1)",
		"transaction_date BETWEEN %(start_date)s AND %(end_date)s"
	]
	params = {"start_date": start_date, "end_date": end_date}

	if users:
		conditions.append("custom_responsable_du_devis IN %(users)s")
		params["users"] = users

	query = f"""
		SELECT
			transaction_date,
			total,
			1 as count
		FROM `tabSales Order`
		WHERE {' AND '.join(conditions)}
	"""

	return frappe.db.sql(query, params, as_dict=True)


def get_invoices(users, start_date, end_date):
	conditions = [
		"si.docstatus = 1",
		"si.posting_date BETWEEN %(start_date)s AND %(end_date)s"
	]
	params = {"start_date": start_date, "end_date": end_date}

	if users:
		conditions.append("p.custom_project_manager IN %(users)s")
		params["users"] = users

	query = f"""
		SELECT
			si.posting_date as transaction_date,
			si.total,
			1 as count
		FROM `tabSales Invoice` si
		LEFT JOIN `tabProject` p ON p.name = si.project
		WHERE {' AND '.join(conditions)}
	"""

	return frappe.db.sql(query, params, as_dict=True)


def get_objectives(users, fiscal_year):
	"""Get objectives from VT Objective doctype, aggregated by week."""
	conditions = ["vo.fiscal_year = %(fiscal_year)s"]
	params = {"fiscal_year": fiscal_year}

	if users:
		conditions.append("vo.user IN %(users)s")
		params["users"] = users

	query = f"""
		SELECT
			vod.idx as week,
			SUM(vod.quotation_amount) as quotation_amount,
			SUM(vod.sales_order_amount) as sales_order_amount,
			SUM(vod.sales_invoice_amount) as sales_invoice_amount
		FROM `tabVT Objective` vo
		JOIN `tabVT Objective details` vod ON vod.parent = vo.name
		WHERE {' AND '.join(conditions)}
		GROUP BY vod.idx
	"""

	results = frappe.db.sql(query, params, as_dict=True)

	# Create a dict by week number
	objectives_by_week = {}
	for r in results:
		objectives_by_week[r.week] = {
			"quotation_amount": flt(r.quotation_amount),
			"sales_order_amount": flt(r.sales_order_amount),
			"sales_invoice_amount": flt(r.sales_invoice_amount),
		}

	return objectives_by_week


def get_week_number(date):
	"""Get ISO week number from date."""
	return getdate(date).isocalendar()[1]


def get_month_number(date):
	"""Get month number from date."""
	return getdate(date).month


def get_quarter_number(date):
	"""Get quarter number from date."""
	month = getdate(date).month
	return (month - 1) // 3 + 1


def get_period_label(period_num, range_type):
	"""Get label for a period."""
	if range_type == "Semaine":
		return f"S{period_num}"
	elif range_type == "Mois":
		months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
		return months[period_num - 1] if 1 <= period_num <= 12 else f"M{period_num}"
	else:  # Trimestre
		return f"T{period_num}"


def get_period_number(date, range_type):
	"""Get period number based on range type."""
	if range_type == "Semaine":
		return get_week_number(date)
	elif range_type == "Mois":
		return get_month_number(date)
	else:  # Trimestre
		return get_quarter_number(date)


def get_weeks_for_period(period_num, range_type):
	"""Get list of week numbers for a given period."""
	if range_type == "Semaine":
		return [period_num]
	elif range_type == "Mois":
		# Approximate: weeks 1-4 for month 1, 5-8 for month 2, etc.
		# More accurate would use actual calendar, but this is simpler
		start_week = (period_num - 1) * 4 + 1
		end_week = period_num * 4
		# Handle last month having more weeks
		if period_num == 12:
			end_week = 52
		return list(range(start_week, end_week + 1))
	else:  # Trimestre
		start_week = (period_num - 1) * 13 + 1
		end_week = period_num * 13
		if period_num == 4:
			end_week = 52
		return list(range(start_week, end_week + 1))


def get_period_count(range_type):
	"""Get total number of periods for range type."""
	if range_type == "Semaine":
		return 52
	elif range_type == "Mois":
		return 12
	else:  # Trimestre
		return 4


def aggregate_data(quotations, sales_orders, invoices, objectives, range_type):
	"""Aggregate data by period."""
	period_count = get_period_count(range_type)

	# Get current period to exclude future periods
	today = getdate(nowdate())
	current_period = get_period_number(today, range_type)

	# Initialize aggregated data
	aggregated = defaultdict(lambda: {
		"nb_quotations": 0,
		"quotation_amount": 0,
		"nb_orders": 0,
		"order_amount": 0,
		"nb_invoices": 0,
		"invoice_amount": 0,
		"quotation_objective": 0,
		"order_objective": 0,
		"invoice_objective": 0,
	})

	# Aggregate quotations
	for q in quotations:
		period = get_period_number(q.transaction_date, range_type)
		aggregated[period]["nb_quotations"] += 1
		aggregated[period]["quotation_amount"] += flt(q.total)

	# Aggregate sales orders
	for so in sales_orders:
		period = get_period_number(so.transaction_date, range_type)
		aggregated[period]["nb_orders"] += 1
		aggregated[period]["order_amount"] += flt(so.total)

	# Aggregate invoices
	for inv in invoices:
		period = get_period_number(inv.transaction_date, range_type)
		aggregated[period]["nb_invoices"] += 1
		aggregated[period]["invoice_amount"] += flt(inv.total)

	# Aggregate objectives by period
	for period_num in range(1, period_count + 1):
		weeks = get_weeks_for_period(period_num, range_type)
		for week in weeks:
			if week in objectives:
				aggregated[period_num]["quotation_objective"] += objectives[week]["quotation_amount"]
				aggregated[period_num]["order_objective"] += objectives[week]["sales_order_amount"]
				aggregated[period_num]["invoice_objective"] += objectives[week]["sales_invoice_amount"]

	# Build data rows and chart data
	data = []
	chart_data = {
		"labels": [],
		"quotation_realized": [],
		"quotation_objective": [],
		"order_realized": [],
		"order_objective": [],
		"invoice_realized": [],
		"invoice_objective": [],
	}

	# Only show periods up to current period (exclude future)
	max_period = min(period_count, current_period)

	for period_num in range(1, max_period + 1):
		label = get_period_label(period_num, range_type)
		agg = aggregated[period_num]

		data.append({
			"period": label,
			"nb_quotations": agg["nb_quotations"],
			"quotation_amount": agg["quotation_amount"],
			"quotation_objective": agg["quotation_objective"],
			"nb_orders": agg["nb_orders"],
			"order_amount": agg["order_amount"],
			"order_objective": agg["order_objective"],
			"nb_invoices": agg["nb_invoices"],
			"invoice_amount": agg["invoice_amount"],
			"invoice_objective": agg["invoice_objective"],
		})

		chart_data["labels"].append(label)
		chart_data["quotation_realized"].append(agg["quotation_amount"])
		chart_data["quotation_objective"].append(agg["quotation_objective"])
		chart_data["order_realized"].append(agg["order_amount"])
		chart_data["order_objective"].append(agg["order_objective"])
		chart_data["invoice_realized"].append(agg["invoice_amount"])
		chart_data["invoice_objective"].append(agg["invoice_objective"])

	return data, chart_data


def apply_cumulative(data):
	"""Apply cumulative sum to data."""
	cumulative = {
		"nb_quotations": 0,
		"quotation_amount": 0,
		"quotation_objective": 0,
		"nb_orders": 0,
		"order_amount": 0,
		"order_objective": 0,
		"nb_invoices": 0,
		"invoice_amount": 0,
		"invoice_objective": 0,
	}

	for row in data:
		for key in cumulative:
			cumulative[key] += flt(row[key])
			row[key] = cumulative[key]

	return data


def apply_cumulative_chart(chart_data):
	"""Apply cumulative sum to chart data."""
	for key in ["quotation_realized", "quotation_objective", "order_realized", "order_objective", "invoice_realized", "invoice_objective"]:
		cumsum = 0
		for i in range(len(chart_data[key])):
			cumsum += chart_data[key][i]
			chart_data[key][i] = cumsum

	return chart_data


def generate_charts_html(chart_data):
	"""Generate HTML with 3 charts using Frappe Charts."""
	labels_json = json.dumps(chart_data["labels"])

	# Format amounts for display (in thousands)
	def format_values(values):
		return json.dumps([round(v / 1000, 1) for v in values])

	html = f"""
	<div style="display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px;">
		<!-- Chart Devis -->
		<div style="flex: 1; min-width: 300px; background: #f9f9f9; border-radius: 8px; padding: 15px;">
			<h4 style="margin: 0 0 10px 0; color: #333;">Devis (k€)</h4>
			<div id="chart-devis"></div>
		</div>

		<!-- Chart Commandes -->
		<div style="flex: 1; min-width: 300px; background: #f9f9f9; border-radius: 8px; padding: 15px;">
			<h4 style="margin: 0 0 10px 0; color: #333;">Commandes (k€)</h4>
			<div id="chart-commandes"></div>
		</div>

		<!-- Chart Factures -->
		<div style="flex: 1; min-width: 300px; background: #f9f9f9; border-radius: 8px; padding: 15px;">
			<h4 style="margin: 0 0 10px 0; color: #333;">Factures (k€)</h4>
			<div id="chart-factures"></div>
		</div>
	</div>

	<script>
		frappe.require('frappe-charts.bundle.js', function() {{
			// Chart Devis
			new frappe.Chart("#chart-devis", {{
				data: {{
					labels: {labels_json},
					datasets: [
						{{ name: "Objectif", values: {format_values(chart_data["quotation_objective"])}, chartType: "line" }},
						{{ name: "Réalisé", values: {format_values(chart_data["quotation_realized"])}, chartType: "line" }}
					]
				}},
				type: "axis-mixed",
				height: 200,
				colors: ["#7cd6fd", "#5e64ff"],
				lineOptions: {{ regionFill: 0 }}
			}});

			// Chart Commandes
			new frappe.Chart("#chart-commandes", {{
				data: {{
					labels: {labels_json},
					datasets: [
						{{ name: "Objectif", values: {format_values(chart_data["order_objective"])}, chartType: "line" }},
						{{ name: "Réalisé", values: {format_values(chart_data["order_realized"])}, chartType: "line" }}
					]
				}},
				type: "axis-mixed",
				height: 200,
				colors: ["#7cd6fd", "#5e64ff"],
				lineOptions: {{ regionFill: 0 }}
			}});

			// Chart Factures
			new frappe.Chart("#chart-factures", {{
				data: {{
					labels: {labels_json},
					datasets: [
						{{ name: "Objectif", values: {format_values(chart_data["invoice_objective"])}, chartType: "line" }},
						{{ name: "Réalisé", values: {format_values(chart_data["invoice_realized"])}, chartType: "line" }}
					]
				}},
				type: "axis-mixed",
				height: 200,
				colors: ["#7cd6fd", "#5e64ff"],
				lineOptions: {{ regionFill: 0 }}
			}});
		}});
	</script>
	"""

	return html

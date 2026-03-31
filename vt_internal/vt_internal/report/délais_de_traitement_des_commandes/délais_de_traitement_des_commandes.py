# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, date_diff
import json


def execute(filters=None):
	# Forcer prepared_report = 0 pour éviter le mode arrière-plan
	frappe.db.set_value('Report', 'Délais de traitement des commandes', 'prepared_report', 0, update_modified=False)

	filters = frappe._dict(filters or {})

	columns = get_columns()
	data = get_data(filters)

	if not data:
		return columns, [], None

	chart_message = generate_chart_html(data)

	return columns, data, chart_message


def get_columns():
	return [
		{"label": _("Projet"), "fieldname": "project_name", "fieldtype": "Data", "width": 220},
		{"label": _("Client"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
		{"label": _("Secteur"), "fieldname": "secteur_vt", "fieldtype": "Link", "options": "Secteur VT", "width": 100},
		{"label": _("Responsable du devis"), "fieldname": "project_manager", "fieldtype": "Link", "options": "User", "width": 160},
		{"label": _("Responsable chantier"), "fieldname": "construction_manager", "fieldtype": "Link", "options": "User", "width": 160},
		{"label": _("Montant cmd HT (€)"), "fieldname": "montant_commande", "fieldtype": "Currency", "width": 130},
		{"label": _("Date commande"), "fieldname": "date_commande", "fieldtype": "Date", "width": 110},
		{"label": _("J. Création→Envoi"), "fieldname": "j_creation_envoi", "fieldtype": "Int", "width": 120},
		{"label": _("J. Devis→Cmd"), "fieldname": "j_devis_commande", "fieldtype": "Int", "width": 110},
		{"label": _("J. Cmd→Réception"), "fieldname": "j_commande_reception", "fieldtype": "Int", "width": 120},
		{"label": _("J. Réception→Fact."), "fieldname": "j_reception_facture", "fieldtype": "Int", "width": 120},
		{"label": _("J. Fact.→Paiement"), "fieldname": "j_facture_paiement", "fieldtype": "Int", "width": 120},
		{"label": _("Total jours"), "fieldname": "j_total", "fieldtype": "Int", "width": 100},
	]


def get_data(filters):
	conditions, params = build_conditions(filters)

	rows = frappe.db.sql(f"""
		SELECT
			p.name AS project,
			p.project_name,
			p.customer,
			p.cost_center,
			p.secteur_vt,
			p.custom_project_manager AS project_manager,
			p.custom_construction_manager AS construction_manager,
			p.company,
			so.name AS sales_order,
			so.transaction_date AS date_commande,
			p.total_sales_amount AS montant_commande,
			q.creation AS date_devis,
			sd.date_envoi_devis AS date_envoi_devis,
			MIN(wcr.le) AS date_reception,
			MIN(CASE WHEN IFNULL(si.is_down_payment_invoice, 0) = 0 THEN si.posting_date END) AS date_facture,
			MAX(pe.reference_date) AS date_paiement
		FROM `tabProject` p
		LEFT JOIN `tabCustomer` cust ON cust.name = p.customer
		LEFT JOIN `tabSales Order` so
			ON so.project = p.name AND so.docstatus = 1
		LEFT JOIN `tabQuotation` q
			ON q.project = p.name
			AND q.docstatus IN (0, 1)
			AND q.transaction_date = (
				SELECT MAX(q2.transaction_date)
				FROM `tabQuotation` q2
				WHERE q2.project = p.name
				  AND q2.docstatus IN (0, 1)
				  AND q2.transaction_date <= so.transaction_date
			)
		LEFT JOIN (
			SELECT parent, MIN(creation) AS date_envoi_devis
			FROM `tabSuivi Devis`
			WHERE parenttype = 'Quotation'
			  AND (statut IS NULL OR statut != 'En attente réponse fournisseur')
			GROUP BY parent
		) sd ON sd.parent = q.name
		LEFT JOIN `tabWork Completion Receipt` wcr
			ON wcr.project = p.name AND wcr.docstatus = 1
		LEFT JOIN `tabSales Invoice` si
			ON si.project = p.name AND si.docstatus = 1
		LEFT JOIN `tabPayment Entry` pe
			ON pe.project = p.name AND pe.docstatus = 1 AND pe.payment_type = 'Receive'
		WHERE p.status = 'Completed'
		{conditions}
		GROUP BY p.name, so.name
		ORDER BY p.name
	""", params, as_dict=True)

	data = []
	for row in rows:
		if not row.date_commande:
			continue

		# Fallback pour j_commande_reception : si pas de réception réelle, utiliser la date facture
		date_reception_ou_facture = row.date_reception or row.date_facture

		# Calcul des durées entre étapes
		j_creation_envoi = safe_date_diff(row.date_envoi_devis, row.date_devis)
		j_devis_commande = safe_date_diff(row.date_commande, row.date_devis)
		j_commande_reception = safe_date_diff(date_reception_ou_facture, row.date_commande)
		# j_reception_facture : uniquement avec la réception réelle (WCR), sinon None pour éviter les 0 artificiels
		j_reception_facture = safe_date_diff(row.date_facture, row.date_reception)
		j_facture_paiement = safe_date_diff(row.date_paiement, row.date_facture)
		j_total = safe_date_diff(row.date_paiement, row.date_devis, allow_negative=False)

		data.append({
			"project": row.project,
			"project_name": row.project_name,
			"customer": row.customer,
			"secteur_vt": row.secteur_vt,
			"project_manager": row.project_manager,
			"construction_manager": row.construction_manager,
			"montant_commande": flt(row.montant_commande),
			"date_devis": row.date_devis,
			"date_envoi_devis": row.date_envoi_devis,
			"date_commande": row.date_commande,
			"date_reception": date_reception_ou_facture,
			"date_facture": row.date_facture,
			"date_paiement": row.date_paiement,
			"j_creation_envoi": j_creation_envoi,
			"j_devis_commande": j_devis_commande,
			"j_commande_reception": j_commande_reception,
			"j_reception_facture": j_reception_facture,
			"j_facture_paiement": j_facture_paiement,
			"j_total": j_total,
		})

	# Tri par j_total décroissant (les plus longs en premier)
	data.sort(key=lambda r: r["j_total"] if r["j_total"] is not None else -1, reverse=True)

	return data


def build_conditions(filters):
	conditions = []
	params = {}

	if filters.get("company"):
		conditions.append("p.company = %(company)s")
		params["company"] = filters.company

	if filters.get("cost_center"):
		conditions.append("p.cost_center = %(cost_center)s")
		params["cost_center"] = filters.cost_center

	if filters.get("secteur_vt"):
		conditions.append("p.secteur_vt = %(secteur_vt)s")
		params["secteur_vt"] = filters.secteur_vt

	if filters.get("project_manager"):
		conditions.append("p.custom_project_manager = %(project_manager)s")
		params["project_manager"] = filters.project_manager

	if filters.get("construction_manager"):
		conditions.append("p.custom_construction_manager = %(construction_manager)s")
		params["construction_manager"] = filters.construction_manager

	if filters.get("customer_group"):
		conditions.append("cust.customer_group = %(customer_group)s")
		params["customer_group"] = filters.customer_group

	if filters.get("project_type"):
		conditions.append("p.project_type = %(project_type)s")
		params["project_type"] = filters.project_type

	if filters.get("from_date"):
		conditions.append("so.transaction_date >= %(from_date)s")
		params["from_date"] = filters.from_date

	if filters.get("to_date"):
		conditions.append("so.transaction_date <= %(to_date)s")
		params["to_date"] = filters.to_date

	cond_str = ("AND " + " AND ".join(conditions)) if conditions else ""
	return cond_str, params


def safe_date_diff(date1, date2, allow_negative=False):
	"""Return date_diff(date1, date2) in days, or None if either date is missing or result is negative."""
	if not date1 or not date2:
		return None
	try:
		result = date_diff(getdate(date1), getdate(date2))
		if not allow_negative and result < 0:
			return None
		return result
	except Exception:
		return None


def generate_chart_html(data):
	"""Generate a pie chart showing average duration per step."""
	steps = [
		("j_creation_envoi", "Création → Envoi devis"),
		("j_devis_commande", "Devis → Commande"),
		("j_commande_reception", "Commande → Réception"),
		("j_reception_facture", "Réception → Facture"),
		("j_facture_paiement", "Facture → Paiement"),
	]

	labels = []
	values = []
	legend_rows = []

	for fieldname, label in steps:
		durations = [r[fieldname] for r in data if r.get(fieldname) is not None and r[fieldname] >= 0]
		avg = round(sum(durations) / len(durations), 1) if durations else 0
		labels.append(label)
		values.append(avg)
		legend_rows.append((label, avg))

	total_avg = round(sum(values), 1)

	labels_json = json.dumps(labels)
	values_json = json.dumps(values)
	colors = ["#28a745", "#5e64ff", "#743ee2", "#ff5858", "#ffa00a"]
	colors_json = json.dumps(colors)

	legend_html = "".join([
		f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">'
		f'<span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:{colors[i]};"></span>'
		f'<span style="font-size:13px; color:#333;">{label}</span>'
		f'<span style="font-size:13px; color:#888; margin-left:auto;"><strong>{avg}j</strong> moy.</span>'
		f'</div>'
		for i, (label, avg) in enumerate(legend_rows)
	])

	html = f"""
	<div style="background: #f9f9f9; border-radius: 8px; padding: 20px; margin-bottom: 20px; display:flex; gap:30px; align-items:center; flex-wrap:wrap;">
		<div style="min-width:280px;">
			<h4 style="margin: 0 0 5px 0; color: #333;">Répartition du délai moyen</h4>
			<p style="margin: 0 0 10px 0; color: #888; font-size: 13px;">Total moyen : <strong>{total_avg} jours</strong> · {len(data)} commande(s)</p>
			<div id="chart-delais" style="margin-top:10px;"></div>
		</div>
		<div style="min-width:220px; flex:1;">
			{legend_html}
		</div>
	</div>

	<script>
		frappe.require('frappe-charts.bundle.js', function() {{
			new frappe.Chart("#chart-delais", {{
				data: {{
					labels: {labels_json},
					datasets: [{{ values: {values_json} }}]
				}},
				type: "pie",
				height: 260,
				colors: {colors_json},
				showLegend: 0,
				tooltipOptions: {{
					formatTooltipY: d => d + ' j (moy.)'
				}}
			}});
		}});
	</script>
	"""

	return html

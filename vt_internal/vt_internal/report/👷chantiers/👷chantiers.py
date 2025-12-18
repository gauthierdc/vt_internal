# Copyright (c) 2025, Verre & Transparence and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from vt_internal.vt_internal.utils.margin_utils import (
	get_theoretical,
	get_project_costs,
	calculate_margin,
	get_project_labour_hours,
)


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
	if filters.get('company'):
		company_filter = filters.get('company')
	else:
		company_filter = None

	# aggregate timesheets by project using SQL to avoid restricted subqueries
	where = ["t.docstatus = 1", "d.project IS NOT NULL"]
	params: list = []
	if company_filter:
		where.append("t.company = %s")
		params.append(company_filter)
	where.append("t.end_date BETWEEN %s AND %s")
	params.extend([start_date, end_date])

	sql = f"""
		SELECT
			d.project AS project,
			SUM(d.costing_amount) AS costing_amount,
			SUM(d.hours) AS hours
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name
		WHERE {' AND '.join(where)}
		GROUP BY d.project
	"""

	tss = frappe.db.sql(sql, tuple(params), as_dict=True)

	# Heures sans projet, groupées par type d'activité (excluant Fabrication et Livraison)
	where_no_project = ["t.docstatus = 1", "(d.project IS NULL OR d.project = '')", "COALESCE(d.activity_type, '') NOT IN ('Fabrication', 'Livraison')"]
	params_no_project: list = []
	if company_filter:
		where_no_project.append("t.company = %s")
		params_no_project.append(company_filter)
	where_no_project.append("t.end_date BETWEEN %s AND %s")
	params_no_project.extend([start_date, end_date])

	sql_no_project = f"""
		SELECT
			COALESCE(d.activity_type, 'Non défini') AS activity_type,
			SUM(d.hours) AS hours
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name
		WHERE {' AND '.join(where_no_project)}
		GROUP BY d.activity_type
		ORDER BY hours DESC
	"""
	hours_by_activity = frappe.db.sql(sql_no_project, tuple(params_no_project), as_dict=True)
	total_hours_no_project = round(sum([(r.get('hours') or 0) for r in hours_by_activity]))

	# Total heures sur chantiers (excluant Fabrication et Livraison) pour calcul du pourcentage
	where_on_project = ["t.docstatus = 1", "d.project IS NOT NULL", "d.project != ''", "COALESCE(d.activity_type, '') NOT IN ('Fabrication', 'Livraison')"]
	params_on_project: list = []
	if company_filter:
		where_on_project.append("t.company = %s")
		params_on_project.append(company_filter)
	where_on_project.append("t.end_date BETWEEN %s AND %s")
	params_on_project.extend([start_date, end_date])

	sql_on_project = f"""
		SELECT SUM(d.hours) AS hours
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name
		WHERE {' AND '.join(where_on_project)}
	"""
	hours_on_project_result = frappe.db.sql(sql_on_project, tuple(params_on_project), as_dict=True)
	total_hours_on_project = round(hours_on_project_result[0].get('hours') or 0) if hours_on_project_result else 0

	# Pourcentage heures chantier
	total_hours_all = total_hours_on_project + total_hours_no_project
	pct_chantier = round(total_hours_on_project / total_hours_all * 100) if total_hours_all > 0 else 0

	columns = [
		"Client::200",
		"Projet::200",
		"CA (HT):Currency:120",
		"Marge %::150",
		"Heures::150",
		"(dont période):Int:80",
		"Type de projet::120",
		"Date de fin:Date:100",
		"Réception::50",
		"Incident::100",
	]

	mydata = []
	total_ca = 0
	
	# Compteurs pour le header
	nb_chantiers_factures_periode = 0  # Chantiers dont statut est Completed
	nb_chantiers_en_cours = 0  # Chantiers dont statut n'est pas Completed
	nb_chantiers_receptionnes = 0  # Chantiers avec une réception
	nb_incidents_qualite = 0  # Total des incidents qualité sur les projets affichés

	# Heures pour chantiers facturés pendant cette période
	hours_factures_periode = 0  # Heures réalisées PENDANT la période
	hours_factures_avant = 0  # Heures réalisées AVANT la période (période précédente)
	total_hours_vendues = 0  # Heures vendues (prévues) pour ces chantiers

	# Heures pour chantiers en cours
	hours_en_cours_periode = 0  # Heures réalisées sur chantiers pas encore facturés

	# Récupérer le CA facturé par projet sur la période
	ca_by_project_sql = """
		SELECT si.project, SUM(si.total) AS ca_total
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1
		  AND si.is_return = 0
		  AND (si.is_down_payment_invoice = 0 OR si.is_down_payment_invoice IS NULL)
		  AND si.project IS NOT NULL
		  AND si.posting_date BETWEEN %s AND %s
	"""
	ca_params = [start_date, end_date]
	if company_filter:
		ca_by_project_sql += " AND si.company = %s"
		ca_params.append(company_filter)
	ca_by_project_sql += " GROUP BY si.project"
	ca_by_project_result = frappe.db.sql(ca_by_project_sql, tuple(ca_params), as_dict=True)
	ca_by_project = {r.project: r.ca_total for r in ca_by_project_result}

	for t in tss:
		project_name = t.get('project')
		p = frappe.db.get_value(
			"Project",
			project_name,
			["status", 'project_type', 'expected_end_date', 'customer', 'total_sales_amount', 'custom_construction_manager'],
			as_dict=True
		)

		if not p:
			continue

		# Filtre uniquement facturé (statut Completed)
		if filters.get('only_completed') and p.status != "Completed":
			continue

		# Filtre par type de projet
		if filters.get('project_type') and p.project_type not in filters.get('project_type'):
			continue

		# Filtre par conducteur de travaux
		if filters.get('construction_manager') and p.custom_construction_manager != filters.get('construction_manager'):
			continue

		# Déterminer si le chantier est facturé (statut Completed)
		is_facture = p.status == "Completed"

		# Calcul des marges
		theo_vente_tp, theo_cost_tp = get_theoretical(project_name, "Temps passé")
		theo_vente_ach, theo_cost_ach = get_theoretical(project_name, "Achats")

		theo_vente = theo_vente_tp + theo_vente_ach
		theo_cost = theo_cost_tp + theo_cost_ach
		theo_margin = calculate_margin(theo_vente, theo_cost)

		# Coûts réels
		costs = get_project_costs(project_name)
		real_cost = costs['total_real_cost']
		real_vente = theo_vente  # Même base de vente
		real_margin = calculate_margin(real_vente, real_cost)

		margin_diff = real_margin - theo_margin

		# Heures
		labour_data = get_project_labour_hours(project_name)
		hours_periode = round(t.get('hours') or 0)  # Heures sur la plage de temps
		hours_expected = round(labour_data['expected_hours'])
		hours_total_project = round(labour_data.get('actual_hours', 0))  # Heures totales du projet
		hours_diff = hours_total_project - hours_expected
		
		# Accumulation selon le type de chantier
		if is_facture:
			nb_chantiers_factures_periode += 1
			hours_factures_periode += hours_periode
			hours_factures_avant += (hours_total_project - hours_periode)
			total_hours_vendues += hours_expected
		else:
			nb_chantiers_en_cours += 1
			hours_en_cours_periode += hours_periode

		# CA (facturé sur la période uniquement)
		ca = round(ca_by_project.get(project_name, 0))
		total_ca += ca

		# Liens
		reception_name = frappe.db.get_value('Work Completion Receipt', {'project': project_name}, ['name'])
		reception_link = reception_name and f"<a href={frappe.utils.get_url_to_form('Work Completion Receipt', reception_name)}>📝</a>" or ""
		if reception_name:
			nb_chantiers_receptionnes += 1

		incident_names = frappe.db.get_all('Quality Incident', filters={'project': project_name}, pluck='name')
		incident_link = ' '.join([f"<a href={frappe.utils.get_url_to_form('Quality Incident', name)}>⚠️</a>" for name in incident_names]) if incident_names else ""
		nb_incidents_qualite += len(incident_names)

		# Date de fin (affichée uniquement si le projet est facturé/Completed)
		date = p.expected_end_date if p.status == "Completed" else ''

		# Formatage couleurs (géré côté JS maintenant)
		margin_diff_int = round(margin_diff)
		hours_diff_int = round(hours_diff)

		# Lien projet avec onclick pour ouvrir la modale
		project_link = f"<a href='#' onclick=\"openProjectDetails('{project_name}'); return false;\">{project_name}</a>"

		# Marge combinée prévu/réel/écart
		marge_prev = round(theo_margin)
		marge_reel = round(real_margin)
		marge_combined = f"{marge_prev}|{marge_reel}|{margin_diff_int}"

		# Heures combinées total/prévu/écart
		heures_combined = f"{hours_total_project}|{hours_expected}|{hours_diff_int}"

		mydata.append([
			p.customer or '',
			project_link,
			ca,
			marge_combined,
			heures_combined,
			hours_periode,
			p.project_type or '',
			date,
			reception_link,
			incident_link,
		])


	# Calcul du CA de la période
	# Récupération des factures qui ne sont pas des acomptes, en docstatus=1,
	# dont le projet a custom_estimated_labor_hours > 1
	ca_periode_where = [
		"si.docstatus = 1",
		"si.is_return = 0",
		"(si.is_down_payment_invoice = 0 OR si.is_down_payment_invoice IS NULL)",
		"p.custom_estimated_labor_hours > 1",
		"p.name IS NOT NULL",
		"si.posting_date BETWEEN %s AND %s"
	]
	ca_periode_params: list = [start_date, end_date]

	# Filtre par société
	if company_filter:
		ca_periode_where.append("si.company = %s")
		ca_periode_params.append(company_filter)

	# Filtre par type de projet
	if filters.get('project_type'):
		project_types = filters.get('project_type')
		if isinstance(project_types, list):
			placeholders = ','.join(['%s'] * len(project_types))
			ca_periode_where.append(f"p.project_type IN ({placeholders})")
			ca_periode_params.extend(project_types)
		else:
			ca_periode_where.append("p.project_type = %s")
			ca_periode_params.append(project_types)

	ca_periode_sql = f"""
		SELECT SUM(si.total) AS ca_total
		FROM `tabSales Invoice` si
		LEFT JOIN `tabProject` p ON p.name = si.project
		WHERE {' AND '.join(ca_periode_where)}
	"""

	ca_periode_result = frappe.db.sql(ca_periode_sql, tuple(ca_periode_params), as_dict=True)
	ca_periode_total = round(ca_periode_result[0].get('ca_total') or 0) if ca_periode_result else 0

	# Heures facturées (somme de custom_labour_hours des factures avec les mêmes filtres)
	heures_facturees_sql = f"""
		SELECT SUM(si.custom_labour_hours) AS heures_total
		FROM `tabSales Invoice` si
		LEFT JOIN `tabProject` p ON p.name = si.project
		WHERE {' AND '.join(ca_periode_where)}
	"""
	heures_facturees_result = frappe.db.sql(heures_facturees_sql, tuple(ca_periode_params), as_dict=True)
	heures_facturees = round(heures_facturees_result[0].get('heures_total') or 0) if heures_facturees_result else 0

	# Heures réalisées (toutes les timesheets validées, hors Fabrication et Livraison)
	where_heures_realisees = [
		"t.docstatus = 1",
		"COALESCE(d.activity_type, '') NOT IN ('Fabrication', 'Livraison')"
	]
	params_heures_realisees: list = []
	if company_filter:
		where_heures_realisees.append("t.company = %s")
		params_heures_realisees.append(company_filter)
	where_heures_realisees.append("t.end_date BETWEEN %s AND %s")
	params_heures_realisees.extend([start_date, end_date])

	sql_heures_realisees = f"""
		SELECT SUM(d.hours) AS hours
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name
		WHERE {' AND '.join(where_heures_realisees)}
	"""
	heures_realisees_result = frappe.db.sql(sql_heures_realisees, tuple(params_heures_realisees), as_dict=True)
	heures_realisees = round(heures_realisees_result[0].get('hours') or 0) if heures_realisees_result else 0

	# Calcul du pourcentage heures facturées / réalisées
	pct_heures = round(heures_facturees / heures_realisees * 100) if heures_realisees > 0 else 0
	pct_heures_color = "#2e7d32" if pct_heures >= 90 else "#c62828"

	# Génération du HTML pour les heures par activité (hors projet)
	activity_items_html = ''.join([
		f'<div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #eee;">'
		f'<span style="font-size: 12px; color: #333;">{a.get("activity_type") or "Non défini"}</span>'
		f'<span style="font-size: 12px; font-weight: bold; color: #1976d2;">{round(a.get("hours") or 0)} h</span>'
		f'</div>'
		for a in hours_by_activity
	])

	# Couleur du pourcentage chantier (vert si >= 70%, orange sinon)
	pct_color = "#2e7d32" if pct_chantier >= 70 else "#f57c00"

	# Format abrégé du CA (M pour millions, k pour milliers)
	if ca_periode_total >= 1000000:
		ca_display = f"{round(ca_periode_total / 1000000)}M"
	elif ca_periode_total >= 1000:
		ca_display = f"{round(ca_periode_total / 1000)}k"
	else:
		ca_display = str(ca_periode_total)

	# Message en haut avec les statistiques
	message = f"""
	<div style="display: flex; gap: 20px; margin-bottom: 15px; flex-wrap: wrap;">
		<!-- Bloc CA de la période -->
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 150px; text-align: center;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">CA période</div>
			<div style="font-size: 36px; font-weight: bold; color: #1976d2;">{ca_display} €</div>
			<div style="font-size: 10px; color: #999;">Factures validées</div>
		</div>

		<!-- Bloc Heures réalisées / facturées -->
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 150px; text-align: center;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">Heures facturées / réalisées</div>
			<div style="font-size: 36px; font-weight: bold; color: {pct_heures_color};">{pct_heures}%</div>
			<div style="font-size: 10px; color: #999;">{heures_facturees}h / {heures_realisees}h</div>
		</div>

		<!-- Bloc % Chantier -->
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 120px; text-align: center;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">% Chantier</div>
			<div style="font-size: 36px; font-weight: bold; color: {pct_color};">{pct_chantier}%</div>
			<div style="font-size: 10px; color: #999;">{total_hours_on_project}h / {total_hours_all}h</div>
		</div>

		<!-- Bloc Chantiers -->
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 250px;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">Chantiers période</div>
			<div style="display: flex; gap: 20px;">
				<div>
					<div style="font-size: 24px; font-weight: bold; color: #2e7d32;">{nb_chantiers_factures_periode}</div>
					<div style="font-size: 11px; color: #666;">facturés</div>
				</div>
				<div>
					<div style="font-size: 24px; font-weight: bold; color: #f57c00;">{nb_chantiers_en_cours}</div>
					<div style="font-size: 11px; color: #666;">en cours</div>
				</div>
				<div>
					<div style="font-size: 24px; font-weight: bold; color: #1976d2;">{nb_chantiers_receptionnes}</div>
					<div style="font-size: 11px; color: #666;">réceptionnés</div>
				</div>
			</div>
		</div>

		<!-- Bloc Heures hors chantiers -->
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 200px;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">Heures hors chantiers <span style="font-weight: bold;">({total_hours_no_project} h)</span></div>
			<div style="max-height: 120px; overflow-y: auto;">
				{activity_items_html if activity_items_html else '<div style="font-size: 12px; color: #999;">Aucune</div>'}
			</div>
		</div>

		<!-- Bloc Incidents Qualité -->
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 150px;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">Incidents qualité</div>
			<div>
				<div style="font-size: 24px; font-weight: bold; color: {'#c62828' if nb_incidents_qualite > 0 else '#2e7d32'};">{nb_incidents_qualite}</div>
				<div style="font-size: 11px; color: #666;">sur les projets</div>
			</div>
		</div>
	</div>
	"""

	return columns, mydata, message


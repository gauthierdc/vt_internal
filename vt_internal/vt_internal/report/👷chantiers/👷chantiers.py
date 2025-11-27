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
	where = ["t.docstatus != 2", "d.project IS NOT NULL"]
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

	# Frais généraux (not project)
	where_not = ["t.docstatus != 2"]
	params_not: list = []
	if company_filter:
		where_not.append("t.company = %s")
		params_not.append(company_filter)
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

	sql_at = f"""
		SELECT SUM(d.hours) AS hours
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name
		WHERE {' AND '.join(where_not)} AND d.activity_type = %s
	"""
	at_rows = frappe.db.sql(sql_at, tuple([*params_not, 'Atelier']), as_dict=True)
	at_hours = round(sum([(r.get('hours') or 0) for r in at_rows]))

	frais_generaux_hours = at_hours + vt_hours

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
		"Incident::50",
	]

	mydata = []
	total_ca = 0
	
	# Compteurs pour le header
	nb_chantiers_factures_periode = 0  # Chantiers dont date de fin est dans la période
	nb_chantiers_en_cours = 0  # Chantiers dont date de fin n'est pas dans la période
	
	# Heures pour chantiers facturés pendant cette période
	hours_factures_periode = 0  # Heures réalisées PENDANT la période
	hours_factures_avant = 0  # Heures réalisées AVANT la période (période précédente)
	total_hours_vendues = 0  # Heures vendues (prévues) pour ces chantiers
	
	# Heures pour chantiers en cours
	hours_en_cours_periode = 0  # Heures réalisées sur chantiers pas encore facturés

	for t in tss:
		project_name = t.get('project')
		p = frappe.db.get_value(
			"Project",
			project_name,
			["status", 'project_type', 'expected_end_date', 'customer', 'total_sales_amount'],
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

		# Déterminer si le chantier est facturé PENDANT cette période
		# (date de fin comprise entre start_date et end_date)
		is_facture_periode = (
			p.status == "Completed" 
			and p.expected_end_date 
			and p.expected_end_date >= frappe.utils.getdate(start_date)
			and p.expected_end_date <= frappe.utils.getdate(end_date)
		)

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
		if is_facture_periode:
			nb_chantiers_factures_periode += 1
			hours_factures_periode += hours_periode
			hours_factures_avant += (hours_total_project - hours_periode)
			total_hours_vendues += hours_expected
		else:
			nb_chantiers_en_cours += 1
			hours_en_cours_periode += hours_periode

		# CA
		ca = round(theo_vente or p.total_sales_amount or 0)
		total_ca += ca

		# Liens
		reception_name = frappe.db.get_value('Work Completion Receipt', {'project': project_name}, ['name'])
		reception_link = reception_name and f"<a href={frappe.utils.get_url_to_form('Work Completion Receipt', reception_name)}>📝</a>" or ""

		incident_name = frappe.db.get_value('Quality Incident', {'project': project_name}, ['name'])
		incident_link = incident_name and f"<a href={frappe.utils.get_url_to_form('Quality Incident', incident_name)}>⚠️</a>" or ""

		# Date de fin
		date = p.expected_end_date or ''

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

	# Total heures chantiers sur la période
	ch_hours = hours_factures_periode + hours_en_cours_periode

	# Calcul du pourcentage chantier après filtrage
	total_hours = max(1, frais_generaux_hours + ch_hours)
	pct_chantier = round(ch_hours / total_hours * 100)

	# Pourcentage heures = (heures chantiers + frais généraux) / heures vendues
	total_heures_realisees = ch_hours + frais_generaux_hours
	pct_heures = round(total_heures_realisees / max(1, total_hours_vendues) * 100) if total_hours_vendues else 0
	pct_color = "#2e7d32" if pct_heures <= 100 else "#c62828"

	# Message en haut avec les statistiques
	message = f"""
	<div style="display: flex; gap: 20px; margin-bottom: 15px; flex-wrap: wrap;">
		<!-- Bloc Chantiers -->
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 200px;">
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
			</div>
		</div>

		<!-- Bloc Calcul Rentabilité -->
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; flex-grow: 1;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">Rentabilité période</div>
			<div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
				<div style="text-align: center; padding: 8px 12px; background: #e3f2fd; border-radius: 6px;">
					<div style="font-size: 18px; font-weight: bold;">{ch_hours} h</div>
					<div style="font-size: 10px; color: #666;">chantiers</div>
				</div>
				<span style="font-size: 20px; color: #666;">+</span>
				<div style="text-align: center; padding: 8px 12px; background: #fff3e0; border-radius: 6px;">
					<div style="font-size: 18px; font-weight: bold;">{frais_generaux_hours} h</div>
					<div style="font-size: 10px; color: #666;">frais gén. <span style="color:#999">(VT {vt_hours} + At {at_hours})</span></div>
				</div>
				<span style="font-size: 20px; color: #666;">÷</span>
				<div style="text-align: center; padding: 8px 12px; background: #e8f5e9; border-radius: 6px;">
					<div style="font-size: 18px; font-weight: bold;">{total_hours_vendues} h</div>
					<div style="font-size: 10px; color: #666;">facturées</div>
				</div>
				<span style="font-size: 20px; color: #666;">=</span>
				<div style="text-align: center; padding: 10px 15px; background: {pct_color}; border-radius: 6px; color: white;">
					<div style="font-size: 22px; font-weight: bold;">{pct_heures}%</div>
				</div>
			</div>
		</div>

		<!-- Bloc Report -->
		<div style="background: #f5f5f5; border-radius: 8px; padding: 15px; min-width: 200px;">
			<div style="font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px;">Report</div>
			<div style="display: flex; gap: 20px;">
				<div>
					<div style="font-size: 24px; font-weight: bold; color: #7b1fa2;">{hours_factures_avant} h</div>
					<div style="font-size: 11px; color: #666;">période précéd.</div>
				</div>
				<div>
					<div style="font-size: 24px; font-weight: bold; color: #1976d2;">{hours_en_cours_periode} h</div>
					<div style="font-size: 11px; color: #666;">période suiv.</div>
				</div>
			</div>
		</div>
	</div>
	"""

	return columns, mydata, message


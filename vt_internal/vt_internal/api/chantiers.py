# Copyright (c) 2025, Verre & Transparence and contributors
# For license information, please see license.txt
#
# API JSON de la vue "Chantiers" (page Desk /app/chantiers).
#
# À la différence du Script Report `👷Chantiers` (qui renvoie du HTML figé),
# on renvoie ici des données structurées : le front Vue rend tout et devient
# interactif (tri, recherche, graphes, drawer…).
#
# Objectif métier : sur une période X→Y, tout comprendre de ses chantiers —
# est-il facturé ? combien d'heures passées (validées ET en attente) ? a-t-on
# repointé sur un chantier déjà facturé (SAV) ? quels chantiers actifs n'ont
# reçu aucun pointage ?

import json

import frappe

from vt_internal.vt_internal.utils.margin_utils import calculate_margin

# Types d'activité exclus du "temps chantier" (temps atelier / logistique).
EXCLUDED_ACTIVITIES = ("Fabrication", "Livraison")


def _parse_list(value):
	"""Normalise un filtre multi-valeurs (liste, JSON string, ou None)."""
	if not value:
		return []
	if isinstance(value, str):
		try:
			value = json.loads(value)
		except (ValueError, TypeError):
			value = [value]
	return [v for v in value if v]


def _company_clause(company, alias="t"):
	"""(fragment_sql, params) pour filtrer sur la société."""
	if company:
		return f" AND {alias}.company = %s", [company]
	return "", []


def _cm_clause(cm_list):
	"""(fragment_sql, params) pour filtrer sur les conducteurs de travaux.

	Suppose qu'un alias `p` (tabProject) est disponible dans la requête."""
	if cm_list:
		ph = ",".join(["%s"] * len(cm_list))
		return f" AND p.custom_construction_manager IN ({ph})", list(cm_list)
	return "", []


def _scalar_kpis(start_date, end_date, company, cm_list):
	"""KPIs scalaires pour une période — réutilisé pour la période courante ET
	la période précédente (comparaison). Ne dépend pas de la boucle projets.

	Si des conducteurs sont sélectionnés, on joint systématiquement `tabProject`
	et on restreint aux chantiers de ces conducteurs (les heures hors chantier
	disparaissent alors naturellement du périmètre)."""

	comp_t, comp_pt = _company_clause(company, "t")
	comp_si, comp_psi = _company_clause(company, "si")
	cm_sql, cm_p = _cm_clause(cm_list)
	# Jointure projet nécessaire pour les requêtes timesheet qui ne l'ont pas.
	cm_join = " JOIN `tabProject` p ON p.name = d.project" if cm_list else ""
	excl = ",".join(["%s"] * len(EXCLUDED_ACTIVITIES))

	# Heures réalisées (validées) et non validées (brouillon), hors Fab/Livraison
	val = frappe.db.sql(
		f"""
		SELECT
			SUM(CASE WHEN t.docstatus = 1 THEN d.hours ELSE 0 END) AS h_val,
			SUM(CASE WHEN t.docstatus = 0 THEN d.hours ELSE 0 END) AS h_draft
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name{cm_join}
		WHERE t.docstatus IN (0, 1)
		  AND COALESCE(d.activity_type, '') NOT IN ({excl})
		  AND t.end_date BETWEEN %s AND %s{comp_t}{cm_sql}
		""",
		tuple([*EXCLUDED_ACTIVITIES, start_date, end_date, *comp_pt, *cm_p]),
		as_dict=True,
	)[0]
	heures_realisees = round(val.h_val or 0)
	heures_non_validees = round(val.h_draft or 0)

	# Heures sur chantier vs hors chantier (validées)
	on_off = frappe.db.sql(
		f"""
		SELECT
			SUM(CASE WHEN d.project IS NOT NULL AND d.project != '' THEN d.hours ELSE 0 END) AS h_on,
			SUM(CASE WHEN d.project IS NULL OR d.project = '' THEN d.hours ELSE 0 END) AS h_off
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name{cm_join}
		WHERE t.docstatus = 1
		  AND COALESCE(d.activity_type, '') NOT IN ({excl})
		  AND t.end_date BETWEEN %s AND %s{comp_t}{cm_sql}
		""",
		tuple([*EXCLUDED_ACTIVITIES, start_date, end_date, *comp_pt, *cm_p]),
		as_dict=True,
	)[0]
	h_on = round(on_off.h_on or 0)
	h_off = round(on_off.h_off or 0)
	pct_chantier = round(h_on / (h_on + h_off) * 100) if (h_on + h_off) > 0 else 0

	# Heures SAV : heures (validées) sur des chantiers DÉJÀ facturés (Completed)
	sav = frappe.db.sql(
		f"""
		SELECT SUM(d.hours) AS h
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name
		JOIN `tabProject` p ON p.name = d.project
		WHERE t.docstatus = 1
		  AND p.status = 'Completed'
		  AND COALESCE(d.activity_type, '') NOT IN ({excl})
		  AND t.end_date BETWEEN %s AND %s{comp_t}{cm_sql}
		""",
		tuple([*EXCLUDED_ACTIVITIES, start_date, end_date, *comp_pt, *cm_p]),
		as_dict=True,
	)[0]
	heures_sav = round(sav.h or 0)

	# CA de la période (factures non-acompte, projets "chantiers" réels)
	ca = frappe.db.sql(
		f"""
		SELECT SUM(si.total) AS ca, SUM(si.custom_labour_hours) AS heures_facturees
		FROM `tabSales Invoice` si
		JOIN `tabProject` p ON p.name = si.project
		WHERE si.docstatus = 1 AND si.is_return = 0
		  AND (si.is_down_payment_invoice = 0 OR si.is_down_payment_invoice IS NULL)
		  AND p.custom_estimated_labor_hours > 1
		  AND si.posting_date BETWEEN %s AND %s{comp_si}{cm_sql}
		""",
		tuple([start_date, end_date, *comp_psi, *cm_p]),
		as_dict=True,
	)[0]
	ca_periode = round(ca.ca or 0)
	heures_facturees = round(ca.heures_facturees or 0)
	pct_heures = round(heures_facturees / heures_realisees * 100) if heures_realisees > 0 else 0

	# Nb de chantiers distincts pointés (validé ou brouillon) sur la période
	nb = frappe.db.sql(
		f"""
		SELECT COUNT(DISTINCT d.project) AS nb
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name{cm_join}
		WHERE t.docstatus IN (0, 1)
		  AND d.project IS NOT NULL AND d.project != ''
		  AND t.end_date BETWEEN %s AND %s{comp_t}{cm_sql}
		""",
		tuple([start_date, end_date, *comp_pt, *cm_p]),
		as_dict=True,
	)[0]

	# Montant commandé en commandes fournisseur sur la période (lignes liées à un projet)
	comp_po = " AND po.company = %s" if company else ""
	comp_po_p = [company] if company else []
	po_join = " JOIN `tabProject` p ON p.name = poi.project" if cm_list else ""
	po = frappe.db.sql(
		f"""
		SELECT SUM(poi.amount) AS montant
		FROM `tabPurchase Order Item` poi
		JOIN `tabPurchase Order` po ON po.name = poi.parent{po_join}
		WHERE po.docstatus < 2
		  AND poi.project IS NOT NULL AND poi.project != ''
		  AND po.transaction_date BETWEEN %s AND %s{comp_po}{cm_sql}
		""",
		tuple([start_date, end_date, *comp_po_p, *cm_p]),
		as_dict=True,
	)[0]

	# Dépenses sur la période (notes de frais rattachées à un chantier)
	comp_exp = " AND e.company = %s" if company else ""
	comp_exp_p = [company] if company else []
	exp_join = " JOIN `tabProject` p ON p.name = e.project" if cm_list else ""
	exp = frappe.db.sql(
		f"""
		SELECT SUM(e.net_amount) AS montant
		FROM `tabExpense` e{exp_join}
		WHERE e.docstatus < 2
		  AND e.project IS NOT NULL AND e.project != ''
		  AND e.expense_date BETWEEN %s AND %s{comp_exp}{cm_sql}
		""",
		tuple([start_date, end_date, *comp_exp_p, *cm_p]),
		as_dict=True,
	)[0]

	# Fabrication VT créée sur la période (hors annulées)
	comp_fab = " AND f.company = %s" if company else ""
	comp_fab_p = [company] if company else []
	fab_join = " JOIN `tabProject` p ON p.name = f.project" if cm_list else ""
	fab = frappe.db.sql(
		f"""
		SELECT SUM(f.manufacturing_costs) AS montant
		FROM `tabFabrication VT` f{fab_join}
		WHERE f.status != 'Annulé'
		  AND f.project IS NOT NULL AND f.project != ''
		  AND DATE(f.creation) BETWEEN %s AND %s{comp_fab}{cm_sql}
		""",
		tuple([start_date, end_date, *comp_fab_p, *cm_p]),
		as_dict=True,
	)[0]

	return {
		"ca_periode": ca_periode,
		"commande_fournisseur": round(po.montant or 0),
		"depenses": round(exp.montant or 0),
		"fabrication": round(fab.montant or 0),
		"heures_facturees": heures_facturees,
		"heures_realisees": heures_realisees,
		"heures_non_validees": heures_non_validees,
		"pct_heures": pct_heures,
		"heures_chantier": h_on,
		"heures_hors_chantier": h_off,
		"pct_chantier": pct_chantier,
		"heures_sav": heures_sav,
		"nb_chantiers_pointes": nb.nb or 0,
	}


@frappe.whitelist()
def get_chantiers(start_date=None, end_date=None, company=None, conducteurs=None):
	"""Point d'entrée principal de la vue Chantiers.

	Renvoie période, KPIs (+ comparaison période précédente), lignes projet
	enrichies, chantiers sans pointage, répartitions (activité, conducteur) et
	séries hebdomadaires. `conducteurs` = liste de User (multi-sélection)."""

	end_date = end_date or frappe.utils.nowdate()
	start_date = start_date or frappe.utils.add_to_date(end_date, days=-7)
	cm_list = _parse_list(conducteurs)

	# Période précédente de même longueur, juste avant.
	length = frappe.utils.date_diff(end_date, start_date)
	prev_end = frappe.utils.add_to_date(start_date, days=-1)
	prev_start = frappe.utils.add_to_date(prev_end, days=-length)

	kpis = _scalar_kpis(start_date, end_date, company, cm_list)
	kpis_prev = _scalar_kpis(prev_start, prev_end, company, cm_list)

	comp_t, comp_pt = _company_clause(company, "t")
	comp_si, comp_psi = _company_clause(company, "si")
	cm_sql, cm_p = _cm_clause(cm_list)
	cm_join = " JOIN `tabProject` p ON p.name = d.project" if cm_list else ""
	excl = ",".join(["%s"] * len(EXCLUDED_ACTIVITIES))

	# --- Heures par projet sur la période (validées + brouillon) ---------------
	rows = frappe.db.sql(
		f"""
		SELECT d.project AS project,
			SUM(CASE WHEN t.docstatus = 1 THEN d.hours ELSE 0 END) AS h_val,
			SUM(CASE WHEN t.docstatus = 0 THEN d.hours ELSE 0 END) AS h_draft
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name{cm_join}
		WHERE t.docstatus IN (0, 1)
		  AND d.project IS NOT NULL AND d.project != ''
		  AND t.end_date BETWEEN %s AND %s{comp_t}{cm_sql}
		GROUP BY d.project
		""",
		tuple([start_date, end_date, *comp_pt, *cm_p]),
		as_dict=True,
	)
	hours_map = {r.project: r for r in rows}

	# --- Commandes fournisseur passées sur la période (par projet) -------------
	# Créer une commande fournisseur sur la période fait aussi "entrer" le
	# chantier dans la période (même sans pointage).
	comp_po = " AND po.company = %s" if company else ""
	comp_po_p = [company] if company else []
	po_cm_join = " JOIN `tabProject` p ON p.name = poi.project" if cm_list else ""
	po_rows = frappe.db.sql(
		f"""
		SELECT poi.project AS project, SUM(poi.amount) AS montant
		FROM `tabPurchase Order Item` poi
		JOIN `tabPurchase Order` po ON po.name = poi.parent{po_cm_join}
		WHERE po.docstatus < 2
		  AND poi.project IS NOT NULL AND poi.project != ''
		  AND po.transaction_date BETWEEN %s AND %s{comp_po}{cm_sql}
		GROUP BY poi.project
		""",
		tuple([start_date, end_date, *comp_po_p, *cm_p]),
		as_dict=True,
	)
	po_map = {r.project: round(r.montant or 0) for r in po_rows}

	# --- Dépenses par projet sur la période -----------------------------------
	comp_exp = " AND e.company = %s" if company else ""
	comp_exp_p = [company] if company else []
	exp_cm_join = " JOIN `tabProject` p ON p.name = e.project" if cm_list else ""
	exp_rows = frappe.db.sql(
		f"""
		SELECT e.project AS project, SUM(e.net_amount) AS montant
		FROM `tabExpense` e{exp_cm_join}
		WHERE e.docstatus < 2
		  AND e.project IS NOT NULL AND e.project != ''
		  AND e.expense_date BETWEEN %s AND %s{comp_exp}{cm_sql}
		GROUP BY e.project
		""",
		tuple([start_date, end_date, *comp_exp_p, *cm_p]),
		as_dict=True,
	)
	exp_map = {r.project: round(r.montant or 0) for r in exp_rows}

	# --- Fabrication VT par projet sur la période -----------------------------
	comp_fab = " AND f.company = %s" if company else ""
	comp_fab_p = [company] if company else []
	fab_cm_join = " JOIN `tabProject` p ON p.name = f.project" if cm_list else ""
	fab_rows = frappe.db.sql(
		f"""
		SELECT f.project AS project, SUM(f.manufacturing_costs) AS montant
		FROM `tabFabrication VT` f{fab_cm_join}
		WHERE f.status != 'Annulé'
		  AND f.project IS NOT NULL AND f.project != ''
		  AND DATE(f.creation) BETWEEN %s AND %s{comp_fab}{cm_sql}
		GROUP BY f.project
		""",
		tuple([start_date, end_date, *comp_fab_p, *cm_p]),
		as_dict=True,
	)
	fab_map = {r.project: round(r.montant or 0) for r in fab_rows}

	# --- CA facturé par projet sur la période ---------------------------------
	si_cm_join = " JOIN `tabProject` p ON p.name = si.project" if cm_list else ""
	ca_period_rows = frappe.db.sql(
		f"""
		SELECT si.project AS project, SUM(si.total) AS ca
		FROM `tabSales Invoice` si{si_cm_join}
		WHERE si.docstatus = 1 AND si.is_return = 0
		  AND (si.is_down_payment_invoice = 0 OR si.is_down_payment_invoice IS NULL)
		  AND si.project IS NOT NULL AND si.project != ''
		  AND si.posting_date BETWEEN %s AND %s{comp_si}{cm_sql}
		GROUP BY si.project
		""",
		tuple([start_date, end_date, *comp_psi, *cm_p]),
		as_dict=True,
	)
	ca_map = {r.project: round(r.ca or 0) for r in ca_period_rows}

	# Chantiers de la période : il s'est passé QUELQUE CHOSE dessus, c.-à-d.
	# pointage OU facturation OU commande fournisseur OU dépense OU fabrication.
	project_names = list(dict.fromkeys(
		[r.project for r in rows]
		+ list(ca_map.keys()) + list(po_map.keys()) + list(exp_map.keys()) + list(fab_map.keys())
	))

	# --- Batchs (une requête pour tous les projets listés) ---------------------
	ca_period_map = ca_map  # déjà calculé ci-dessus (sert aussi à l'inclusion)
	billed_all_map, last_activity_map = {}, {}
	reception_map, incident_map = {}, {}
	meta_map, theo_map = {}, {}
	po_all_map, fab_all_map, expected_map, actual_map, so_total_map = {}, {}, {}, {}, {}
	if project_names:
		ph = ",".join(["%s"] * len(project_names))

		for r in frappe.db.sql(
			f"""
			SELECT si.project, SUM(si.total) AS ca
			FROM `tabSales Invoice` si
			WHERE si.docstatus = 1 AND si.is_return = 0
			  AND (si.is_down_payment_invoice = 0 OR si.is_down_payment_invoice IS NULL)
			  AND si.project IN ({ph})
			GROUP BY si.project
			""",
			tuple(project_names),
			as_dict=True,
		):
			billed_all_map[r.project] = round(r.ca or 0)

		for r in frappe.db.sql(
			f"""
			SELECT d.project, MAX(t.end_date) AS last_date
			FROM `tabTimesheet` t
			JOIN `tabTimesheet Detail` d ON d.parent = t.name
			WHERE t.docstatus IN (0, 1) AND d.project IN ({ph})
			GROUP BY d.project
			""",
			tuple(project_names),
			as_dict=True,
		):
			last_activity_map[r.project] = r.last_date

		for r in frappe.db.get_all(
			"Work Completion Receipt",
			filters={"project": ["in", project_names]},
			fields=["project", "name"],
		):
			reception_map.setdefault(r.project, []).append(r.name)

		for r in frappe.db.get_all(
			"Quality Incident",
			filters={"project": ["in", project_names]},
			fields=["project", "name", "status"],
		):
			incident_map.setdefault(r.project, []).append(r)

		# Métadonnées projet (remplace un get_value par projet)
		for r in frappe.db.sql(
			f"""
			SELECT name, status, project_type, expected_end_date, customer,
			       total_sales_amount, custom_construction_manager, custom_project_manager,
			       total_costing_amount, total_consumed_material_cost, total_expense_claim
			FROM `tabProject` WHERE name IN ({ph})
			""",
			tuple(project_names), as_dict=True,
		):
			meta_map[r.name] = r

		# Ventes/coûts théoriques par projet (Sales Order Items + Packed Items) —
		# remplace get_theoretical. Somme sur tous les axes (= marge globale).
		def _accum_theo(sql_rows):
			for r in sql_rows:
				e = theo_map.setdefault(r.project, {"vente": 0.0, "cost": 0.0})
				e["vente"] += (r.vente or 0)
				e["cost"] += (r.cost or 0)
		_accum_theo(frappe.db.sql(
			f"""
			SELECT so.project AS project, SUM(soi.amount) AS vente,
			       SUM(soi.qty * COALESCE(soi.base_unit_cost_price, 0)) AS cost
			FROM `tabSales Order Item` soi
			JOIN `tabSales Order` so ON so.name = soi.parent
			WHERE so.project IN ({ph}) AND so.docstatus = 1
			  AND so.custom_exclude_from_statistics != 1
			  AND COALESCE(soi.product_bundle_name, '') = ''
			GROUP BY so.project
			""", tuple(project_names), as_dict=True))
		_accum_theo(frappe.db.sql(
			f"""
			SELECT so.project AS project, SUM(pi.qty * pi.rate) AS vente,
			       SUM(pi.qty * COALESCE(pi.base_unit_cost_price, 0)) AS cost
			FROM `tabPacked Item` pi
			JOIN `tabSales Order` so ON so.name = pi.parent AND pi.parenttype = 'Sales Order'
			WHERE so.project IN ({ph}) AND so.docstatus = 1
			  AND so.custom_exclude_from_statistics != 1
			GROUP BY so.project
			""", tuple(project_names), as_dict=True))

		# Coûts réels : commandes fournisseur + fabrications (tout l'historique)
		for r in frappe.db.sql(
			f"""
			SELECT poi.project AS project, SUM(poi.amount) AS total
			FROM `tabPurchase Order Item` poi
			JOIN `tabPurchase Order` po ON po.name = poi.parent
			WHERE poi.project IN ({ph}) AND po.docstatus < 2
			GROUP BY poi.project
			""", tuple(project_names), as_dict=True):
			po_all_map[r.project] = r.total or 0
		for r in frappe.db.sql(
			f"""
			SELECT project, SUM(manufacturing_costs) AS total
			FROM `tabFabrication VT`
			WHERE project IN ({ph}) AND docstatus < 2
			GROUP BY project
			""", tuple(project_names), as_dict=True):
			fab_all_map[r.project] = r.total or 0

		# Heures prévues (Sales Order) et réalisées (Timesheet) — remplace
		# get_project_labour_hours.
		for r in frappe.db.sql(
			f"""
			SELECT project, SUM(custom_labour_hours) AS h, SUM(total) AS montant
			FROM `tabSales Order`
			WHERE project IN ({ph}) AND docstatus = 1 AND custom_exclude_from_statistics != 1
			GROUP BY project
			""", tuple(project_names), as_dict=True):
			expected_map[r.project] = r.h or 0
			so_total_map[r.project] = round(r.montant or 0)
		for r in frappe.db.sql(
			f"""
			SELECT d.project AS project, SUM(d.hours) AS h
			FROM `tabTimesheet Detail` d
			JOIN `tabTimesheet` t ON t.name = d.parent
			WHERE d.project IN ({ph}) AND t.docstatus != 2
			GROUP BY d.project
			""", tuple(project_names), as_dict=True):
			actual_map[r.project] = r.h or 0

	# --- Construction des lignes projet ---------------------------------------
	projects = []
	cm_users = set()
	for name in project_names:
		p = meta_map.get(name)
		if not p:
			continue

		is_facture = p.status == "Completed"

		# Marges (données pré-agrégées en batch)
		theo = theo_map.get(name, {})
		theo_vente = theo.get("vente", 0)
		theo_cost = theo.get("cost", 0)
		theo_margin = calculate_margin(theo_vente, theo_cost)
		real_cost = (
			(p.total_costing_amount or 0)
			+ po_all_map.get(name, 0)
			+ (p.total_consumed_material_cost or 0)
			+ (p.total_expense_claim or 0)
			+ fab_all_map.get(name, 0)
		)
		real_margin = calculate_margin(theo_vente, real_cost)

		hm = hours_map.get(name)
		h_val = round(hm.h_val or 0) if hm else 0
		h_draft = round(hm.h_draft or 0) if hm else 0
		hours_expected = round(expected_map.get(name, 0))
		hours_total = round(actual_map.get(name, 0))

		# Montant total du projet = somme des commandes client (Sales Orders),
		# avec repli sur total_sales_amount si aucune commande.
		total_sold = so_total_map.get(name, 0) or round(p.total_sales_amount or 0)
		billed_all = billed_all_map.get(name, 0)
		pct_facture = round(billed_all / total_sold * 100) if total_sold > 0 else 0
		reste_a_facturer = max(0, total_sold - billed_all)

		retard = 0
		if p.expected_end_date and not is_facture:
			retard = frappe.utils.date_diff(frappe.utils.nowdate(), p.expected_end_date)
			retard = retard if retard > 0 else 0

		incidents = incident_map.get(name, [])
		if p.custom_construction_manager:
			cm_users.add(p.custom_construction_manager)
		if p.custom_project_manager:
			cm_users.add(p.custom_project_manager)

		projects.append({
			"project": name,
			"client": p.customer or "",
			"status": p.status,
			"is_facture": is_facture,
			"is_sav": is_facture and (h_val + h_draft) > 0,
			"type_projet": p.project_type or "",
			"ca_periode": ca_period_map.get(name, 0),
			"po_periode": po_map.get(name, 0),
			"depense_periode": exp_map.get(name, 0),
			"fab_periode": fab_map.get(name, 0),
			"marge_theo": round(theo_margin),
			"marge_reel": round(real_margin),
			"marge_diff": round(real_margin - theo_margin),
			"heures_val": h_val,
			"heures_draft": h_draft,
			"heures_total": hours_total,
			"heures_expected": hours_expected,
			"heures_diff": hours_total - hours_expected,
			"total_sold": total_sold,
			"billed_all": billed_all,
			"pct_facture": pct_facture,
			"reste_a_facturer": reste_a_facturer,
			"expected_end_date": p.expected_end_date,
			"retard": retard,
			"derniere_activite": last_activity_map.get(name),
			"conducteur": p.custom_construction_manager or "",
			"responsable": p.custom_project_manager or "",
			"nb_receptions": len(reception_map.get(name, [])),
			"nb_incidents": len(incidents),
			"nb_incidents_ouverts": sum(1 for i in incidents if i.get("status") not in ("Closed", "Resolved", "Fermé")),
		})

	# --- Chantiers "décrochés" -------------------------------------------------
	# Chantiers actifs qui étaient pointés la période PRÉCÉDENTE mais sur lesquels
	# plus aucune heure n'a été pointée pendant la période courante. C'est le
	# signal actionnable ("on a arrêté de pointer dessus"), et non la liste de
	# tous les projets ouverts (bien trop nombreuse pour être pertinente).
	prev_pointed = frappe.db.sql(
		f"""
		SELECT DISTINCT d.project
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name{cm_join}
		WHERE t.docstatus IN (0, 1)
		  AND d.project IS NOT NULL AND d.project != ''
		  AND t.end_date BETWEEN %s AND %s{comp_t}{cm_sql}
		""",
		tuple([prev_start, prev_end, *comp_pt, *cm_p]),
		pluck="project",
	)
	current_set = set(project_names)
	candidates = [pr for pr in prev_pointed if pr not in current_set]
	sans_pointage = []
	if candidates:
		ph = ",".join(["%s"] * len(candidates))
		sans_pointage = frappe.db.sql(
			f"""
			SELECT p.name AS project, p.customer, p.status, p.project_type,
			       p.expected_end_date, p.custom_construction_manager AS conducteur
			FROM `tabProject` p
			WHERE p.name IN ({ph})
			  AND p.status NOT IN ('Completed', 'Cancelled')
			  AND p.custom_estimated_labor_hours > 1
			ORDER BY p.expected_end_date ASC
			""",
			tuple(candidates),
			as_dict=True,
		)
	for s in sans_pointage:
		if s.conducteur:
			cm_users.add(s.conducteur)
		r = frappe.utils.date_diff(frappe.utils.nowdate(), s.expected_end_date) if s.expected_end_date else 0
		s["retard"] = r if r > 0 else 0

	# --- Heures hors chantier par activité (vide si filtre conducteur) --------
	activity = frappe.db.sql(
		f"""
		SELECT COALESCE(d.activity_type, 'Non défini') AS activity_type, SUM(d.hours) AS hours
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name{cm_join}
		WHERE t.docstatus = 1
		  AND (d.project IS NULL OR d.project = '')
		  AND COALESCE(d.activity_type, '') NOT IN ({excl})
		  AND t.end_date BETWEEN %s AND %s{comp_t}{cm_sql}
		GROUP BY d.activity_type
		ORDER BY hours DESC
		""",
		tuple([*EXCLUDED_ACTIVITIES, start_date, end_date, *comp_pt, *cm_p]),
		as_dict=True,
	)
	activity = [{"activity_type": a.activity_type, "hours": round(a.hours or 0)} for a in activity]

	# --- Répartition par conducteur de travaux --------------------------------
	conducteurs_rows = frappe.db.sql(
		f"""
		SELECT COALESCE(NULLIF(p.custom_construction_manager, ''), '—') AS conducteur,
		       SUM(CASE WHEN t.docstatus = 1 THEN d.hours ELSE 0 END) AS h_val,
		       SUM(CASE WHEN t.docstatus = 0 THEN d.hours ELSE 0 END) AS h_draft,
		       COUNT(DISTINCT d.project) AS nb_chantiers
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name
		JOIN `tabProject` p ON p.name = d.project
		WHERE t.docstatus IN (0, 1)
		  AND d.project IS NOT NULL AND d.project != ''
		  AND t.end_date BETWEEN %s AND %s{comp_t}{cm_sql}
		GROUP BY conducteur
		ORDER BY h_val DESC
		""",
		tuple([start_date, end_date, *comp_pt, *cm_p]),
		as_dict=True,
	)
	for c in conducteurs_rows:
		c["h_val"] = round(c["h_val"] or 0)
		c["h_draft"] = round(c["h_draft"] or 0)
		if c["conducteur"] and c["conducteur"] != "—":
			cm_users.add(c["conducteur"])

	# --- Séries hebdomadaires (lundi = début de semaine) ----------------------
	ca_week = frappe.db.sql(
		f"""
		SELECT DATE(DATE_SUB(si.posting_date, INTERVAL WEEKDAY(si.posting_date) DAY)) AS wk,
		       SUM(si.total) AS ca
		FROM `tabSales Invoice` si
		JOIN `tabProject` p ON p.name = si.project
		WHERE si.docstatus = 1 AND si.is_return = 0
		  AND (si.is_down_payment_invoice = 0 OR si.is_down_payment_invoice IS NULL)
		  AND p.custom_estimated_labor_hours > 1
		  AND si.posting_date BETWEEN %s AND %s{comp_si}{cm_sql}
		GROUP BY wk ORDER BY wk
		""",
		tuple([start_date, end_date, *comp_psi, *cm_p]),
		as_dict=True,
	)
	hours_week = frappe.db.sql(
		f"""
		SELECT DATE(DATE_SUB(t.end_date, INTERVAL WEEKDAY(t.end_date) DAY)) AS wk,
		       SUM(CASE WHEN t.docstatus = 1 THEN d.hours ELSE 0 END) AS val,
		       SUM(CASE WHEN t.docstatus = 0 THEN d.hours ELSE 0 END) AS draft
		FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name{cm_join}
		WHERE t.docstatus IN (0, 1)
		  AND COALESCE(d.activity_type, '') NOT IN ({excl})
		  AND t.end_date BETWEEN %s AND %s{comp_t}{cm_sql}
		GROUP BY wk ORDER BY wk
		""",
		tuple([*EXCLUDED_ACTIVITIES, start_date, end_date, *comp_pt, *cm_p]),
		as_dict=True,
	)
	wk_map = {}
	for r in ca_week:
		wk_map.setdefault(str(r.wk), {"ca": 0, "val": 0, "draft": 0})["ca"] = round(r.ca or 0)
	for r in hours_week:
		e = wk_map.setdefault(str(r.wk), {"ca": 0, "val": 0, "draft": 0})
		e["val"] = round(r.val or 0)
		e["draft"] = round(r.draft or 0)
	weekly = [{"week": k, **v} for k, v in sorted(wk_map.items())]

	# --- Noms complets des utilisateurs ---------------------------------------
	user_names = {}
	if cm_users:
		for u in frappe.db.get_all(
			"User", filters={"name": ["in", list(cm_users)]},
			fields=["name", "full_name"],
		):
			user_names[u.name] = u.full_name or u.name

	def resolve(u):
		return user_names.get(u, u) if u else ""

	for p in projects:
		p["conducteur_nom"] = resolve(p["conducteur"])
		p["responsable_nom"] = resolve(p["responsable"])
	for s in sans_pointage:
		s["conducteur_nom"] = resolve(s.get("conducteur"))
	for c in conducteurs_rows:
		c["conducteur_nom"] = resolve(c["conducteur"]) if c["conducteur"] != "—" else "Sans conducteur"

	# --- Options de filtres (indépendantes de la période) ---------------------
	meta_conducteurs = frappe.db.sql(
		"""
		SELECT DISTINCT p.custom_construction_manager AS value,
		       COALESCE(u.full_name, p.custom_construction_manager) AS label
		FROM `tabProject` p
		LEFT JOIN `tabUser` u ON u.name = p.custom_construction_manager
		WHERE p.custom_construction_manager IS NOT NULL AND p.custom_construction_manager != ''
		ORDER BY label
		""",
		as_dict=True,
	)
	meta_companies = frappe.get_all("Company", pluck="name", order_by="name")

	# --- Noms exacts des documents composant chaque KPI ------------------------
	# Le filtre "conducteur" porte sur le Projet, pas sur ces documents : le seul
	# moyen d'ouvrir une liste qui reflète EXACTEMENT le total est de filtrer par
	# `name IN [...]`. On renvoie donc la liste des documents de chaque KPI.
	def _names(sql, params):
		return frappe.db.sql(sql, tuple(params), pluck=True)

	inv_names = _names(
		f"""
		SELECT si.name FROM `tabSales Invoice` si
		JOIN `tabProject` p ON p.name = si.project
		WHERE si.docstatus = 1 AND si.is_return = 0
		  AND (si.is_down_payment_invoice = 0 OR si.is_down_payment_invoice IS NULL)
		  AND p.custom_estimated_labor_hours > 1
		  AND si.posting_date BETWEEN %s AND %s{comp_si}{cm_sql}
		""",
		[start_date, end_date, *comp_psi, *cm_p],
	)
	po_join2 = " JOIN `tabProject` p ON p.name = poi.project" if cm_list else ""
	po_names = _names(
		f"""
		SELECT DISTINCT po.name FROM `tabPurchase Order Item` poi
		JOIN `tabPurchase Order` po ON po.name = poi.parent{po_join2}
		WHERE po.docstatus < 2 AND poi.project IS NOT NULL AND poi.project != ''
		  AND po.transaction_date BETWEEN %s AND %s{comp_po}{cm_sql}
		""",
		[start_date, end_date, *comp_po_p, *cm_p],
	)
	exp_join2 = " JOIN `tabProject` p ON p.name = e.project" if cm_list else ""
	exp_names = _names(
		f"""
		SELECT e.name FROM `tabExpense` e{exp_join2}
		WHERE e.docstatus < 2 AND e.project IS NOT NULL AND e.project != ''
		  AND e.expense_date BETWEEN %s AND %s{comp_exp}{cm_sql}
		""",
		[start_date, end_date, *comp_exp_p, *cm_p],
	)
	fab_join2 = " JOIN `tabProject` p ON p.name = f.project" if cm_list else ""
	fab_names = _names(
		f"""
		SELECT f.name FROM `tabFabrication VT` f{fab_join2}
		WHERE f.status != 'Annulé' AND f.project IS NOT NULL AND f.project != ''
		  AND DATE(f.creation) BETWEEN %s AND %s{comp_fab}{cm_sql}
		""",
		[start_date, end_date, *comp_fab_p, *cm_p],
	)
	ts_join2 = " JOIN `tabProject` p ON p.name = d.project" if cm_list else ""
	ts_draft_names = _names(
		f"""
		SELECT DISTINCT t.name FROM `tabTimesheet` t
		JOIN `tabTimesheet Detail` d ON d.parent = t.name{ts_join2}
		WHERE t.docstatus = 0
		  AND COALESCE(d.activity_type, '') NOT IN ({excl})
		  AND t.end_date BETWEEN %s AND %s{comp_t}{cm_sql}
		""",
		[*EXCLUDED_ACTIVITIES, start_date, end_date, *comp_pt, *cm_p],
	)

	return {
		"period": {
			"start_date": str(start_date),
			"end_date": str(end_date),
			"prev_start": str(prev_start),
			"prev_end": str(prev_end),
			"days": length + 1,
		},
		"meta": {"conducteurs": meta_conducteurs, "companies": meta_companies},
		"doc_names": {
			"ca": inv_names,
			"po": po_names,
			"depenses": exp_names,
			"fabrication": fab_names,
			"nonval": ts_draft_names,
		},
		"kpis": kpis,
		"kpis_prev": kpis_prev,
		"projects": projects,
		"sans_pointage": sans_pointage,
		"activity": activity,
		"conducteurs": conducteurs_rows,
		"weekly": weekly,
	}

# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt
#
# API JSON de la vue "Planning Chantiers" (page Desk /app/planning-chantiers).
#
# Remplace le Script Report `Order book` par une vue PROSPECTIVE : au lieu de
# lister les commandes en retard de facturation, on projette dans le futur ce
# qui doit se passer sur chaque chantier, semaine par semaine.
#
# La grille = une ligne par chantier (Projet), une colonne par semaine. Chaque
# cellule porte des "jalons" :
#   • 🛒 réceptions attendues de commandes fournisseur (poi.schedule_date)
#   • 🏭 fabrications VT à terminer (date_de_fin_prévue)
#   • 🚚 poses / livraisons prévues (Sales Order.delivery_date)
#   • 📅 événements planifiés (Event.starts_on)
#   • ✅ réceptions de chantier DÉJÀ faites (Work Completion Receipt) — le "déjà
#        fait" qu'on veut aussi voir.
#
# On garde le champ texte "statut du chantier" (Sales Order.custom_construction_status)
# très apprécié, agrégé au niveau du chantier.

import json

import frappe

# Fenêtre par défaut : 2 semaines passées (ce qui vient d'être fait / en retard)
# + 12 semaines à venir.
DEFAULT_PAST_WEEKS = 2
DEFAULT_WEEKS = 14


def _parse_list(value):
	if not value:
		return []
	if isinstance(value, str):
		try:
			value = json.loads(value)
		except (ValueError, TypeError):
			value = [value]
	return [v for v in value if v]


def _monday(d):
	"""Lundi de la semaine contenant `d`."""
	d = frappe.utils.getdate(d)
	return frappe.utils.add_days(d, -d.weekday())


def _week_index(mdate, first_monday):
	"""Index de semaine (0-based) d'une date dans la fenêtre, ou None si hors."""
	if not mdate:
		return None
	return frappe.utils.date_diff(frappe.utils.getdate(mdate), first_monday) // 7


@frappe.whitelist()
def get_planning(
	start_date=None,
	weeks=None,
	company=None,
	cost_center=None,
	conducteurs=None,
	responsable=None,
	only_active=1,
	granularity="week",
):
	"""Point d'entrée de la vue Planning Chantiers.

	`start_date` = lundi de la première semaine affichée (défaut : lundi
	d'il y a 2 semaines). `weeks` = nombre de colonnes hebdomadaires.
	Filtres portés par le chantier : `company`, `cost_center`, `conducteurs`
	(conducteur de travaux) et `responsable` (responsable de chantier).
	`only_active` masque les chantiers Terminés/Annulés (défaut : oui).
	"""

	weeks = int(weeks or DEFAULT_WEEKS)
	if start_date:
		first_monday = _monday(start_date)
	else:
		first_monday = _monday(frappe.utils.add_days(frappe.utils.nowdate(), -DEFAULT_PAST_WEEKS * 7))
	last_sunday = frappe.utils.add_days(first_monday, weeks * 7 - 1)
	today = frappe.utils.getdate(frappe.utils.nowdate())
	cm_list = _parse_list(conducteurs)
	cost_center = cost_center or None
	responsable = responsable or None
	only_active = frappe.utils.cint(only_active)
	granularity = "day" if str(granularity).startswith("day") else "week"

	# --- Colonnes de la grille + fonction date -> index de colonne ------------
	columns = []
	if granularity == "day":
		# Jours ouvrés uniquement (lundi→vendredi). Une échéance tombant un
		# week-end est rattachée au lundi suivant (glissement naturel).
		dow_fr = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
		date_to_idx = {}
		d = first_monday
		while d <= last_sunday:
			if d.weekday() < 5:
				i = len(columns)
				date_to_idx[str(d)] = i
				columns.append({
					"index": i, "start": str(d), "end": str(d),
					"is_current": d == today, "is_past": d < today,
					"top": dow_fr[d.weekday()], "bottom": d.strftime("%d/%m"),
				})
			d = frappe.utils.add_days(d, 1)

		def bucket_of(mdate):
			if not mdate:
				return None
			dd = frappe.utils.getdate(mdate)
			while dd.weekday() >= 5:
				dd = frappe.utils.add_days(dd, 1)
			return date_to_idx.get(str(dd))
	else:
		for i in range(weeks):
			ws = frappe.utils.add_days(first_monday, i * 7)
			we = frappe.utils.add_days(ws, 6)
			columns.append({
				"index": i, "start": str(ws), "end": str(we),
				"is_current": ws <= today <= we, "is_past": we < today,
				"top": f"S{ws.isocalendar()[1]}", "bottom": ws.strftime("%d/%m"),
			})

		def bucket_of(mdate):
			if not mdate:
				return None
			idx = frappe.utils.date_diff(frappe.utils.getdate(mdate), first_monday) // 7
			return idx if 0 <= idx < weeks else None

	# --- Clause commune de filtrage sur le chantier ---------------------------
	# Toutes les sources sont reliées au chantier par `project`. On restreint via
	# une jointure `tabProject p` (déjà présente dans toutes les requêtes).
	proj_sql, proj_p = "", []
	if company:
		proj_sql += " AND p.company = %s"
		proj_p.append(company)
	if cost_center:
		proj_sql += " AND p.cost_center = %s"
		proj_p.append(cost_center)
	if cm_list:
		ph = ",".join(["%s"] * len(cm_list))
		proj_sql += f" AND p.custom_construction_manager IN ({ph})"
		proj_p += list(cm_list)
	if responsable:
		proj_sql += " AND p.custom_project_manager = %s"
		proj_p.append(responsable)
	if only_active:
		proj_sql += " AND p.status NOT IN ('Completed', 'Cancelled')"

	window = [first_monday, last_sunday]

	# milestones_by_project[project] = [milestone, ...]
	milestones = {}

	def add(project, ms):
		if not project:
			return
		idx = bucket_of(ms.get("date"))
		if idx is None:
			return
		ms["week"] = idx
		ms["overdue"] = bool(not ms.get("done") and ms.get("date") and frappe.utils.getdate(ms["date"]) < today)
		milestones.setdefault(project, []).append(ms)

	# --- 🛒 Réceptions attendues de commandes fournisseur ---------------------
	# Agrégées par (commande, semaine) : une ligne de commande = une échéance.
	po_rows = frappe.db.sql(
		f"""
		SELECT poi.project AS project, po.name AS po, po.supplier AS supplier,
		       po.supplier_name AS supplier_name, poi.schedule_date AS date,
		       SUM(poi.amount) AS amount,
		       SUM(poi.qty) AS qty, SUM(poi.received_qty) AS received_qty,
		       COUNT(*) AS nb_lines
		FROM `tabPurchase Order Item` poi
		JOIN `tabPurchase Order` po ON po.name = poi.parent
		JOIN `tabProject` p ON p.name = poi.project
		WHERE po.docstatus = 1 AND po.status NOT IN ('Closed', 'Cancelled')
		  AND poi.project IS NOT NULL AND poi.project != ''
		  AND poi.schedule_date BETWEEN %s AND %s{proj_sql}
		GROUP BY poi.project, po.name, poi.schedule_date
		ORDER BY poi.schedule_date
		""",
		tuple([*window, *proj_p]),
		as_dict=True,
	)
	for r in po_rows:
		done = (r.received_qty or 0) >= (r.qty or 0) and (r.qty or 0) > 0
		add(r.project, {
			"type": "po",
			"date": str(r.date),
			"done": done,
			"ref": r.po,
			"doctype": "Purchase Order",
			"title": r.supplier_name or r.supplier or r.po,
			"amount": round(r.amount or 0),
			"qty": r.qty or 0,
			"received_qty": r.received_qty or 0,
			"nb_lines": r.nb_lines or 0,
		})

	# --- 🏭 Fabrications VT à terminer ----------------------------------------
	fab_rows = frappe.db.sql(
		f"""
		SELECT f.project AS project, f.name AS ref, f.status AS status,
		       f.article AS article, f.`date_de_fin_prévue` AS date,
		       f.manufacturing_costs AS cost
		FROM `tabFabrication VT` f
		JOIN `tabProject` p ON p.name = f.project
		WHERE f.status != 'Annulé'
		  AND f.project IS NOT NULL AND f.project != ''
		  AND f.`date_de_fin_prévue` BETWEEN %s AND %s{proj_sql}
		ORDER BY f.`date_de_fin_prévue`
		""",
		tuple([*window, *proj_p]),
		as_dict=True,
	)
	for r in fab_rows:
		add(r.project, {
			"type": "fab",
			"date": str(r.date),
			"done": r.status == "Fait",
			"ref": r.ref,
			"doctype": "Fabrication VT",
			"title": r.article or r.ref,
			"status": r.status,
			"amount": round(r.cost or 0),
		})

	# --- 🚚 Poses / livraisons prévues (Sales Order.delivery_date) ------------
	so_rows = frappe.db.sql(
		f"""
		SELECT so.project AS project, so.name AS ref, so.delivery_date AS date,
		       so.status AS status, so.per_delivered AS per_delivered,
		       so.per_billed AS per_billed, so.total AS total,
		       so.customer_name AS customer_name,
		       so.custom_construction_status AS construction_status,
		       so.custom_statut_fiche_de_travail AS statut_fiche,
		       so.custom_per_received AS per_received,
		       so.custom_payment_request_status AS payment_request_status
		FROM `tabSales Order` so
		JOIN `tabProject` p ON p.name = so.project
		WHERE so.docstatus = 1 AND so.status NOT IN ('Closed', 'Cancelled')
		  AND so.project IS NOT NULL AND so.project != ''
		  AND so.delivery_date BETWEEN %s AND %s{proj_sql}
		ORDER BY so.delivery_date
		""",
		tuple([*window, *proj_p]),
		as_dict=True,
	)
	for r in so_rows:
		add(r.project, {
			"type": "delivery",
			"date": str(r.date),
			"done": (r.per_delivered or 0) >= 100 or r.status == "Completed",
			"ref": r.ref,
			"doctype": "Sales Order",
			"title": r.customer_name or r.ref,
			"per_delivered": round(r.per_delivered or 0),
			"amount": round(r.total or 0),
			"status": r.status,
			# Champs bruts pour reconstituer VOTRE indicateur de statut de
			# commande (cf. sales_order_list.js get_indicator).
			"so": {
				"name": r.ref,
				"status": r.status,
				"docstatus": 1,
				"per_billed": round(r.per_billed or 0),
				"per_delivered": round(r.per_delivered or 0),
				"custom_per_received": round(r.per_received or 0),
				"custom_statut_fiche_de_travail": r.statut_fiche or "",
				"custom_payment_request_status": r.payment_request_status or "",
			},
		})

	# --- 📅 Événements planifiés ----------------------------------------------
	# On distingue trois sous-types via les liens de l'événement :
	#   • 🔍 visite technique (custom_visite_technique)
	#   • 📋 fiche de travail (custom_fiche_de_travail)
	#   • 📅 autre événement
	# et on affiche l'employé rattaché (custom_employé).
	ev_rows = frappe.db.sql(
		f"""
		SELECT e.project AS project, e.name AS ref, DATE(e.starts_on) AS date,
		       e.starts_on AS starts_on, e.ends_on AS ends_on, e.subject AS subject,
		       e.color AS color, e.event_category AS category,
		       e.custom_visite_technique AS vt, e.custom_fiche_de_travail AS ft,
		       e.`custom_employé` AS employe
		FROM `tabEvent` e
		JOIN `tabProject` p ON p.name = e.project
		WHERE e.project IS NOT NULL AND e.project != ''
		  AND DATE(e.starts_on) BETWEEN %s AND %s{proj_sql}
		ORDER BY e.starts_on
		""",
		tuple([*window, *proj_p]),
		as_dict=True,
	)
	# Noms des employés rattachés aux événements.
	emp_ids = {r.employe for r in ev_rows if r.employe}
	emp_names = {}
	if emp_ids:
		for e in frappe.db.get_all("Employee", filters={"name": ["in", list(emp_ids)]},
								   fields=["name", "employee_name"]):
			emp_names[e.name] = e.employee_name or e.name
	for r in ev_rows:
		# Le sous-type sert à la distinction visuelle (icône/couleur/filtre), mais
		# l'objet reste un ÉVÉNEMENT : le clic ouvre l'Event, pas le doc lié.
		if r.vt:
			kind, linked_dt, linked = "vt", "Visite Technique", r.vt
		elif r.ft:
			kind, linked_dt, linked = "ft", "Fiche de travail", r.ft
		else:
			kind, linked_dt, linked = "event", None, None
		add(r.project, {
			"type": kind,
			"date": str(r.date),
			"done": bool(r.date and frappe.utils.getdate(r.date) < today),
			"ref": r.ref,
			"doctype": "Event",
			"title": r.subject or r.ref,
			"linked_doctype": linked_dt,
			"linked_name": linked,
			"color": r.color,
			"category": r.category,
			"employee": r.employe or "",
			"employee_name": emp_names.get(r.employe, r.employe) if r.employe else "",
			"starts_on": str(r.starts_on) if r.starts_on else None,
			"ends_on": str(r.ends_on) if r.ends_on else None,
		})

	# --- ✅ Réceptions de chantier DÉJÀ faites (Work Completion Receipt) -------
	wcr_rows = frappe.db.sql(
		f"""
		SELECT w.project AS project, w.name AS ref, w.le AS date,
		       w.status AS status, w.date_levee_reserve AS date_levee_reserve
		FROM `tabWork Completion Receipt` w
		JOIN `tabProject` p ON p.name = w.project
		WHERE w.docstatus < 2
		  AND w.project IS NOT NULL AND w.project != ''
		  AND w.le BETWEEN %s AND %s{proj_sql}
		ORDER BY w.le
		""",
		tuple([*window, *proj_p]),
		as_dict=True,
	)
	for r in wcr_rows:
		add(r.project, {
			"type": "reception",
			"date": str(r.date),
			"done": True,
			"ref": r.ref,
			"doctype": "Work Completion Receipt",
			"title": r.ref,
			"status": r.status,
			"date_levee_reserve": str(r.date_levee_reserve) if r.date_levee_reserve else None,
		})

	# --- Métadonnées chantier + agrégats Sales Order --------------------------
	project_names = list(milestones.keys())
	rows = []
	cm_users = set()
	if project_names:
		ph = ",".join(["%s"] * len(project_names))
		meta = {}
		for r in frappe.db.sql(
			f"""
			SELECT name, customer, status, project_type, expected_end_date,
			       custom_construction_manager AS conducteur,
			       custom_project_manager AS responsable, cost_center, company
			FROM `tabProject` WHERE name IN ({ph})
			""",
			tuple(project_names), as_dict=True,
		):
			meta[r.name] = r

		# Agrégats SO par chantier : total commandé, % facturé, dernier statut de
		# chantier renseigné (texte libre très utilisé).
		so_agg = {}
		for r in frappe.db.sql(
			f"""
			SELECT project,
			       SUM(total) AS total_sold,
			       SUM(total * per_billed / 100) AS billed,
			       MIN(delivery_date) AS next_delivery
			FROM `tabSales Order`
			WHERE project IN ({ph}) AND docstatus = 1
			  AND status NOT IN ('Closed', 'Cancelled')
			  AND custom_exclude_from_statistics != 1
			GROUP BY project
			""",
			tuple(project_names), as_dict=True,
		):
			so_agg[r.project] = r

		# Statut du chantier (texte libre sur Sales Order) : on affiche le statut
		# de la commande la plus récente qui en porte un, et on retient la
		# commande cible pour l'édition en un clic (comme l'ancien Order book).
		constr_status = {}   # project -> {"text": str, "so": so_name}
		latest_so = {}       # project -> commande la plus récente (repli édition)
		for r in frappe.db.sql(
			f"""
			SELECT project, name AS so, custom_construction_status AS s
			FROM `tabSales Order`
			WHERE project IN ({ph}) AND docstatus = 1
			ORDER BY modified DESC
			""",
			tuple(project_names), as_dict=True,
		):
			latest_so.setdefault(r.project, r.so)
			s = (r.s or "").strip()
			if s and r.project not in constr_status:
				constr_status[r.project] = {"text": s, "so": r.so}

		# Incidents qualité par chantier (ouverts ET fermés) — pastille cliquable.
		incident_map = {}
		closed_status = ("Closed", "Resolved", "Fermé", "Résolu")
		for i in frappe.db.get_all(
			"Quality Incident",
			filters={"project": ["in", project_names]},
			fields=["name", "project", "status", "object"],
		):
			incident_map.setdefault(i.project, []).append({
				"name": i.name,
				"status": i.status,
				"object": i.object or i.name,
				"open": i.status not in closed_status,
			})

		for name in project_names:
			m = meta.get(name)
			if not m:
				continue
			agg = so_agg.get(name) or {}
			total_sold = round(agg.get("total_sold") or 0)
			billed = round(agg.get("billed") or 0)
			ml = sorted(milestones[name], key=lambda x: (x["date"], x["type"]))
			# Prochaine échéance non faite (pour le tri et le repérage rapide).
			next_ms = next((x for x in ml if not x["done"]), None)
			if m.conducteur:
				cm_users.add(m.conducteur)
			if m.responsable:
				cm_users.add(m.responsable)
			rows.append({
				"project": name,
				"customer": m.customer or "",
				"status": m.status,
				"type_projet": m.project_type or "",
				"conducteur": m.conducteur or "",
				"responsable": m.responsable or "",
				"cost_center": m.cost_center or "",
				"expected_end_date": str(m.expected_end_date) if m.expected_end_date else None,
				"construction_status": (constr_status.get(name) or {}).get("text", ""),
				"construction_status_so": (constr_status.get(name) or {}).get("so") or latest_so.get(name),
				"total_sold": total_sold,
				"billed": billed,
				"reste_a_facturer": max(0, total_sold - billed),
				"pct_facture": round(billed / total_sold * 100) if total_sold > 0 else 0,
				"milestones": ml,
				"next_date": next_ms["date"] if next_ms else None,
				"nb_milestones": len(ml),
				"nb_todo": sum(1 for x in ml if not x["done"]),
				"nb_overdue": sum(1 for x in ml if x["overdue"]),
				"incidents": incident_map.get(name, []),
				"nb_incidents": len(incident_map.get(name, [])),
				"nb_incidents_ouverts": sum(1 for x in incident_map.get(name, []) if x["open"]),
			})

	# Noms complets des conducteurs
	user_names = {}
	if cm_users:
		for u in frappe.db.get_all("User", filters={"name": ["in", list(cm_users)]},
								   fields=["name", "full_name"]):
			user_names[u.name] = u.full_name or u.name
	for r in rows:
		r["conducteur_nom"] = user_names.get(r["conducteur"], r["conducteur"]) if r["conducteur"] else ""
		r["responsable_nom"] = user_names.get(r["responsable"], r["responsable"]) if r["responsable"] else ""

	# Tri : chantiers avec la prochaine échéance la plus proche d'abord, puis les
	# chantiers sans échéance à venir (que du passé/fait).
	rows.sort(key=lambda r: (r["next_date"] is None, r["next_date"] or "9999", r["project"]))

	# Les colonnes (jour ou semaine) ont été construites en amont.

	# --- Résumé (KPIs) --------------------------------------------------------
	all_ms = [m for r in rows for m in r["milestones"]]
	summary = {
		"nb_projects": len(rows),
		"nb_po": sum(1 for m in all_ms if m["type"] == "po" and not m["done"]),
		"nb_fab": sum(1 for m in all_ms if m["type"] == "fab" and not m["done"]),
		"nb_delivery": sum(1 for m in all_ms if m["type"] == "delivery" and not m["done"]),
		"nb_vt": sum(1 for m in all_ms if m["type"] == "vt" and not m["done"]),
		"nb_ft": sum(1 for m in all_ms if m["type"] == "ft" and not m["done"]),
		"nb_event": sum(1 for m in all_ms if m["type"] == "event" and not m["done"]),
		"nb_overdue": sum(1 for m in all_ms if m["overdue"]),
		"reste_a_facturer": sum(r["reste_a_facturer"] for r in rows),
	}

	# --- Options de filtres ---------------------------------------------------
	meta_companies = frappe.get_all("Company", pluck="name", order_by="name")
	meta_cost_centers = frappe.db.sql(
		"""
		SELECT DISTINCT p.cost_center AS value, p.cost_center AS label
		FROM `tabProject` p
		WHERE p.cost_center IS NOT NULL AND p.cost_center != ''
		ORDER BY label
		""",
		as_dict=True,
	)
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
	meta_responsables = frappe.db.sql(
		"""
		SELECT DISTINCT p.custom_project_manager AS value,
		       COALESCE(u.full_name, p.custom_project_manager) AS label
		FROM `tabProject` p
		LEFT JOIN `tabUser` u ON u.name = p.custom_project_manager
		WHERE p.custom_project_manager IS NOT NULL AND p.custom_project_manager != ''
		ORDER BY label
		""",
		as_dict=True,
	)

	return {
		"period": {
			"start_date": str(first_monday),
			"end_date": str(last_sunday),
			"weeks": weeks,
			"granularity": granularity,
			"today": str(today),
		},
		"weeks": columns,
		"rows": rows,
		"summary": summary,
		"meta": {
			"companies": meta_companies,
			"cost_centers": meta_cost_centers,
			"conducteurs": meta_conducteurs,
			"responsables": meta_responsables,
		},
	}

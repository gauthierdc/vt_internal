# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt
#
# API JSON de la page Desk « Carnet de commande » (/app/carnet-de-commande).
#
# Le Script Report `Order book` reste disponible (shell Frappe) ; cette API
# renvoie des données structurées pour que Vue rende ARC, événements, statuts
# et filtres en composants.

from __future__ import annotations

from datetime import date, datetime

import frappe

from vt_internal.vt_internal.report.order_book.order_book import (
	get_order_book_rows,
	summarize_rows,
)


def _iso(value):
	"""Serialize date / datetime / string for JSON (None stays None)."""
	if value is None:
		return None
	if isinstance(value, datetime):
		return value.strftime("%Y-%m-%d %H:%M:%S")
	if isinstance(value, date):
		return value.isoformat()
	text = str(value).strip()
	return text or None


def serialize_arc(po: dict) -> dict:
	return {
		"name": po.get("name"),
		"supplier_name": po.get("supplier_name") or po.get("name") or "",
		"schedule_date": _iso(po.get("schedule_date")),
		"ar_valide": 1 if po.get("ar_valide") else 0,
		"per_received": po.get("per_received") or 0,
		"overdue": bool(po.get("overdue")),
	}


def serialize_event(event: dict) -> dict:
	return {
		"name": event.get("name"),
		"starts_on": _iso(event.get("starts_on")),
		"subject": event.get("subject") or "",
		"kind": event.get("kind") or "event",
		"past": bool(event.get("past")),
		"color": event.get("color"),
	}


def serialize_row(row: dict) -> dict:
	"""JSON-friendly row: ISO dates, ARC / event objects (never HTML)."""
	return {
		"name": row.get("name"),
		"project": row.get("project"),
		"customer_name": row.get("customer_name") or "",
		"status": row.get("status") or "",
		"custom_construction_status": row.get("custom_construction_status") or "",
		"pending_arcs": [serialize_arc(po) for po in (row.get("pending_arcs") or [])],
		"events": [serialize_event(ev) for ev in (row.get("events") or [])],
		"reference_piece": row.get("reference_piece") or "",
		"remaining_amount": row.get("remaining_amount") or 0,
		"total": row.get("total") or 0,
		"delivery_date": _iso(row.get("delivery_date")),
		"hours_total": row.get("hours_total") or 0,
		"hours_solde": row.get("hours_solde") or 0,
		"age": row.get("age"),
		"construction_manager": row.get("construction_manager") or "",
		"construction_manager_name": row.get("construction_manager_name")
		or row.get("construction_manager")
		or "",
		"per_delivered": row.get("per_delivered") or 0,
		"skip_delivery_note": row.get("skip_delivery_note") or 0,
		"grand_total": row.get("grand_total") or 0,
		"custom_statut_fiche_de_travail": row.get("custom_statut_fiche_de_travail"),
		"custom_per_received": row.get("custom_per_received") or 0,
		"custom_payment_request_status": row.get("custom_payment_request_status"),
		"per_billed": row.get("per_billed") or 0,
	}


def build_order_book_payload(rows: list[dict], meta: dict, today) -> dict:
	"""Assemble the Vue payload (pure — unit-tested without a live site)."""
	serialized = [serialize_row(r) for r in rows]
	statuses = sorted({r.get("status") for r in serialized if r.get("status")})
	payload_meta = dict(meta or {})
	payload_meta.setdefault("so_statuses", [{"value": s, "label": s} for s in statuses])
	return {
		"today": today if isinstance(today, str) else _iso(today),
		"rows": serialized,
		"summary": summarize_rows(serialized),
		"meta": payload_meta,
	}


def get_order_book_meta() -> dict:
	"""Filter options independent of the current result set."""
	meta_companies = frappe.get_all("Company", pluck="name", order_by="name")
	meta_cost_centers = frappe.db.sql(
		"""
		SELECT DISTINCT so.cost_center AS value, so.cost_center AS label
		FROM `tabSales Order` so
		WHERE so.cost_center IS NOT NULL AND so.cost_center != ''
		  AND so.docstatus != 2
		  AND so.custom_exclude_from_statistics != 1
		ORDER BY label
		""",
		as_dict=True,
	)
	meta_conducteurs = frappe.db.sql(
		"""
		SELECT DISTINCT src.value, COALESCE(u.full_name, src.value) AS label
		FROM (
			SELECT custom_construction_manager AS value
			FROM `tabProject`
			WHERE custom_construction_manager IS NOT NULL AND custom_construction_manager != ''
			UNION
			SELECT custom_construction_manager AS value
			FROM `tabSales Order`
			WHERE custom_construction_manager IS NOT NULL AND custom_construction_manager != ''
			  AND docstatus != 2
		) src
		LEFT JOIN `tabUser` u ON u.name = src.value
		ORDER BY label
		""",
		as_dict=True,
	)
	return {
		"companies": meta_companies,
		"cost_centers": meta_cost_centers,
		"conducteurs": meta_conducteurs,
	}


@frappe.whitelist()
def get_order_book(company=None, cost_center=None, construction_managers=None, status=None):
	"""Point d'entrée de la page Carnet de commande.

	Filtres serveur : société, centre de coût (descendants inclus), responsables
	de chantier (multi, champ projet avec repli SO), statut SO optionnel.
	Les exclusions planner (Closed, 100 % facturé, stats) restent appliquées.
	"""
	filters = {}
	if company:
		filters["company"] = company
	if cost_center:
		filters["cost_center"] = cost_center
	if construction_managers:
		filters["construction_managers"] = construction_managers
	if status:
		filters["status"] = status
	rows = get_order_book_rows(filters)
	return build_order_book_payload(rows, get_order_book_meta(), frappe.utils.nowdate())

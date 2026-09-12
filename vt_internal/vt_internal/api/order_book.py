# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt
#
# API JSON de la page Desk « Carnet de commande » (/app/carnet-de-commande).
#
# Le Script Report `Order book` reste disponible (shell Frappe) ; cette API
# renvoie des données structurées pour que Vue rende ARC, événements, statuts
# et filtres en composants.

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import frappe

from vt_internal.vt_internal.report.order_book.order_book import (
	get_order_book_rows,
	summarize_rows,
)

PARIS_TZ = ZoneInfo("Europe/Paris")

# Même vocabulaire que public/js/carnet_de_commande/helpers.js (salesOrderStatus)
# et sales_order_list.js — pas les statuts ERP Sales Order.status.
INTERNAL_STATUS_ORDER = [
	"À fabriquer",
	"En fabrication",
	"À livrer",
	"En BL",
	"Chantier à planifier",
	"Chantier à faire",
	"Chantier en cours",
	"CH fait à facturer",
	"🕦 Acompte",
	"On Hold",
	"Closed",
	"Terminé",
]


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


def paris_now(now=None) -> datetime:
	"""Instant de référence en Europe/Paris (aware)."""
	if now is None:
		return datetime.now(PARIS_TZ)
	if isinstance(now, datetime):
		if now.tzinfo is None:
			return now.replace(tzinfo=PARIS_TZ)
		return now.astimezone(PARIS_TZ)
	if isinstance(now, date):
		return datetime.combine(now, time.min, tzinfo=PARIS_TZ)
	text = str(now).strip()
	if not text:
		return datetime.now(PARIS_TZ)
	if " " in text or "T" in text:
		parsed = datetime.fromisoformat(text.replace(" ", "T"))
		if parsed.tzinfo is None:
			return parsed.replace(tzinfo=PARIS_TZ)
		return parsed.astimezone(PARIS_TZ)
	return datetime.combine(date.fromisoformat(text[:10]), time.min, tzinfo=PARIS_TZ)


def event_is_future(starts_on, now=None) -> bool:
	"""True si le début de l'événement est dans le futur (Europe/Paris).

	- datetime : starts_on >= now
	- date seule : date >= jour civil Paris
	- vide / illisible : False
	"""
	if starts_on is None or starts_on == "":
		return False
	ref = paris_now(now)
	if isinstance(starts_on, datetime):
		start = starts_on if starts_on.tzinfo else starts_on.replace(tzinfo=PARIS_TZ)
		if starts_on.tzinfo:
			start = starts_on.astimezone(PARIS_TZ)
		return start >= ref
	if isinstance(starts_on, date):
		return starts_on >= ref.date()
	text = str(starts_on).strip()
	if not text:
		return False
	if " " in text or "T" in text:
		try:
			start = datetime.fromisoformat(text.replace(" ", "T", 1))
		except ValueError:
			try:
				return date.fromisoformat(text[:10]) >= ref.date()
			except ValueError:
				return False
		if start.tzinfo is None:
			start = start.replace(tzinfo=PARIS_TZ)
		else:
			start = start.astimezone(PARIS_TZ)
		return start >= ref
	try:
		return date.fromisoformat(text[:10]) >= ref.date()
	except ValueError:
		return False


def sales_order_internal_status(row: dict) -> str:
	"""Statut interne VT (pills), aligné sur salesOrderStatus() côté Vue."""
	if not row:
		return ""
	billed = row.get("per_billed") or 0
	delivered = row.get("per_delivered") or 0
	fiche = row.get("custom_statut_fiche_de_travail") or ""
	rec = row.get("custom_per_received") or 0
	pay = row.get("custom_payment_request_status")
	status = row.get("status") or ""
	if billed == 100:
		return "Terminé"
	if status in ("On Hold", "Closed"):
		return status
	if pay == "Requested":
		return "🕦 Acompte"
	if delivered > 0 and billed < 100 and not fiche:
		return "En BL"
	if fiche == "À faire" and billed < 100:
		return "Chantier à faire"
	if fiche == "En cours" and billed < 100:
		return "Chantier en cours"
	if fiche == "À planifier" and billed < 100:
		return "Chantier à planifier"
	if rec > 0 and rec < 100:
		return "En fabrication"
	if rec == 100 and delivered == 0 and not fiche:
		return "À livrer"
	if delivered < 100 and billed < 100 and fiche == "Fait":
		return "CH fait à facturer"
	if rec == 0:
		return "À fabriquer"
	return status


def build_internal_status_options(rows: list[dict]) -> list[dict]:
	present = {r.get("internal_status") for r in rows if r.get("internal_status")}
	options = [{"value": s, "label": s} for s in INTERNAL_STATUS_ORDER if s in present]
	known = {o["value"] for o in options}
	for extra in sorted(present - known):
		options.append({"value": extra, "label": extra})
	return options


def filter_rows_by_internal_statuses(rows: list[dict], statuses) -> list[dict]:
	if not statuses:
		return list(rows or [])
	wanted = {s for s in statuses if s}
	if not wanted:
		return list(rows or [])
	return [r for r in (rows or []) if r.get("internal_status") in wanted]


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


def serialize_row(row: dict, now=None) -> dict:
	"""JSON-friendly row: ISO dates, ARC / event objects (never HTML).

	Les événements passés (début < now, Europe/Paris) sont exclus : la page
	Carnet n'affiche que le futur.
	"""
	internal = sales_order_internal_status(row)
	events = [
		serialize_event(ev)
		for ev in (row.get("events") or [])
		if event_is_future(ev.get("starts_on"), now)
	]
	return {
		"name": row.get("name"),
		"project": row.get("project"),
		"customer_name": row.get("customer_name") or "",
		"status": row.get("status") or "",
		"internal_status": internal,
		"custom_construction_status": row.get("custom_construction_status") or "",
		"pending_arcs": [serialize_arc(po) for po in (row.get("pending_arcs") or [])],
		"events": events,
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


def build_order_book_payload(rows: list[dict], meta: dict, today, now=None) -> dict:
	"""Assemble the Vue payload (pure — unit-tested without a live site)."""
	ref = now if now is not None else today
	serialized = [serialize_row(r, now=ref) for r in rows]
	payload_meta = dict(meta or {})
	payload_meta.setdefault("internal_statuses", build_internal_status_options(serialized))
	# Conservé pour compat : plus utilisé par le filtre Vue.
	if "so_statuses" not in payload_meta:
		erp = sorted({r.get("status") for r in serialized if r.get("status")})
		payload_meta["so_statuses"] = [{"value": s, "label": s} for s in erp]
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
	de chantier (multi, champ projet avec repli SO).
	Le filtre de statut interne (pills VT) est côté Vue / URL ``status=``.
	``status`` reste accepté ici pour compat (statut ERP SO) mais la page
	Carnet ne l'envoie plus.
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
	return build_order_book_payload(
		rows,
		get_order_book_meta(),
		frappe.utils.nowdate(),
		now=datetime.now(PARIS_TZ),
	)

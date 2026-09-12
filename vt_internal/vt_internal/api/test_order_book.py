# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

"""Unit tests for the Carnet de commande JSON API (no live Frappe site)."""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock

if "frappe" not in sys.modules:
	frappe = MagicMock()

	def _escape_html(value):
		return (
			str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
		)

	def _format_date(value, fmt="dd/MM/yyyy"):
		if not value:
			return ""
		if hasattr(value, "strftime"):
			if fmt == "dd/MM/yyyy":
				return value.strftime("%d/%m/%Y")
			if fmt == "dd/MM":
				return value.strftime("%d/%m")
		return str(value)

	def _getdate(value):
		if value is None:
			return None
		if isinstance(value, datetime):
			return value.date()
		if isinstance(value, date):
			return value
		return date.fromisoformat(str(value)[:10])

	frappe.utils.escape_html = _escape_html
	frappe.utils.format_date = _format_date
	frappe.utils.getdate = _getdate
	frappe.utils.nowdate = lambda: "2026-09-09"
	frappe._ = lambda text: text
	sys.modules["frappe"] = frappe
	sys.modules["frappe.utils"] = frappe.utils

from vt_internal.vt_internal.api.order_book import (
	PARIS_TZ,
	build_internal_status_options,
	build_order_book_payload,
	event_is_future,
	filter_rows_by_internal_statuses,
	sales_order_internal_status,
	serialize_arc,
	serialize_event,
	serialize_row,
)


def _structured_row(**overrides):
	row = {
		"name": "SO-1",
		"project": "PROJ-1",
		"customer_name": "Miroiterie Avignon",
		"status": "To Deliver and Bill",
		"custom_construction_status": "Attente verre",
		"pending_arcs": [
			{
				"name": "PO-SG",
				"supplier_name": "Saint-Gobain",
				"schedule_date": date(2026, 9, 1),
				"ar_valide": 0,
				"per_received": 20,
				"overdue": True,
			}
		],
		"events": [
			{
				"name": "EV-VT",
				"starts_on": datetime(2026, 9, 12, 9, 0),
				"subject": "Visite Royon",
				"kind": "vt",
				"past": False,
				"color": None,
			}
		],
		"reference_piece": "REF-1",
		"remaining_amount": 800,
		"total": 1000,
		"delivery_date": date(2026, 9, 20),
		"hours_total": 10,
		"hours_solde": 7,
		"age": 39,
		"construction_manager": "alice@example.com",
		"construction_manager_name": "Alice Martin",
		"per_delivered": 0,
		"skip_delivery_note": 0,
		"grand_total": 1200,
		"custom_statut_fiche_de_travail": "À planifier",
		"custom_per_received": 0,
		"custom_payment_request_status": "",
		"per_billed": 20,
	}
	row.update(overrides)
	return row


class TestOrderBookApi(unittest.TestCase):
	def test_serialize_row_is_json_friendly_no_html(self):
		out = serialize_row(_structured_row())
		self.assertEqual(out["customer_name"], "Miroiterie Avignon")
		self.assertEqual(out["delivery_date"], "2026-09-20")
		self.assertEqual(out["pending_arcs"][0]["schedule_date"], "2026-09-01")
		self.assertEqual(out["pending_arcs"][0]["overdue"], True)
		self.assertEqual(out["pending_arcs"][0]["ar_valide"], 0)
		self.assertEqual(out["events"][0]["kind"], "vt")
		self.assertEqual(out["events"][0]["starts_on"], "2026-09-12 09:00:00")
		self.assertNotIn("<", str(out["pending_arcs"]))
		self.assertNotIn("<", str(out["events"]))
		self.assertEqual(out["construction_manager_name"], "Alice Martin")

	def test_serialize_helpers_tolerate_empty(self):
		self.assertEqual(serialize_arc({}).get("supplier_name"), "")
		self.assertEqual(serialize_event({}).get("kind"), "event")
		empty = serialize_row({"name": "SO-X"})
		self.assertEqual(empty["pending_arcs"], [])
		self.assertEqual(empty["events"], [])
		self.assertEqual(empty["customer_name"], "")

	def test_payload_shape_and_summary(self):
		payload = build_order_book_payload(
			[_structured_row()],
			{"companies": ["MAV"], "cost_centers": [], "conducteurs": []},
			date(2026, 9, 9),
		)
		self.assertEqual(payload["today"], "2026-09-09")
		self.assertEqual(len(payload["rows"]), 1)
		self.assertEqual(payload["summary"]["nb_orders"], 1)
		self.assertEqual(payload["summary"]["nb_arcs"], 1)
		self.assertEqual(payload["summary"]["nb_events"], 1)
		self.assertEqual(payload["summary"]["remaining_ht"], 800)
		self.assertEqual(payload["meta"]["companies"], ["MAV"])
		self.assertEqual(payload["meta"]["so_statuses"][0]["value"], "To Deliver and Bill")
		self.assertEqual(payload["meta"]["internal_statuses"][0]["value"], "Chantier à planifier")
		self.assertEqual(payload["rows"][0]["internal_status"], "Chantier à planifier")
		self.assertIsInstance(payload["rows"][0]["pending_arcs"], list)
		self.assertIsInstance(payload["rows"][0]["events"], list)

	def test_payload_keeps_provided_so_statuses(self):
		payload = build_order_book_payload(
			[_structured_row()],
			{"so_statuses": [{"value": "Draft", "label": "Draft"}]},
			"2026-09-09",
		)
		self.assertEqual(payload["meta"]["so_statuses"][0]["value"], "Draft")
		self.assertEqual(payload["today"], "2026-09-09")
		self.assertEqual(payload["meta"]["internal_statuses"][0]["value"], "Chantier à planifier")

	def test_serialize_row_drops_past_events_keeps_future(self):
		now = datetime(2026, 9, 12, 14, 0, tzinfo=PARIS_TZ)
		row = _structured_row(
			events=[
				{
					"name": "EV-PAST-DAY",
					"starts_on": datetime(2026, 9, 11, 9, 0),
					"kind": "vt",
					"past": True,
				},
				{
					"name": "EV-PAST-TODAY",
					"starts_on": datetime(2026, 9, 12, 9, 0),
					"kind": "ft",
					"past": False,
				},
				{
					"name": "EV-FUTURE",
					"starts_on": datetime(2026, 9, 12, 16, 0),
					"kind": "event",
					"past": False,
				},
				{
					"name": "EV-NODATE",
					"starts_on": None,
					"kind": "event",
				},
			]
		)
		out = serialize_row(row, now=now)
		names = [e["name"] for e in out["events"]]
		self.assertEqual(names, ["EV-FUTURE"])

	def test_payload_event_kpi_counts_only_future(self):
		now = datetime(2026, 9, 12, 14, 0, tzinfo=PARIS_TZ)
		row = _structured_row(
			events=[
				{"name": "EV-OLD", "starts_on": datetime(2026, 8, 1, 8, 0), "kind": "vt", "past": True},
				{"name": "EV-NEXT", "starts_on": datetime(2026, 9, 20, 9, 0), "kind": "ft", "past": False},
			]
		)
		payload = build_order_book_payload([row], {}, date(2026, 9, 12), now=now)
		self.assertEqual(len(payload["rows"][0]["events"]), 1)
		self.assertEqual(payload["rows"][0]["events"][0]["name"], "EV-NEXT")
		self.assertEqual(payload["summary"]["nb_events"], 1)

	def test_event_is_future_paris_timezone_and_date_only(self):
		now = datetime(2026, 9, 12, 14, 0, tzinfo=PARIS_TZ)
		self.assertFalse(event_is_future(None, now))
		self.assertFalse(event_is_future("", now))
		self.assertFalse(event_is_future(datetime(2026, 9, 12, 13, 59), now))
		self.assertTrue(event_is_future(datetime(2026, 9, 12, 14, 0), now))
		self.assertTrue(event_is_future(datetime(2026, 9, 12, 15, 0), now))
		self.assertTrue(event_is_future(date(2026, 9, 12), now))
		self.assertFalse(event_is_future(date(2026, 9, 11), now))
		self.assertTrue(event_is_future("2026-09-13 08:00:00", now))
		self.assertFalse(event_is_future("2026-09-12 08:00:00", now))

	def test_internal_status_matches_vue_pills(self):
		self.assertEqual(
			sales_order_internal_status(_structured_row()),
			"Chantier à planifier",
		)
		self.assertEqual(
			sales_order_internal_status(_structured_row(custom_statut_fiche_de_travail="", custom_per_received=0)),
			"À fabriquer",
		)
		self.assertEqual(
			sales_order_internal_status(
				_structured_row(custom_statut_fiche_de_travail="", custom_per_received=40)
			),
			"En fabrication",
		)
		self.assertEqual(
			sales_order_internal_status(
				_structured_row(custom_statut_fiche_de_travail="À faire", per_billed=20)
			),
			"Chantier à faire",
		)
		self.assertEqual(
			sales_order_internal_status(
				_structured_row(custom_statut_fiche_de_travail="", custom_per_received=100, per_delivered=0)
			),
			"À livrer",
		)
		self.assertEqual(sales_order_internal_status({"per_billed": 100, "status": "Completed"}), "Terminé")

	def test_filter_rows_by_internal_statuses_multi(self):
		rows = [
			{"name": "A", "internal_status": "À fabriquer"},
			{"name": "B", "internal_status": "En fabrication"},
			{"name": "C", "internal_status": "Chantier à faire"},
		]
		self.assertEqual(
			[r["name"] for r in filter_rows_by_internal_statuses(rows, ["À fabriquer", "Chantier à faire"])],
			["A", "C"],
		)
		self.assertEqual(filter_rows_by_internal_statuses(rows, []), rows)
		self.assertEqual(filter_rows_by_internal_statuses(rows, None), rows)
		opts = build_internal_status_options(rows)
		self.assertEqual([o["value"] for o in opts], ["À fabriquer", "En fabrication", "Chantier à faire"])


if __name__ == "__main__":
	unittest.main()

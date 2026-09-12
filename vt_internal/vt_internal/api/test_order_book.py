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
	build_order_book_payload,
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


if __name__ == "__main__":
	unittest.main()
